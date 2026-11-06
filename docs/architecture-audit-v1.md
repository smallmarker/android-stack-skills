# 四个 Skill 的架构成熟度审查

审查日期：2026-11-04。以本地仓库 `b20cb40` 和当前工作树为准。定义三个成熟度级别：L1 可复现集成，L2 有边界的参考实现，L3 有决策依据、持续开发指导和可重复架构验收。级别按最有代表性的能力评估。

## 证据与边界

- 对照了 [四个 SKILL.md](../skills)、[六个 Recipe manifest 与模板](../recipes)、[项目骨架](../src/android_stack_skills/data/project-templates)、[Compose/XML 骨架](../src/android_stack_skills/data/project-ui)、[CLI](../src/android_stack_skills/cli.py)、[生成器](../src/android_stack_skills/generator.py)和[测试](../tests)。四个仓库 Skill 目录和打包副本一致，Recipe 目录与打包副本一致。
- Inspector 静态识别声明、模块及源根；Resolver 校验兼容性、依赖、冲突、权限及文件计划；Installer 用计划前镜像、锁、journal 和 hash 保护交付。Validator 验证选中模块的安装状态并运行 `assembleDebug`、`testDebugUnitTest`。工具可保护既有代码和依赖，但不会分析业务调用链与分层语义。参考 [CLI 架构](architecture.md)、[Validator](../src/android_stack_skills/validator/__init__.py)。
- 本轮运行 `.venv/bin/python -m pytest -q`，**86 通过**。这些测试主要验证安装契约、冲突、并发改动、回滚、源根、兼容性、分发和 CLI 行为。历史 Android 证据包括已有工程隔离矩阵、生成项目的 debug 构建/单测，以及日志 release 夹具。Kotlin 2.0.21 实测适用范围仅为文档列出的 Retrofit 纯 Kotlin Android 组合，Compose/Hilt 沿单独基线。历史矩阵不能外推到任意工具链、真实设备、真实后端或生产缩减构建。[兼容性记录](compatibility.md) · [测试范围](testing.md) · RC 原始证据（本地历史留档）。

## android-project — L2 初级参考骨架

| 问题 | 发现 |
| --- | --- |
| 1 解决什么 | 可重复生成单 app 模块；Lightweight 和 Standard 共用骨架及三类 Recipe，提供 Compose/XML 入口和构建校验。 |
| 2 集成还是模式 | 有 MVVM 和两种 DI 装配样例。主页只取本地固定字符串，独立网络示例没有进入主页调用链。 |
| 3 分层职责 | 包区分 ui/data/network，ViewModel 消费 HomeRepository；没有通用依赖规则或应用/DTO 边界门禁。 |
| 4 选型原因 | Skill 给出小项目用手动装配、需要 Hilt/接口用 Standard。缺少何时拆模块、何时加 Domain 或接口的业务依据。 |
| 5 适用范围 | 新建 Kotlin 单模块。XML 默认 Glide，Compose 默认 Coil；生成器支持 Compose + Glide，拒绝 XML + Coil。 |
| 6 生命周期、异常、安全、性能 | 生命周期感知收集、viewModelScope、取消重抛、无真实凭据、Wrapper 校验。HomeViewModel 广泛捕获 Exception 且 refresh 每次独立 launch；固定 greeting 隐藏了异步竞态和故障语义问题。 |
| 7 既有工程 | create 拒绝覆盖目录；适配由单项 Skill 与现有应用代码承担。 |
| 8 增量 | README/Usage 可作起点，缺少持久架构决策和继续修改 ViewModel/Repository 的验收流程。 |
| 9 测试 | 生成测试校验变体，Gradle 编译与执行单测；HomeRepositoryTest 只断言固定字符串，未验证状态机、重复触发和依赖边界。 |
| 10 普通 AI 可等效处 | 基础 MVVM、Hilt 与 UI 样例易复现。差异在相同可核对的版本、交付保护和可重复运行证据。 |

证据：[Skill](../skills/android-project/SKILL.md) · [Lightweight](../recipes/project/lightweight/recipe.yaml) · [Standard](../recipes/project/standard/recipe.yaml) · [项目模板](../src/android_stack_skills/data/project-templates) · [生成测试](../tests/unit/test_generator.py)。

## android-network — L2 传输层参考实现

