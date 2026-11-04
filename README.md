# Android Stack Skills

[English](README_EN.md)

面向多种 AI Coding Agent 的 Android 开发 Skills，通过经过验证的 Recipe 安全集成成熟技术栈。

通过自然语言创建 Kotlin Android 工程、为已有项目集成技术栈，并运行 Gradle 验证。Skills 遵循开放的 [Agent Skills 规范](https://agentskills.io/specification)，适用于能访问本地工程和执行命令的宿主。

## 为什么需要它

Agent 理解需求，Recipe 提供经过验证的实现，CLI 负责确定性安装和验证。固定的封装和依赖版本让结果可复现，安装计划让你在修改前审查变更与冲突。

## 快速开始

通过 Agent 使用时，分别安装 Skills 和 CLI。直接使用命令行时，只需安装 CLI。

### 1. 安装 Agent Skills

需要 Node.js 和 npm。在目标项目目录运行，然后选择你的 Coding Agent。

```sh
npx skills add smallmarker/android-stack-skills
```

### 2. 安装 Android Stack CLI

需要 Python 3.11+ 和 pipx。安装后，在 Agent 能执行命令的环境中运行下列检查。若找不到 CLI，运行 `pipx ensurepath` 后重新启动宿主。

```sh
pipx install git+https://github.com/smallmarker/android-stack-skills.git@main
android-stack version
android-stack recipes list
android-stack capabilities --json
```

此命令安装当前开发版 CLI。Skills 会在修改工程前检查 CLI 与 Recipe 的兼容性。缺少兼容 CLI 时，Skills 会引导准备，并在安装前征求批准。详见 [能力协议](docs/agent-compatibility.md#能力协议)。

### 3. 开始使用

将下面的请求发给 Agent。构建需要配置 JDK 17、Android SDK Platform 36 / Build Tools 35.0.0，并能访问 Gradle 和 Maven 依赖。

> 使用 Android Stack Skills 创建一个 Kotlin Android 项目，采用 XML + ViewBinding、Standard MVVM、Glide、Retrofit、Timber 和 Hilt，并运行 Gradle 构建验证。

## 功能与技术栈

- **Lightweight** 使用单模块 Kotlin + MVVM，直接构造 Repository。
- **Standard** 增加 Hilt 和 Repository 接口与实现。
- 两个预设都集成 Retrofit + OkHttp、Timber 和所选图片库，并共享 ViewModel 与 StateFlow。

| UI | 图片加载 |
|---|---|
| Compose | Coil（默认） |
| XML + ViewBinding | Glide（默认） |
| Compose | Glide（显式选择，通过 AndroidView） |
| XML + ViewBinding | 当前 Coil Recipe 仅提供 Compose API |

XML + Coil 的限制来自本项目的 `coil-standard` Recipe。Coil 库本身也支持 Android Views。

## 创建工程

```sh
android-stack create --name StandardDemo --package com.example.standard --preset standard --ui xml --output ./StandardDemo
```

默认使用 Compose。需要在 Compose 中使用 Glide 时，指定 `--ui compose --image glide`。创建默认运行 `assembleDebug` 和 `testDebugUnitTest`，失败时保留工程和日志。使用 `--skip-verify` 可仅生成工程，结果会标记为未验证。已有输出目录受到保护。

可在 Android Studio 打开 [Lightweight 示例](examples/lightweight-app) 和 [Standard 示例](examples/standard-app)。

## 已有工程集成

```sh
android-stack inspect --project ./MyApp --json
android-stack plan --project ./MyApp --recipe retrofit-standard
android-stack install --project ./MyApp --recipe retrofit-standard --verify
```

同样的流程适用于 `coil-standard`、`glide-standard` 和 `timber-standard`。多模块工程可用 `--module :app` 选择目标模块。通过 `inspect` 的 `image_libraries` 选择现有图片库对应的 Recipe，并按生成的 `app/android-stack/*/Usage.md` 完成初始化。

安装计划可只读预览。CLI 复用版本匹配的依赖，遇到版本或源码冲突时停止。重复安装会核验已安装内容并保持文件原样。已有工程需要 Kotlin DSL、显式 namespace 和 minSdk。Network 和 Image Recipe 需要 INTERNET 权限。缺少权限时，可用 `plan --add-internet-permission` 审查 Manifest 变更，明确授权后再为 `install` 传入 `--add-internet-permission`。

## 支持的 Coding Agents

Codex 已完成安装、自然语言触发、CLI 调用和 Android 构建验证。Claude Code、Cursor、OpenCode 和 GitHub Copilot 已验证安装器文件放置，完整工作流待验证。详见 [Agent 兼容性矩阵](docs/agent-compatibility.md)。

```sh
npx skills add smallmarker/android-stack-skills --agent codex
npx skills add smallmarker/android-stack-skills --agent claude-code
npx skills add smallmarker/android-stack-skills --agent cursor
npx skills add smallmarker/android-stack-skills --agent opencode
npx skills add smallmarker/android-stack-skills --agent github-copilot
```

默认安装到当前项目。添加 `--global` 安装到用户级，或使用 `--skill` 选择单个 Skill。

```sh
npx skills add smallmarker/android-stack-skills --skill android-project
npx skills list --agent codex
```

查看用户级安装时，在 `list` 命令中添加 `--global`。重新打开目标项目，然后请 Agent 查找 `android-project` 以确认宿主能发现它。

## 高级安装

### 手动安装（高级用法）

将所需的完整 Skill 目录从仓库的 `skills/` 复制到宿主文档指定的目录。以 Codex 为例，项目级可用 `.agents/skills/`，用户级可用 `~/.agents/skills/`。其他宿主请按各自的发现路径配置。复制前先比对已有同名目录。

如果从 wheel 安装，可在安装了 CLI 的 Python 环境中定位随包分发的 Skills。

```sh
python -c 'from importlib.resources import files; print(files("android_stack_skills").joinpath("data", "skills"))'
```

## 兼容性与限制

已验证的构建基线为 AGP 8.13.1、Gradle 8.14.3、Kotlin 2.2.20、Compose BOM 2025.08.01，验证环境为 macOS arm64 和 JDK 17，生成工程支持 Android API 26+。XML / Glide 的 Android Studio、设备和图片显示体验仍待人工验证。

当前自动集成范围排除 Groovy 写入、AGP 9 内置 Kotlin、动态依赖和 bundles、自定义 projectDir / includeBuild、复杂 convention plugin、多平台迁移和自动合并已有 ImageLoader。构建日志与中断恢复说明见 [测试文档](docs/testing.md)。

构建日志保存在 `.android-stack/verification.log`。安装中断后，先确认没有其他进程持有安装锁，再运行 `android-stack recover --project ./MyApp`。恢复会保护中断后的用户编辑。

Early Preview 源码已公开在 GitHub 的 `main` 和 [`v0.2.0` 标签](https://github.com/smallmarker/android-stack-skills/tree/v0.2.0)。目前通过 Git 安装，尚未发布 GitHub Release 或 PyPI 包。

## 文档与贡献

[架构](docs/architecture.md) · [Android 兼容性](docs/compatibility.md) · [Recipe 协议](docs/recipe-spec.md) · [测试](docs/testing.md) · [贡献](CONTRIBUTING.md) · [路线图](docs/roadmap.md)

[android-project](skills/android-project/SKILL.md) · [android-network](skills/android-network/SKILL.md) · [android-image](skills/android-image/SKILL.md) · [android-logging](skills/android-logging/SKILL.md)
