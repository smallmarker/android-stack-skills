# Android Stack Skills

Production-ready Android stacks, powered by Agent Skills.

面向 Android 开发者的确定性技术栈集成工具：Agent 理解需求，Recipe 提供固定实现，Python CLI 生成可审查计划、安全安装，再通过真实 Gradle 构建验证。

V1 的 CLI、三个技术栈 Recipe、Lightweight / Standard 预设和四个 Skills 已实现。真实验证结果与未验证项见 [交付报告](docs/delivery.md) 和 [开发进度](docs/progress.md)。不将“生成成功”等同于“编译成功”。

## 为什么需要它

普通 Agent 每次可能生成不同封装与依赖组合。本项目将可复用的 Kotlin 实现、依赖版本、错误处理、测试和集成策略固定为 Recipe，同时保留 Agent 对非标准工程的适配能力。没有通用插件市场、自动架构迁移或跨大版本升级。

## 安装

**Early Preview 0.2.0**。通过 Codex 使用需要分别安装 Agent Skills 和 Python CLI。

CLI 需要 Python 3.11+。Android 构建需要 JDK 17、Android SDK Platform 36 / Build Tools 35.0.0 和 Maven / Gradle 网络访问。

### Agent Skills (Codex)

在目标 Codex 项目根目录执行以下命令，将四个 Skills 安装到当前 Codex 项目。加上 `--skill android-project` 可只安装工程生成 Skill。

```sh
npx skills add smallmarker/android-stack-skills --agent codex
```

### Python CLI

```sh
pipx install git+https://github.com/smallmarker/android-stack-skills.git@v0.2.0
android-stack --help
android-stack version
android-stack recipes list
```

也可在独立虚拟环境中安装本地构建的 wheel。 `android_stack_skills-0.2.0-py3-none-any.whl`

若 Codex 找不到 Skill，请确认在目标项目内安装并重新打开会话。若找不到 `android-stack`，请检查 `pipx ensurepath` 并重启启动 Codex 的终端。依赖冲突时先查看 `android-stack plan` 的输出。

## 创建工程

```sh
export ANDROID_HOME="$HOME/Library/Android/sdk"  # 按本机 SDK 位置设置
android-stack create --name DemoApp --package com.example.demo --preset lightweight --output ./DemoApp
android-stack create --name StandardDemo --package com.example.standard --preset standard --ui xml --output ./StandardDemo
android-stack create --name GlideCompose --package com.example.glidecompose --ui compose --image glide --output ./GlideCompose
```

默认创建后执行 assembleDebug 和 testDebugUnitTest；失败返回非零，保留工程与日志。仅需离线生成时显式添加 `--skip-verify`，结果会标记为未验证。已存在的输出目录一律拒绝覆盖。

省略 `--ui` 时使用 Compose。省略 `--image` 时，Compose 选 Coil，XML 选 Glide。可以显式指定 `--ui compose --image glide`，模板通过 `AndroidView` 使用 Glide。XML + Coil 会在创建目录前报错，因为现有 `coil-standard` 提供 Compose 的 AppImage API。

Lightweight 使用单模块 MVVM 与直接构造的 Repository。Standard 增加 Hilt、Repository 接口与实现。XML 由 Activity 使用 ViewBinding 并按生命周期收集 ViewModel 的 StateFlow。两个 UI 共用 ViewModel、Repository、Network 和 Logging。

可直接在 Android Studio 打开 [Lightweight 示例](examples/lightweight-app) 或 [Standard 示例](examples/standard-app)。

## 给已有工程集成

```sh
android-stack inspect --project ./MyApp --json
android-stack plan --project ./MyApp --recipe retrofit-standard
android-stack install --project ./MyApp --recipe retrofit-standard --verify

android-stack plan --project ./MyApp --recipe coil-standard
android-stack install --project ./MyApp --recipe coil-standard --verify

android-stack plan --project ./MyApp --recipe timber-standard
android-stack install --project ./MyApp --recipe timber-standard --verify

android-stack status --project ./MyApp
android-stack verify --project ./MyApp
```

多 Android 模块时向 inspect/plan/install/verify 添加 `--module :app`。`plan` 不写工程；`install --dry-run` 仅预览 Diff。`--json` 输出结构化报告。`install` 默认仅安装并标记 `installed-unverified`，`--verify` 才执行真实构建。

现有依赖版本完全相同时复用；不同或未知时报告冲突，绝不静默升级。模板文件或同包 Kotlin 声明冲突时停止安装。已安装但源码被修改时报告漂移；重复安装不改文件。

已有工程需启用 Kotlin、显式 namespace 和 minSdk，Coil Recipe 需要 Compose，Glide Recipe 使用 ImageView。Network/Image 安装前需声明 INTERNET 权限。安装器只追加独立依赖块，不尝试重写任意 Gradle 程序。不会擅自替换已有 Application：初始化方式见生成的 `app/android-stack/*/Usage.md`。