| 问题 | 发现 |
| --- | --- |
| 1 解决什么 | 固定版本 Retrofit/OkHttp、类型化传输结果、应用配置、来源限定 header/token、可选 Hilt、真实 HTTP JVM 测试。 |
| 2 集成还是模式 | 有传输边界实现。UserRepository 直接返回 Gson 解码的 User 和 ApiResult，缺少可复用的业务数据模式。 |
| 3 分层职责 | Service、示例模型、Repository 和 client 同居 Network.kt，Usage 没规定远端与公开模型或业务错误的边界。 |
| 4 选型原因 | 有真实版本兼容记录，未给出 Retrofit 与既有网络栈并存或替换的条件，也未解释 converter、接口和分层取舍。 |
| 5 适用范围 | 支持受限 Kotlin DSL 模块，明确版本/权限/源根门禁。常规 JSON 请求可起步，文件流、私有认证策略和业务 envelope 需单独设计。 |
| 6 生命周期、异常、安全、性能 | 明确 30 秒各超时和总时限、HTTPS base URL、来源匹配和禁重定向，部分异常先查取消。缺少必需空体与字段策略、明确重放限制、端到端取消证据；工厂每次调用新建客户端，非 Hilt 需自行复用。 |
| 7 既有工程 | 能选模块并保留依赖及 Application，明确权限写入与冲突处理。安装独立实现，不分析或接管已有服务、认证、DI、Repository。 |
| 8 增量 | Usage 提示替换示例、配置绑定，但未提供业务 API 的步骤、契约和审查规则；直接改受管文件还会产生 ownership drift。 |
| 9 测试 | 现有 14 个 JVM 测试覆盖 HTTP、超时、解析、部分取消映射和来源限制。取消例手动抛异常或模拟 IO，未观察真实 Call 取消；多数 MockWebServer 测试自建客户端，未走生产 TLS factory。 |
| 10 普通 AI 可等效处 | Retrofit 接口、基础拦截器和 sealed result 易生成。可核对的行为证据、兼容性矩阵和无覆盖安装更具复用性。 |

证据：[Skill](../skills/android-network/SKILL.md) · [manifest](../recipes/network/retrofit-standard/recipe.yaml) · [Network.kt](../recipes/network/retrofit-standard/templates/Network.kt.j2) · [NetworkTest](../recipes/network/retrofit-standard/templates/NetworkTest.kt.j2) · [Usage](../recipes/network/retrofit-standard/templates/Usage.md.j2) · [兼容性测试](../tests/integration/test_network_compatibility.py)。

## android-image — L1 集成，具备局部运行策略

| 问题 | 发现 |
| --- | --- |
| 1 解决什么 | Coil Compose 组件与共享缓存，或 Glide ImageView helper、占位/失败/释放；优先保留已有图片库。 |
| 2 集成还是模式 | 提供具体 UI 适配器和使用约定，缺少应用级图片引用、安全、缓存与性能契约。 |
| 3 分层职责 | 包隔离图片实现，Usage 以 UI 调用为主，缺少应用模型与鉴权客户端的边界。 |
| 4 选型原因 | 按现有库及 Compose/XML 表面选型，有避免双栈的规则，缺少图片尺寸、列表性能和缓存选择依据。 |
| 5 适用范围 | Coil Recipe 限 Compose，Glide 对 ImageView 和 Compose AndroidView；既有 XML Coil 保留但不自动生成。 |
| 6 生命周期、异常、安全、性能 | Coil 提供占位/失败/可访问描述和默认 20% 内存、64 MiB 磁盘缓存；Glide 文档要求主线程及回收清理。缺少真实列表/设备证据，私有图片及缓存隔离无决策规则。 |
| 7 既有工程 | 识别库、版本和 loader 冲突。保留 Application，由调用者选择初始化与改造位置。 |
| 8 增量 | Usage 可复用 helper。新增屏幕仍需补充对回收、私有图、尺寸和访问性的验证。 |
| 9 测试 | Glide 仅断言 RequestOptions，Coil 无专属行为测试。构建和依赖保护无法证明真实占位、回收取消或缓存表现。 |
| 10 普通 AI 可等效处 | helper 和占位样式容易复制。保护已有 loader/版本与经过验证的组合更有价值。 |

证据：[Skill](../skills/android-image/SKILL.md) · [Coil](../recipes/image/coil-standard) · [Glide](../recipes/image/glide-standard) · [安装回归](../tests/integration/test_install.py)。

## android-logging — L2 日志策略样板

