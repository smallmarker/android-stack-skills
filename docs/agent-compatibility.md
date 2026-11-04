# Agent compatibility

The same four Skills follow the open [Agent Skills specification](https://agentskills.io/specification). The host needs to discover and read `SKILL.md`, access the local Android project, execute `android-stack` and use command results to continue or report failures. The CLI and its bundled Recipes work independently of the agent. Android builds also require the environment listed in the [installation guide](../README_EN.md#4-start-using).

| Coding agent | Installer file placement | Natural-language trigger | CLI invocation | Android build |
|---|---|---|---|---|
| Codex | Verified | Verified | Verified | Verified |
| Claude Code | Verified with skills CLI | Pending | Pending | Pending |
| Cursor | Verified with skills CLI | Pending | Pending | Pending |
| OpenCode | Verified with skills CLI | Pending | Pending | Pending |
| GitHub Copilot | Verified with skills CLI | Pending | Pending | Pending |

File placement was checked with the [Vercel skills CLI](https://github.com/vercel-labs/skills) 1.5.24 using local project installs and the agent IDs in the README. A successful install confirms files were placed. Agent discovery and execution require a separate session test. For Copilot, the installer target alone does not establish support across Copilot clients or versions.

Codex runtime evidence comes from the four isolated `codex exec` scenarios recorded on macOS arm64 in the [2026-11-03 RC report](delivery.md) and [scenario notes](skill-scenarios.md). Codex also installed all four Skills from the public repository during v0.2.0 release verification. The runtime evidence covers the tested CLI workflows and Gradle builds in that environment.

To contribute a compatibility result, include the agent name, client and version, operating system, project or global installation command, CLI version, Recipe, prompt and success or failure at each stage. Include sanitized logs or the exact error and distinguish file placement from discovery, CLI execution and Gradle build results.

## 开发版能力协议与验收

Phase 2 的本地候选版为 `0.3.0rc1`。四个 Skill 新增要求 `distribution.release-identity.v1`，同时保留协议和 Recipe 约束。支持同一能力与 Recipe 契约的后续 CLI 可继续使用。Phase 1 Skill 的旧契约也可使用候选 CLI。安装来源与平台锁见 [候选版说明](release-candidate.md)。以下保留 Phase 1 历史证据。


Skills 安装器复制指令和伴随文件。Python wheel 提供执行入口、Resolver、Installer 和 Recipe。两条分发渠道可以独立更新。验收中，旧 wheel 和候选 wheel 均报告 `0.2.0`，只有候选实现能力查询。开发用可编辑环境还曾出现运行代码为 `0.2.0`、包元数据为 `0.1.0` 的情况。

## 能力协议

`android-stack capabilities --json` 返回协议号、运行代码版本 `version`、已安装包版本 `distribution_version`、解释器与实际加载模块位置、功能标识列表和已打包的 Recipe 版本。已有 `android-stack version` 和 Recipe 命令保持原接口。

每个 Skill 随附 `cli-requirements.json` 和 `cli-setup.md`。先确定可信 CLI 的绝对路径并运行探测。协议号必须相同，所列能力必须全部存在，所列 Recipe 版本必须精确匹配。CLI 运行版本必须与分发元数据一致。额外能力可接受。协议、能力或 Recipe 版本不符时停止，后续命令沿用通过探测的同一个可执行文件。能力标识有独立版本，Recipe 版本从 wheel 内的清单读取。功能或 Recipe 改变时需同步更新契约与测试。

## 准备方案

| 方案 | 实测范围 | Phase 1 选择 |
| --- | --- | --- |
| A，Agent 引导 | 发现旧 CLI，检查 Python 与已审查制品，申请安装批准。夹具在模拟批准后离线安装并复用环境。 | 四个 Skill 的默认流程 |
| B，Skill 内入口 | `android-network/scripts/cli_gate.py` 使用 Python 标准库探测并转发到同一 CLI。项目级和用户级副本均实测。 | 保留为网络 Skill POC |

方案 A 优先复用兼容隔离环境。确需准备时，先让用户审查来源、固定制品及依赖哈希、目标 venv 路径和影响范围。获批后在 Android 工程外新建 venv，以隔离 pip 和已审查 wheelhouse 离线安装。准备失败时停止。回滚可选回原 CLI，无需就地升级或删除旧环境。方案 B 的入口不安装软件或管理缓存，依赖 Python 3.11+ 与调用方提供的可信 CLI 路径。跨 Agent 和 Windows 启动、缓存升级策略仍待验证。具体命令见 [准备指南](../skills/android-network/cli-setup.md)。

## 可复现实验

1. 从干净源码暂存目录构建候选 wheel。打包前排除旧 `build/` 和 `*.egg-info`。初次复用本地 `build/` 时发现两个过时模板，最终 wheel 在全新目录重建并检查内容。
2. 在新的临时目录准备 `candidate/` 和 `legacy/`，分别放当前与早期、同名的 `android_stack_skills-0.2.0-py3-none-any.whl`。将审查过的目标平台依赖 wheel 放入 `wheelhouse/`。
3. 把四个完整 Skill 目录放进独立的待审查制品目录。从临时工程 `agent-project/` 运行 `npx --offline --yes skills@1.7.6 add /path/to/reviewed-skill-bundle --agent codex --skill '*' --copy --yes --json`。再设置临时 HOME 为 `home-user/`，用同一命令加 `--global`。验证复制到 `.agents/skills/` 和 `$HOME/.agents/skills/` 后移开制品源目录。运行离线 npx 需要预热 npm 缓存。Codex 路径与工具参数见 [Codex Skills](https://learn.chatgpt.com/docs/build-skills) 和 [Vercel Skills](https://github.com/vercel-labs/skills)。
4. 用 Python 3.11+ 执行 `python -I scripts/verify_cli_readiness.py --fixtures /path/to/temporary-root --unsupported-python /path/to/python3.9`。脚本以临时 HOME、精简 PATH 和绝对可执行路径启动子进程。旧 Python、CLI 缺失和能力不足都需返回阻止状态。它模拟批准与拒绝，检查真实 pip 失败的零工程写入、批准后的离线安装、两种安装范围的 CLI 转发，以及重复准备的文件哈希稳定性。实际 CLI 从隔离 venv 的 site-packages 加载。见 [干净环境结果与哈希](validation/readiness-phase1/clean-matrix.json)。

## 验收边界

干净环境测试使用 macOS arm64、Python 3.11 和宿主 Python 3.9。它隔离了子进程环境，宿主仍有源码、Python 和 Node 工具。真实 Codex 会话使用宿主认证与登录 shell，并允许受控访问 Gradle 缓存及本地文件锁套接字。测试使用已安装的项目级 Skill。用户级仅验证安装和入口转发。其他 Agent、Windows、远程 Skill 来源、交互式批准后恢复原 Agent 会话均未验证。

能力报告用于功能协商。它无法证明可执行文件来源或签名，探测本身会运行目标代码，因此仅探测可信来源。离线夹具验证了本地依赖包，Android 构建仍依赖 SDK、JDK 和 Gradle/Maven 可用性。本轮没有公共候选制品。下一阶段需要为公开 wheel 与 Skill bundle 分配唯一发行标识、提供可信固定下载来源与按平台锁定的哈希，再验收公开安装链路和各 Agent 的批准交互。

## 实测结果

- `.venv/bin/python -m pytest -q`，86 项通过。新增覆盖四份 Skill 契约、同版本缺能力、Recipe 错配、包元数据错配、协议错配，以及 Skill 伴随文件的打包镜像检查。`git diff --check` 通过。
- 项目级与用户级 `npx` 安装均复制了四个 Skill 及其伴随文件。干净环境矩阵用最终 wheel 通过。批准与拒绝是脚本分支模拟，安装与失败用真实 pip 验证。
- Codex A 显式调用 `$android-network`。读取项目级 Skill 后识别 `0.2.0` 旧 CLI 缺失 `capabilities`，验证 Python 3.11.14、最终 wheel 和十个依赖哈希，并在请求批准后停止。拟用 venv 不存在，Android 夹具未改变。
- Codex B 收到“帮我给已有 Android 工程集成 Retrofit + OkHttp，保留项目现有工具链和源码目录结构。”会话自行读取 `android-network`，使用最终 wheel 的已准备 CLI，完成 `inspect`、`plan`、`install`、重复安装、`verify`。首次 Gradle 验证遭遇本地套接字沙箱限制，授权重试后实际命令 `./gradlew :app:assembleDebug :app:testDebugUnitTest --console=plain --stacktrace` 成功。JUnit 14 项通过，零失败、错误或跳过。保留 Kotlin 2.0.21、AGP 8.13.1、Gradle 8.14.3 和原有 Java 源码根。重复安装返回 `already-installed`，另行核对四份受管理文件哈希全部一致。见 [Gradle 日志](validation/readiness-phase1/gradle.txt)。
- 两个 Codex 会话使用较早的 `cli-setup.md` 副本。握手、Skill 主文件和能力契约一致。最终指南补充逐个校验依赖哈希及 pip `--isolated`。A 实际检查了全部哈希，B 使用已准备环境，最终离线安装命令由干净环境夹具执行。

## 修改范围

CLI 新增 `capabilities.py` 和一个子命令。四个 `SKILL.md`、能力契约、准备指南及网络启动器同步到 wheel 内的 `data/skills/`。新增 `scripts/verify_cli_readiness.py` 和 CLI 契约测试，扩展 wheel 资源镜像测试，更新中英文 README。Phase 1 使用临时 Android 工程与本地制品。
