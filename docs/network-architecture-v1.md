# Network Architecture v1

状态：响应边界在 0.2.0 落地，凭据隔离与默认写入防护在 0.3.0 落地。实测范围见 [Phase 1](network-architecture-v1-phase1.md) 与 [Phase 2](network-architecture-v1-phase2.md)。其余内容为设计。适用于 Kotlin Android 的 Retrofit/OkHttp JSON API 与已存在的网络适配层。基于[共享契约](architecture-foundation-v1.md#跨-skill-契约)。文件上传下载、流式连接、离线同步和多账户鉴权分别按实际业务扩展。

## 调用边界

`UI → ViewModel → [可选 UseCase] → Repository → [可选 RemoteDataSource] → API Service → HTTP`。应用装配根组装客户端、会话来源和 Repository。现有多模块若已通过领域接口做依赖反转，保留其方向，由装配根绑定实现。UI 状态不接触 DTO、Response、ApiError 或后端业务码。

- **API Service** 声明 HTTP 方法、路径、参数、返回体。路径默认相对固定 base URL。原始状态、响应头、反序列化类型只在数据实现内。
- **RemoteDataSource** 封装重复的协议适配、分页或跨调用的远端交互。简单路径由 Repository 调用 Service，并在内部完成同样的边界工作。无需为一个调用增加转发类。
- **Repository** 定义业务数据操作，映射失败和模型，管理缓存/本地来源和一致性（如有）。默认具体类和构造注入。跨模块接口或真实替换需求沿 Foundation 决策。
- **DTO** 按协议定义字段与可缺省性。对 Gson 的缺字段、显式 null、非法值和默认值逐项决定，必要时采用可空 wire 字段与集中映射，或定制 adapter 识别必需基本类型缺失。Mapper 校验必需字段和语义约束，允许契约规定的默认值。应用模型仅保留业务需要的值；简单映射可放在现有 Repository 文件。UI 格式化和资源映射放呈现层。

## 默认响应策略

现有 `safeApiCall` 可保留为 transport 内部入口。新增示例用 `suspend fun getUser(): Response<UserDto>` 明确处理状态和 body，避免 Retrofit 在必需 body 缺失时抛空指针。由具体端点决定是否接受空内容。映射后的业务结果可沿用应用已有结果类型，不复制一套全局 Result。

| 结果 | 在数据边界处理 |
| --- | --- |
| 2xx + 有效数据 | 校验并映射应用模型；列表为空可合法，不等同于缺失 body |
| 204/205 或合法空成功 | 对确认支持无内容的命令按契约返回 Unit，或按约定得到可空数据。对必需 DTO 接口返回可识别的协议失败 |
| 2xx + 空 body、JSON null、缺字段或无效结构 | 仅在契约允许时视为成功；否则归协议/解码错误。测试实际 converter 路径，避免全局捕获空指针 |
| 2xx + 业务拒绝 | 仅在约定的 envelope 中读取白名单业务码，映射业务语义。未知业务码回退安全通用错误 |
| 非 2xx | 以状态为基础。401 表示鉴权失败，403 权限不足，404 按端点语义解释，429 与 5xx 只在明确策略下重试。仅在已约定时解析错误体，关闭 body。错误体异常不能覆盖已知 HTTP 结果；禁止透传原文、异常或整组 header |
| I/O、超时、解析异常 | 区分传输与协议失败，业务选择是否合并展示。以固定版本异常与回归样本为依据，区分截断 JSON 与响应流断开。编程错误保留原状 |

Retrofit 3.0.0 会预缓冲非 2xx 响应。映射时的读取上限只能限制二次解析。对不可信大响应若需硬上限，在反序列化或 Retrofit 缓冲前处理并测试；流式下载另定所有权和字节预算。项目不凭空定义统一服务端 envelope。[Retrofit 响应处理源码](https://github.com/square/retrofit/blob/3.0.0/retrofit/src/main/java/retrofit2/OkHttpCall.java)

## 取消、客户端与超时

默认使用 Retrofit suspend，让 Job 取消底层 Call。任何预期异常转成结果前检查协程仍活跃，返回映射结果前同样避免已取消工作发布状态。显式重抛 `CancellationException`，包括外层 `withTimeout` 的取消。应用若明确用自己的期限产生业务超时，只转换自己拥有的期限并保持父取消可传播。常规 Retrofit suspend 可在主线程调用；阻塞 token/磁盘读取应在拥有者提前完成，昂贵映射切到合适的 Dispatcher。

0.3.0 按精确 scheme/host/port 绑定客户端，拒绝其它目的地；认证客户端与第三方客户端分别配置和复用。清理逐请求 auth/cookies，关闭 CookieJar 和两个 Authenticator。保留系统 TLS 校验、禁用默认重定向、按 scheme/host/port 注入应用级凭据。鉴权 Service 默认仅允许固定 HTTPS origin，动态 @Url 作为独立评审入口；公共或第三方请求用无凭据 client。现有 30 秒是参考默认值，保留 connect/read/write 与 call 总预算，慢接口按业务约定调整。重试/刷新另有端到端总预算。拦截器可注入明确的通用 header 和非阻塞 token 快照。避免在拦截器里做业务错误转换、阻塞磁盘或创建新 client。[Retrofit suspend 取消源码](https://github.com/square/retrofit/blob/3.0.0/retrofit/src/main/java/retrofit2/KotlinExtensions.kt)

## 重放与鉴权

- **默认**：项目可提供非阻塞 token 快照，无 token 或独立公开客户端不注入；401 返回类型化结果，由会话拥有者决定交互。无全局应用重试，无内置刷新机制。0.3.0 关闭连接恢复，非 GET/HEAD 使用 one-shot body，包括无正文写入的空 body。读取的库级状态 follow-up 仍需注意，GET/HEAD 必须保持读取语义。
- **读及可重放操作**：按端点和服务端语义显式允许。遇到短暂故障时可选有限次数和总时限的退避、抖动，按约定处理 `Retry-After`。取消停止所有新尝试。401 走鉴权策略，解析错误、永久拒绝和 TLS 信任错误不自动重试。
- **未知结果写操作**：超时或断线可能已提交。支付、创建订单等默认禁止自动重放，必要时提供查询/对账。服务端明确支持幂等 key、去重范围和期限后才允许重放，且重试沿用同一个 key 和请求语义。HTTP 动词只是线索。
- **OkHttp 4.12.0 的限制**：`retryOnConnectionFailure(false)` 控制连接恢复及部分 408 follow-up。503 + `Retry-After: 0` 的分支独立于该开关，421、Authenticator 等也有各自条件。对不可重放且有请求体的命令，结合独立策略 client、关闭连接恢复、禁用重定向/Authenticator 和 one-shot body，并以实际请求数验证。无请求体的写操作同样要验证固定客户端路径，对仍有 follow-up 的路径使用经验证的替代实现或服务器去重，再对业务承诺不重放。[OkHttp 4.12.0 重试和 follow-up 源码](https://github.com/square/okhttp/blob/parent-4.12.0/okhttp/src/main/kotlin/okhttp3/internal/http/RetryAndFollowUpInterceptor.kt)

### 可选并发 Token 刷新

仅在后端有刷新协议且业务需要时引入。优先由会话组件在 suspend 数据路径统一协调，支持取消和测试。每个账户/会话世代共享一个在途刷新，401 时对比请求使用的 token 世代与当前 token。若已有新 token，直接进入一次受控重放；否则并发等待同一个刷新。刷新使用独立、同样校验 TLS 的 client 或适配器，无业务鉴权回调，避免递归和队列饥饿。刷新协程有明确的会话 scope 和超时；等待者取消即退出，其它有效等待者可继续，登出或换号取消旧会话任务。更新 token 时按会话世代提交，迟到结果不能覆盖新会话。永久拒绝发一次会话失效信号，短暂网络失败走可恢复状态。二次 401 停止；只有可重放端点才能自动重发。若既有项目使用同步 Authenticator，审查执行线程与独立刷新通道，并用并发测试证实不阻塞整个业务队列。

## 日志与安全

默认无 HTTP 请求/响应内容日志。可选的诊断只记录静态端点标识、状态码、耗时、有限错误类别；统一由应用已有日志入口处理，避免每层重复记录。禁止正文、原始 URL、查询参数、凭据 header 和异常消息进入日志。已有 HTTP 日志工具先关闭 BODY，检查其他等级仍会记录 URL；用字段 allowlist 输出元数据，遮蔽 Authorization、Cookie、Set-Cookie 和自定义凭据头。使用假秘密验证日志、跨 origin、重定向及 release。日志开关不能代替字段审查。

## 验证与接续开发

| 验证 | 目标 |
| --- | --- |
| JVM 单元 | 必需字段、默认值、业务码、错误映射，Repository 返回公开应用模型；受控调度验证取消、刷新重复触发、迟到响应 |
| MockWebServer 集成 | 真实 Service + converter + client，覆盖 2xx、204/205、200 null/空或坏 JSON、4xx/5xx、延迟、断线、真实在途取消（等待收到请求再取消并观察 Call 取消，无失败发布）；origin/TLS 安全用两个服务和测试证书，断言收到的请求数和凭据 |
| 后端契约 | 从经确认的 OpenAPI、后端提供的无敏感 fixture 或 staging 验证方法、路径、字段缺省和错误码。MockWebServer 只验证客户端对其测试输入的行为 |
| 可选扩展回归 | 并发 N 个 401 只发一个刷新，同一请求至多一次重放；测试刷新失败、取消等待、重复 401、登出/换号与不可重放写入。对重试断言实际尝试数、预算、key 和停止条件 |
| Android 工程 | 对选中模块构建、单测。若使用 R8，检查 release 变体中 DTO、泛型签名和转换行为，真实设备/环境结果独立记录 |

Agent 新增业务 API 时先找到项目 ADR、已有 Repository 和生成的 Usage。记录端点的鉴权、重放、成功 body、业务码与失效策略，按现有命名加入 Service 和内部 DTO，并在公开数据入口完成映射。验证失败和取消后再改 UI 状态。没有后端契约时，将未知项记录为待确认，不虚构线上接口。示例的 `GET user` 只是参考。

## 升级与替换

将库类型限制在 Service、converter、transport 结果、DI 装配和相应测试中。上层 Repository API 及业务失败语义原则上保留。升级前记录 Recipe、直接依赖及 Gradle 实际解析版本（含 OkHttp、Okio、Gson、协程与图片库的传递依赖）。用隔离项目核对 Kotlin/AGP/Gradle 支持范围，重跑空 body、解码、取消、重放、TLS、release 测试，审查 Gson/R8 和二进制影响。验证通过后更新兼容性记录与 Recipe/Usage 版本，保留旧锁定版本和回滚点。替换 Retrofit 时用相同协议测试约束新适配器；使用既有网络栈的 App 可应用同一架构契约。