| 问题 | 发现 |
| --- | --- |
| 1 解决什么 | 提供 Timber facade、可选 Hilt、默认静默、类型化字段、异常类名输出和既有树保留。 |
| 2 集成还是模式 | 已有可复用日志模式，约束只覆盖 facade，未涵盖应用级观测职责与绕行入口。 |
| 3 分层职责 | 应用初始化，业务可通过 Logger 记录事件。未规定谁拥有错误记录，调用方仍可直接用 Timber/Log。 |
| 4 选型原因 | 用 Timber 管理 Tree，约束输出字段以降低泄露风险。已有其他 facade 如何接入缺少指导。 |
| 5 适用范围 | 开发期诊断和受控结构化事件；生产遥测需独立策略。 |
| 6 生命周期、异常、安全、性能 | 初始化使用同步与 volatile，正常一次初始化；release facade 静默，异常消息与堆栈未写入。但 tag/message/event 仍是 String，事件正则只能查形状，数字字段可装业务标识，`write` 直接传入文本。 |
| 7 既有工程 | 保留已有 Application/Timber trees，支持模块选择和 Hilt，冲突时停下。 |
| 8 增量 | 有静态文案和字段提示，缺少新事件字段评审与端到端泄漏验收。 |
| 9 测试 | 测 facade 静默、异常类别与事件校验，历史有 release 夹具。未证明应用内所有 SDK/旁路安全，字段测试也未捕获一个完整结构化事件。 |
| 10 普通 AI 可等效处 | DebugTree、BuildConfig 开关和 facade 容易生成。明确字段策略、可重复的 release 捕获及既有树兼容是值得保留的差异。 |

证据：[Skill](../skills/android-logging/SKILL.md) · [Recipe 与模板](../recipes/logging/timber-standard) · release 夹具结果（本地历史留档）。

## 网络边界的实测复现

从当前 Recipe 渲染 `Network.kt` 和 `NetworkTest.kt` 到临时纯 JVM Gradle 项目，使用 JDK 17、Gradle 8.14.3、Kotlin 2.2.20，依赖沿用 manifest 版本（JVM 用 coroutines-core 1.10.2）。离线运行 `gradle --offline --no-daemon test`，原 14 个测试与下方复现探针共 **15 通过**。探针断言的是缺陷的现状；修复回归应改为期望类型化失败。HTTP 在本地 MockWebServer 上进行。本轮未重跑 Android 构建或设备矩阵。

```kotlin
// 放在渲染后的 NetworkTest 中，复用 api(server) 与既有 imports。
@Test fun requiredBodyAndMissingFields() {
    MockWebServer().use { server ->
        val service = api(server)
        server.enqueue(MockResponse().setResponseCode(204))
        assertThrows(NullPointerException::class.java) {
            runBlocking { safeApiCall { service.getUser() } }
        }

        server.enqueue(MockResponse().setBody("{}"))
        val user = runBlocking { safeApiCall { service.getUser() } } as ApiResult.Success
        assertEquals(0L, user.value.id)
        assertNull(user.value.name)
    }
}
```

