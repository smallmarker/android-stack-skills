# Network Architecture v1 · Phase 1 验收

2026-11-05 · [Foundation](architecture-foundation-v1.md) · [Network Architecture](network-architecture-v1.md)

## 缺陷与根因

先把两个预期失败的测试加到旧网络实现上。隔离 JVM 测试执行 16 项，14 项通过，新增的两项失败。204 被 Retrofit 解析为没有 body 的成功响应，原 `suspend getUser(): User` 在收到 null 时抛出空指针。Gson 用缺省字段构造 `User`，因此 `{}` 进入成功分支，产生 `id=0` 和违反 Kotlin 非空声明的 `name=null`。两个入口都缺少应用可验证的响应边界。[Phase 0 复现记录](architecture-audit-v1.md#网络边界的实测复现)。

## 0.2.0 的响应边界

Service 返回 `Response<UserDto>`。Repository 用 `safeApiResponse` 处理 HTTP 和必需响应体，再调用纯 mapper 校验 DTO 并构造 `User`。实际转换器使用固定版本 Gson 的严格 JSON 配置，空白但非零字节的响应按 JSON 解析。Retrofit 直接处理 204/205，零字节 JSON 响应经轻量 converter 交给相同的缺体分支。用于判断字段的 `JsonElement` 保留 token 类型，`@SerializedName` 固定 wire 字段名。样例只接受 Long 范围内的正 JSON 整数和非空白字符串。其他接口按自身契约选择类型、范围、默认值及空值语义。

| 输入 | 结果 |
| --- | --- |
| 有效 2xx + DTO | `Success(User)`，上层不依赖 Gson DTO |
| 必需体遇到 204/205、零字节 2xx、JSON null | `MissingBody` |
| 明确允许空成功的端点 | `Response<Unit>` 与 `safeEmptyApiResponse`，成功返回 `Unit` |
| JSON 语法错误或不可解码顶层结构 | `Parsing` |
| 必需字段缺失或 null | `InvalidField(field, MissingOrNull)` |
| wire 类型或表示范围不符 | `InvalidField(field, WrongType)` |
| 合法 wire 类型违反端点约束 | `InvalidField(field, Constraint)` |
| 非 2xx | `Http(status)`，关闭 error body |
| 已知 I/O、超时 | `Connection` 或 `Timeout` |
| 调用取消 | 传播 `CancellationException`。在请求前、生成结果后及映射边界检查活跃状态。Retrofit 取消底层 Call |

原有 `safeApiCall` 保留并继续传播程序错误。mapper 在 transport 异常捕获范围外执行。字段错误只携带静态 schema 字段名与原因。

## 文件、版本与已有安装

- [Recipe manifest 与模板](../recipes/network/retrofit-standard)是维护入口，[CLI 打包资源](../src/android_stack_skills/data/recipes/network/retrofit-standard)是运行时来源。安装已有工程及 Lightweight / Standard 生成入口都调用同一 Recipe。发布模板、打包副本、仓库内两个示例及其网络文件哈希已同步。
- [android-network Skill](../skills/android-network)及其[打包副本](../src/android_stack_skills/data/skills/android-network)增加增量工作流。Usage 说明如何在应用自有源码新增 API、使用同一客户端及结果类型、校验映射、测试和核对归属。
- `ApiResult`、`safeApiCall`、`User`、`UserRepository.getUser()` 保留 API 形状。直接调用示例 `UserApi.getUser()` 的代码需适配 `Response<UserDto>`。穷举 `ApiError` 的调用方需处理新增分支。严格 JSON 也需要评估原来接受宽松输入的端点。
- 旧 0.1.1 记录在同版 CLI 下重装为 `already-installed`。0.2.0 CLI 的 plan/install 遇旧记录会提示人工迁移并保持零写入，其 CLI verify 也受同一版本门禁约束。旧项目可沿用原工具或直接运行项目 Gradle；新增 API 可在应用自有边界适配。既有用户安装、工具链和原始 MyApplication 未迁移。

## 回归

| 检查 | 结果 |
| --- | --- |
| Python 全量 | 87 项通过，含新增的版本门禁零写入回归，以及既有哈希、冲突和 Java/Kotlin/mixed/custom 源码布局测试 |
| 网络 JVM | 24 项通过，保留原有 14 项覆盖并增加 10 项。新增覆盖必需体、空成功、字段校验、预取消及真实在途取消。收到请求后取消调用，OkHttp 报告 Call 已取消，mapper 和结果发布均未执行 |
| 0.1.1 旧记录 | 用旧版 CLI 实际安装后同版重装零写入。用新 wheel 的 plan/install 均拒绝自动升级，记录及所有受管哈希仍匹配 |
| 本地 wheel | 离线装入临时环境，从该 wheel 验证真实入口，能力声明为 retrofit-standard 0.2.0 |
| 已有 Android 工程 · Kotlin 2.0.21 / JVM 11 | 安装、幂等、assembleDebug、testDebugUnitTest 均通过，24 项 |
| 已有 Android 工程 · Kotlin 2.2.20 / JVM 17 | 安装、幂等、assembleDebug、testDebugUnitTest 均通过，24 项 |
| Lightweight · Compose + Coil | 从 wheel 新建，assembleDebug、testDebugUnitTest 均通过，28 项 |
| Standard · Compose + Coil + Hilt | 从 wheel 新建，assembleDebug、testDebugUnitTest 均通过，28 项 |
| 独立订单工程 · Kotlin 2.2.20 / JVM 17 | assembleDebug、testDebugUnitTest 均通过，30 项 |

Android 矩阵使用 JDK 17、AGP 8.13.1、Gradle 8.14.3 与 compileSdk 36，各工程产出 debug APK，测试零失败、零跳过。兼容性脚本逐一核对原有工具链文件与重复安装前后快照。最初临时 Gradle 缓存缺少 Kotlin 2.0.21 插件，改用从本机复制的完整缓存离线重跑后通过。

## 独立的第二个 API

从一个已有 `AppGraph` 的空白 Android 工程安装 0.2.0。随后启动真实的 `codex exec --ephemeral` 会话，要求读取 wheel 内的 Skill、项目决策和生成 Usage，按给定契约实现 `GET orders/{id}`。会话在应用自有的 Java 源根（其中编译 Kotlin）中新增 `OrderRepository.kt` 和 `OrderRepositoryTest.kt`，在现有 AppGraph 注入同一个 Retrofit。它复用了 `safeApiResponse` 和 `ApiResult`，增加 6 项 MockWebServer 测试，包括成功模型和路由、必需字段、错误类型、约束、空/非法响应体和 HTTP 404/500。

独立会话尝试运行 Gradle 时，sandbox 拒绝文件锁服务的本机套接字。外层验收对同一份源码运行 wheel 的 `verify`，完成真实 Gradle 构建和 30 项测试（24 项网络、6 项订单）。安装后与增量开发后进行快照比对，已有文件中只有应用自有 `AppGraph.kt` 发生改变。安装记录、全部受管文件哈希、依赖声明与 Wrapper 一致。会话没有调用 Recipe 安装或引入第二个生产客户端。此次结果验证的是给定契约和单模块手动装配下的增量工作流。

临时证据目录为 `<network-test-root>`。其中 `jvm-red.log` 与 `jvm-green.log` 记录红绿测试，`compatibility-retry.jsonl`、`lightweight.json`、`standard.json` 和 `order-verification.json` 记录构建入口及结果。`order-codex.jsonl` 保留独立会话，`order-drill` 保留演练工程和测试产物。

## 下一阶段

优先将真实网络测试从目前共享 converter 的 HTTP 夹具扩展到生产工厂的 HTTPS 路径。用双 origin 和测试证书验证凭据隔离，并以实际请求数测试重放边界。现有工厂保持原重试行为，当前验收未覆盖写请求重放、真实后端、设备或 release/R8。会话刷新和缓存仍由业务需求触发。
