# Network Architecture v1 · Phase 2 验收

2026-11-06 · retrofit-standard 0.3.0 · [Phase 1](network-architecture-v1-phase1.md)

## 原有边界与复现

0.2.0 使用 OkHttp 4.12.0。生产配置要求 HTTPS，按 scheme/host/port 决定是否自动注入配置头和 Token，关闭普通重定向与跨协议重定向。默认未安装 HTTP 日志拦截器。OkHttp 原有 CookieJar 与 Authenticator 默认均无操作。Phase 1 的订单 API 是只读 GET，复用 AppGraph 的 Retrofit 和响应映射；其测试直接构造 converter 夹具，未验证生产客户端的凭据和写入策略。

已有自动注入限制没有拒绝目的地变化，也没有清理调用方手动带入的 Authorization/Cookie。连接恢复开关沿 OkHttp 默认值，普通可重放请求体仍可能进入 HTTP follow-up。先用旧生产工厂跑新 HTTPS 测试，得到两项失败。

| 真实输入 | 旧实现结果 | 安全契约要求 |
| --- | --- | --- |
| HTTPS 请求手动带 Cookie | 服务端收到 `session=request-secret` | Token-only 客户端清理手动会话凭据 |
| POST 收到 408，随后准备 200 | 客户端最终收到 200，发生 follow-up | 返回原始 408，服务端只接到一次 POST |
| 依赖对照，关闭连接恢复，POST 收到 503 + Retry-After 0 | 服务端收到两个同方法、路径、正文的 POST，最终 200 | 工厂默认写策略还必须阻止状态码 follow-up |

第三项是独立保留的 OkHttp 对照测试。它保留测试 TLS 信任并移除工厂拦截器，以证明库行为。上述 Cookie 和 Token 均为公开测试哨兵。

## 工厂与凭据契约

沿用 `NetworkConfig`、`HttpClientFactory.client/retrofit` 和 `TokenProvider`，每个实例固定一个 HTTPS 来源。每个来源在应用装配根复用自己的实例。认证 API 传入其 TokenProvider，第三方 API 使用独立配置与默认空 TokenProvider。独立配置不复制应用凭据或自定义秘密头。

- 请求目的地必须精确匹配 scheme、host、port，否则在发送 HTTP 前抛出静态消息的 IOException，现有结果边界映射为 Connection。带 URL 用户名/密码的请求同样被拒绝。
- TokenProvider 是 Authorization 的唯一来源。清理逐请求 Authorization、Proxy-Authorization、Cookie、Cookie2 后再注入 Token。配置禁止这些头与 Host。逐请求 Host 被移除，由 OkHttp 为目标生成正确的 HTTP/1.1 Host 或 HTTP/2 authority。
- 自定义配置头如 X-Api-Key 只能到达该来源。工厂拒绝对别的来源发起请求，避免任意头继承。第三方客户端的字段来源仍需应用审查。
- CookieJar、Authenticator、proxyAuthenticator 显式禁用。Cookie 登录或自动刷新需要业务另行设计。
- 所有重定向均关闭，包括同来源及 HTTPS → HTTP。3xx 保留给调用者，响应边界输出 Http。应用若决定跟随 Location，要重新审查信任来源、方法、正文和凭据。
- 生产保留系统证书校验和主机名验证。测试通过 newBuilder 仅替换测试信任根。两套服务各自生成证书，私钥只存在测试内存中。okhttp-tls 仅为 testImplementation。

## 写请求与 OkHttp 行为

默认对所有非 GET/HEAD 请求采取保守策略。关闭连接恢复，同时将 RequestBody 包装为 one-shot，委托原类型、长度和写入行为。无正文 DELETE 等操作使用零长度 one-shot body。HTTP 方法用于选择默认防护，业务是否幂等仍由接口契约决定。相同的保护也应用于第三方客户端。