204 由 Retrofit 解析成成功但无 body，非空 suspend 声明把它升级为空指针，当前 wrapper 有意放过该类异常。缺字段则显示 Gson 反射构造的对象可以违背 Kotlin 的字段声明。对应生产风险是合法 HTTP 响应触发错误路径崩溃，或无效模型在成功分支里传播。[Retrofit 响应处理](https://github.com/square/retrofit/blob/3.0.0/retrofit/src/main/java/retrofit2/OkHttpCall.java) · [非空 suspend 实现](https://github.com/square/retrofit/blob/3.0.0/retrofit/src/main/java/retrofit2/KotlinExtensions.kt)。

## Gap Analysis

P0 指可复现的安全或数据完整性问题且当前路径受影响；一旦真实业务引入可重放副作用或私密日志，则按 P0 阻断该业务路径。当前审查未证明默认生成的只读示例存在此类 P0 事故。P1 是下一阶段应修的边界与运行缺陷；P2 是条件性扩展或成熟度提升。表中“Recipe”包括其现有模板。

| 当前实现 | 目标行为 | 影响 | 架构缺陷 | Recipe | Skill | 新验证 | 优先级 | 最小方案 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Network.kt 117–124 用裸 body，Gson User 直接向外返回 | 明确 body 语义并映射稳定模型 | 204 可抛未映射异常，缺字段可产生带非法值的成功 | 是 | 是 | 是 | MockWebServer 204、空/null、缺字段、合法成功 | P1 | 在原示例内改为 Response DTO，显式校验后映射 |
| safeApiCall 的取消 guard 只在部分 catch，现有取消测试为合成异常 | 活跃检查覆盖所有映射出口，真实 Job 取消到底层 | 业务继续发布陈旧失败，真实路径缺证据 | 部分防护与验证缺口 | 是 | 是 | 在途请求取消并观测底层 Call | P1 | 共用活跃检查，保留取消重抛，先验证行为 |
| 工厂未指定 retryOnConnectionFailure，且 OkHttp 有独立 follow-up 分支 | 端点重放策略及明确可验证的写入约束 | 以后接入副作用请求可能重复提交 | 是，影响取决于调用 | 按首个真实写场景 | 是 | 统计 408/503/断线等请求数 | P1 | 先写 Usage 门禁，按业务路径引入不可重放策略 |
| header 注入限制来源，直接带凭据的动态 URL 仍可由调用方构造 | 明确可信客户端与动态 URL 契约 | 新 API 可能绕过来源意图 | 是，当前示例无动态 URL | 视引入场景 | 是 | 双 origin + TLS + redirect | P1 | 固定相对路径，动态 URL 单独评审 |
| Project HomeViewModel broad catch、每次 refresh 新开任务 | 已知失败与明确的并发策略 | 业务化后旧响应可能覆盖新状态、程序错误被吞 | 是 | 是 | 是 | ViewModel 竞态及取消 | P1 | 首个异步页面选择 latest-wins 或合并，测试状态序列 |
| Skill 入口围绕安装，manifest 标识文件归属 | 项目决策持久化、增量用业务自有源码 | Agent 可能重装或改坏受管文件 | 是 | Usage | 是 | 一次真实的新增 API 与复审演练 | P1 | 复用 ADR/README、现有 Skill/Usage |
| Logger 接受动态字符串，测试覆盖有限 | 字段来源有审查，关键调用以捕获验证 | 插值、业务标识或旁路可泄露 | 是，现有样例未证明泄露 | 先改 Usage | 是 | 秘密哨兵、release 和旁路检查 | P1 | 在实际调用处审查来源，验证结构化日志与已有树 |
| Coil/Glide 缺真实状态/回收证据，默认缓存与私有图无分流 | UI 生命周期与私有图策略可验证 | 列表错图、缓存残留风险依赖业务 | 验证和适用边界缺口 | 先改 Usage | 是 | 设备/可靠 UI 夹具 | P2 | 针对真实列表跑回收与失败场景 |
| Standard 将 Hilt 与 Repository 接口绑定，缺拆分决策 | DI、接口与模块按独立条件选择 | 小项目样例易被机械扩展 | 设计指导缺口 | 先改 Usage | 是 | 项目决策审查 | P2 | 先解释 preset 含义，等真实项目驱动模板变更 |
| 无刷新/缓存/离线内建机制 | 按真实后端和需求开启 | 过早实现会引入会话与一致性负担 | 否 | 仅触发时 | 可选指导 | 按扩展验证 | P2 | 使用已有方案的项目只需审查契约 |

## 分阶段实施

1. **本轮设计基线。** 发布仓库内 Foundation、网络样板和审查文档。CLI 工程架构文档提供入口。
2. **下一轮最小改进。** 仅修现有 `retrofit-standard` 的示例响应边界。用 `Response<UserDto>`、显式必需字段校验和应用模型映射，保持 `UserRepository.getUser(): ApiResult<User>` 与 DI 安装入口的基本形状，评估新增错误类型对 exhaustive when 的影响。对 200 合法、204/205、200 空/null、缺字段和真实在途取消做回归；补网络 Usage 与 Skill 的增量入口。同步打包副本与必要示例版本。现有已安装项目提供可审查的迁移说明，原文件不自动覆盖。验收在临时 JVM 和 Android 夹具运行现有测试，另演练在应用自有源码新增第二个 API。
3. **扩展到 Project、Logging 和 Image。** 在一条真实业务路径补 ViewModel 竞态、release 日志捕获和设备图片回收证据，确定能在各自项目持续执行的最小检查。先使用现有 Gradle 和文档。
4. **需求触发的扩展。** 按首个真实鉴权刷新、写入重放、离线或模块拆分需求，交付对应测试与决策。库升级继续走隔离兼容性验证。