```kotlin
// network: 真实端点由应用提供；safeApiCall 保留协程取消语义。
val api = HttpClientFactory.retrofit(NetworkConfig("https://api.example.com/"))
    .create(UserApi::class.java)
val result = UserRepository(api).getUser() // 在 coroutine 内调用

// Application.onCreate
AppImages.initialize(this)
AppLogger.initialize(BuildConfig.DEBUG)

// Compose；支持 CircleShape、placeholder/error Painter 与 loading/failure 插槽。
AppImage(url = avatarUrl, shape = CircleShape, contentDescription = "User avatar")
AppLogger.d("Home", "Page created")
```

Hilt 工程安装 Network 后，应用必须提供 `NetworkConfig` 和 `TokenProvider` 绑定；Standard 已提供可替换的示例绑定。日志自由文本只允许静态开发消息；动态数据使用 `LogField` 白名单。Release facade 静默，异常仅记录类型，不声称可自动清洗任意文本。

对于已有图片库，`inspect` 在所选模块中报告 `image_libraries`。使用现有库对应的 Recipe。计划会拒绝引入另一套图片库或覆盖不同版本。Glide 集成示例：

```sh
android-stack plan --project ./MyApp --recipe glide-standard
android-stack install --project ./MyApp --recipe glide-standard --verify
```

在 ViewBinding 的 ImageView 上调用 `binding.preview.loadGlide(url, placeholder = R.drawable.loading, error = R.drawable.unavailable)`。组合与构建结果见 [兼容性矩阵](docs/compatibility.md#v11-ui-与图片库)。

## 安装 Agent Skills

先安装上述 CLI，然后从本仓库复制四个 Skill 文件夹到目标工程；若目标已有同名目录，先比对内容，不覆盖已有自定义 Skill。

```sh
mkdir -p /path/to/MyApp/.agents/skills
cp -R skills/android-project skills/android-network skills/android-image skills/android-logging /path/to/MyApp/.agents/skills/
```

仅通过 wheel 安装时，可用下面命令找到随包分发的 Skill 源目录，再复制四个子目录；已有同名目录应先比对，不能直接覆盖。

```sh
python -c 'from importlib.resources import files; print(files("android_stack_skills").joinpath("data", "skills"))'
```

用户级目录为 `~/.agents/skills/`。这些路径已按 [OpenAI 官方 Skills 文档](https://learn.chatgpt.com/docs/build-skills) 核实（2026-11-02）；Codex 会从工作目录向仓库根查找 `.agents/skills`。如未发现，重启宿主。其他 Agent 的安装路径应按其各自文档设置；文件格式遵循 [Agent Skills 规范](https://agentskills.io/specification)。

四个入口：

- [android-project](skills/android-project/SKILL.md)：创建 Compose 或 XML/MVVM 工程。
- [android-network](skills/android-network/SKILL.md)：Retrofit / OkHttp 集成与状态检查。
- [android-image](skills/android-image/SKILL.md)：根据现有依赖和 UI 选择 Coil 或 Glide。
- [android-logging](skills/android-logging/SKILL.md)：Timber 日志集成。

示例：“给当前项目集成 Retrofit”“创建一个 Standard Compose 项目”“检查网络 Recipe 是否已安装”。Skill 将调用同一 CLI，不复制 Kotlin 封装。格式校验与独立 Codex 会话验收结果见 [RC 报告](docs/delivery.md)；不代表所有 Agent 宿主均已验证。

## 支持范围与恢复

构建基线为 AGP 8.13.1、Gradle 8.14.3、Kotlin 2.2.20、Compose BOM 2025.08.01；完整版本、来源和最新版审计见 [兼容性](docs/compatibility.md)。当前验证 macOS arm64 / Java 17 / API 26+ Android 应用，支持 Compose 与 XML ViewBinding。

V1 不支持 Groovy 自动写入、AGP 9 built-in Kotlin、动态依赖 / bundles / 自定义 projectDir / includeBuild、复杂 convention plugin、多平台工程或已有 ImageLoader 自动合并。未知版本会明确提示验证风险，不宣称已兼容所有工程。

中断安装会保留 `.android-stack/journal.json`。确认没有其他进程持有锁后执行 `android-stack recover --project ./MyApp`。恢复拒绝覆盖后续用户编辑；真实编译错误保存在 `.android-stack/verification.log`，验证失败不会被报告为成功。

[架构](docs/architecture.md) · [Recipe 协议](docs/recipe-spec.md) · [测试](docs/testing.md) · [贡献](CONTRIBUTING.md) · [路线图](docs/roadmap.md) · [English](README_EN.md)