| OkHttp 路径 | 工厂防护 |
| --- | --- |
| I/O 连接恢复、部分 408 follow-up | retryOnConnectionFailure false |
| 401 / 407 认证挑战 | Authenticator 和 proxyAuthenticator NONE |
| 301/302/303/307/308 | 两种重定向开关均关闭 |
| 503 + Retry-After 0 | one-shot body 令内部 follow-up 停止，并保留原始状态 |
| HTTP/2 合并连接上的 421 | OkHttp 在 one-shot 情况停止重放；精确来源限制也阻止客户端跨来源请求。测试包含普通 421，未专门强制合并连接分支 |
| 取消 | Retrofit 取消真实 Call，结果边界继续传播 CancellationException |

读取请求也关闭连接恢复，但 GET/HEAD 无正文时仍可能走库的 503 等状态 follow-up。应用应确保它们没有副作用。显式幂等写入仍沿默认防护，幂等键不会自动开启重试。后续若需要重试，应确认服务端键范围、过期时间和去重行为，并保持相同键和语义，增加实际次数与失败测试。factory 不实现通用重试框架。

防护范围是一个 Call 的客户端自动行为。响应超时或丢失时，服务端可能已经提交。用户重复点击、应用重新创建 Call、代理或服务端重试都可能重复执行。exactly-once 需要服务端去重、幂等键及必要的结果查询协议。

按固定版本源码核对上述分支。[OkHttp 4.12.0 follow-up](https://github.com/square/okhttp/blob/parent-4.12.0/okhttp/src/main/kotlin/okhttp3/internal/http/RetryAndFollowUpInterceptor.kt) · [RequestBody one-shot 契约](https://github.com/square/okhttp/blob/parent-4.12.0/okhttp/src/main/kotlin/okhttp3/RequestBody.kt) · [Client 默认设置](https://github.com/square/okhttp/blob/parent-4.12.0/okhttp/src/main/kotlin/okhttp3/OkHttpClient.kt)。

## 实际请求与日志验证

新增 NetworkSecurityTest 共 13 项，使用生产工厂，再注入测试证书信任；响应边界原有 24 项继续执行。下列数量均检查服务端 RecordedRequest，并核对有请求的场景的方法、路径和正文。

| 场景 | 服务端预期与结果 |
| --- | --- |
| 同来源两次正常 HTTPS | 收到两次 Bearer Token 与配置 X-Api-Key；手动 auth 被覆盖，Cookie/Proxy-Authorization/Cookie2 均未收到；Set-Cookie 未持久化 |
| 不同端口、host 或 scheme 的直接访问 | 受保护客户端抛出异常；两个 HTTPS 目标和 HTTP 目标均收到零次 HTTP |
| 独立第三方客户端 | 收到一次正常请求，Authorization、Cookie、应用 X-Api-Key 均为空 |
| GET 的 5 类重定向 × 4 类目标 | 来源只收到 20 次 /start；同来源 next、跨 host/port 与 HTTP 降级均未收到跟随请求 |
| POST/PUT/PATCH/DELETE × 401/407/408/421/503 | 20 组各收到一次原始方法、路径和正文，无追加请求。未配置 HTTP 代理的 407 被 OkHttp 视为协议错误 |
| 4 种写方法 × 5 类跨来源重定向 | 20 组各来源一次、目标零次；未改变方法或正文 |
| POST 超时、发出后响应丢失 | 各收到一次完整 POST，无重发；服务端结果未知 |
| POST 发送中断开 | 记录一次请求与部分正文，无重发 |
| TLS 建立前断开 | 一次连接尝试；服务器记录一次空连接占位，零次 HTTP 执行，无第二次连接 |
| 挂起中的 HTTPS POST 取消 | 收到一次完整 POST，底层 Call 取消，未发布结果，无额外请求 |
| 默认 TLS 信任 | 自签测试证书被拒绝，服务器零次 HTTP |
| 客户端日志 | 捕获 okhttp3 的标准 Java 日志通道，排除测试服务端的日志；Token、API key、Cookie、响应 Cookie、正文和查询哨兵均未出现。核对无 HTTP logging interceptor |

日志策略是默认没有请求/响应内容输出。应用新增的 logger、SDK、builder 配置与拦截器必须独立审查，尤其不能把异常消息或完整 URL 写入日志。此次捕获无法证明任意外部日志设施安全。

## 修改与兼容性

Recipe 从 0.2.0 提升到 0.3.0。响应结果类型、DTO 校验、Repository 公共签名及取消语义保留。客户端的来源约束、Cookie/手动 auth 清理、连接恢复和无正文写请求行为均有可见变化，Cookie 认证、动态 URL 和自定义客户端需要迁移评审。

变更集中在现有 Network.kt、NetworkTest、Usage、新增的 NetworkSecurityTest 模板与 manifest；同步 CLI 打包副本、android-network Skill/版本门禁和仓库自有示例。新增生产依赖为零，新增 testImplementation 为 okhttp-tls 4.12.0。CLI 安装流程沿用原机制。

用真实旧 0.2.0 安装工程执行新 CLI plan/install，版本门禁拒绝写入，原记录、工具链和受管文件快照保持一致。旧 0.1.1 和 0.2.0 记录的零写入门禁均有 Python 回归。新安装重复执行为 already-installed，修改受管源码仍被哈希保护。原始 MyApplication 未改动。

## 验收结果

| 验收范围 | 实际结果 |
| --- | --- |
| Python 单元与安装集成回归 | 88 项通过 |
| JVM 响应边界与取消回归 | 24 项通过 |
| JVM 双 HTTPS 安全集成 | 13 项通过，覆盖表中各组实际请求，包含 OkHttp 503 对照 |
| 已有工程 · Kotlin 2.0.21 / JVM 11 | assembleDebug + testDebugUnitTest 通过，37 项 |
| 已有工程 · Kotlin 2.2.20 / JVM 17 | assembleDebug + testDebugUnitTest 通过，37 项 |
| 新建 Lightweight · Compose + Coil | assembleDebug + testDebugUnitTest 通过，41 项 |
| 新建 Standard · Compose + Coil + Hilt | assembleDebug + testDebugUnitTest 通过，41 项 |
| 既有应用自有订单代码 · 新独立工程 | assembleDebug + testDebugUnitTest 通过，43 项，含原 6 项订单测试 |
| 旧 0.2.0 安装保护 | 新 plan/install 拒绝升级且零写入，旧受管文件快照一致 |
| 当前安装和 Skill 门禁 | 兼容性脚本检查重复安装零写入；Skill gate 对 wheel CLI 放行，受管哈希均为 ok |

五个 Android 工程均使用 JDK 17、AGP 8.13.1、Gradle 8.14.3、compileSdk 36，产出 debug APK，测试零失败、零跳过。Kotlin 2.0.21 的验证仍限纯 Kotlin Android 网络模块。订单工程复用 Phase 1 会话的应用源码，本轮由脚本准备独立工程和执行回归。

[机器可读结果及源码哈希](validation/network-phase2/summary.json) · [实际请求计数](validation/network-phase2/request-counts.txt) · [旧实现失败](validation/network-phase2/jvm-red.txt) · [最终 JVM 结果](validation/network-phase2/jvm-green.txt)。Android 构建原始日志在同一证据目录。临时完整工程位于 `<network-test-root>`。

## 持续开发与下一阶段

现有 Skill 和生成 Usage 要求 Agent 在新增 API 前记录信任域、认证来源、重定向、写操作副作用、重试权限、幂等键契约及敏感头。复用所选来源的客户端，在应用自有源码扩展 Service/DTO/Repository 和测试。涉及认证/URL 需双 HTTPS 验证，涉及写入需实际方法、正文、次数及取消证据。升级既有受管实现是独立评审动作。

本轮证据限于固定版本的 JVM 集成测试和 Android debug 构建/本地单测。真实后端、代理基础设施、设备 TLS 提供者及 release/R8 仍需对应环境验证。下一阶段可先为一个真实写接口明确幂等键和结果查询契约，再验证丢失响应后的恢复行为。
