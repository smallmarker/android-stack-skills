# Android Stack Skills 0.3.0rc1

| 分发状态 | 当前记录 |
| --- | --- |
| 公开稳定版 | 仓库未配置远程。PyPI 项目查询未找到记录，尚无已确认的公开稳定制品 |
| 本地候选版 | `0.3.0rc1`，以构建时生成的 `release-manifest.json` 为准 |
| 公开候选版 | 等待确认 canonical GitHub 仓库和发布授权 |

Release 附件拟由经确认的 canonical GitHub 仓库的固定 `v0.3.0rc1` Release 提供。下载时固定 Tag 和文件名，校验可信渠道提供的 SHA-256。用户批准前无需接触远程仓库。公开后保持 Tag、提交及附件不变。任何内容变更使用 `0.3.0rc2` 等新版本，正式版使用 `0.3.0`。Recipe 版本独立管理。

## 从固定提交构建

1. 使用 CPython 3.11.14 创建独立构建环境。用 `release/build-requirements.txt` 以 `pip install --no-index --only-binary=:all: --require-hashes --find-links <build-wheelhouse> -r release/build-requirements.txt` 安装锁定构建工具。构建工具 wheel 来自官方 PyPI。
2. 准备四个平台的 wheelhouse。每个依赖以 `release/locks/` 中记录的版本与 SHA-256 为准。以下示例是 Linux，其他目标分别用 `macosx_11_0_arm64`、`macosx_10_15_x86_64` 和 `win_amd64` 及对应锁文件。跨目标下载使用 `--no-deps`，因为锁显式枚举了完整运行依赖图。
   ```sh
   python -I -m pip --isolated download --index-url https://pypi.org/simple --require-hashes --no-deps --only-binary=:all: --python-version 3.11 --implementation cp --abi cp311 --platform manylinux_2_17_x86_64 -r release/locks/linux-x86_64.txt -d /path/to/wheelhouses/linux-x86_64
   ```
3. 执行 `/path/to/build-env/bin/python release/build_rc.py --commit <full-commit> --wheelhouses /path/to/wheelhouses --output /path/to/new/bundle`。脚本从 Git archive 在新目录构建 wheel，锁定构建工具并用提交时间作为 `SOURCE_DATE_EPOCH`。输出 wheel、Skill zip、平台锁与 wheelhouse、安装器、包含完整提交和制品哈希的清单、`SHA256SUMS` 与完整 bundle zip。

## 安装已批准的候选版

先校验从可信渠道获得的 bundle 或清单 SHA-256，再解包。按已验证清单核对安装器和 Skill zip。将 Skill zip 解压到独立目录，在目标工程检查同名自定义 Skill，然后执行 `npx skills@1.7.6 add /path/to/extracted-skills --agent codex --skill '*' --copy`。仅在有意安装到用户范围时添加 `--global`。

Agent 会检查可信 CLI。安装需批准固定制品、校验值和目标 venv。安装器在目标工程之外准备 CPython 环境，仅从该平台 wheelhouse 读取哈希锁定的二进制包。使用方式见 [Skill 准备指南](../skills/android-network/cli-setup.md)。已成功准备的环境可复用。失败的部分环境保留供排查，请选新路径重试。旧环境可用于回滚。

| 平台锁 | 目标 |
| --- | --- |
| macOS arm64 | macOS 11+，CPython 3.11 |
| macOS x86_64 | macOS 10.15+，CPython 3.11 |
| Linux x86_64 | glibc 2.28+，CPython 3.11 |
| Windows x86_64 | CPython 3.11 x64 |

CLI 包元数据仍声明 Python 3.11+。本轮可复现安装渠道只接受 CPython 3.11，实际运行验收在 macOS arm64 3.11.14。其他目标的二进制选择与哈希可跨平台验证，实际运行需对应主机。三项原生依赖是 PyYAML、MarkupSafe 和 rpds-py，其余七项为通用 wheel。

## 公开验收门槛

确认仓库归属、现有发行和 Tag 后，需要单独授权推送固定提交、建立并推送 Tag、发布 GitHub 预发行版及上传校验过的附件。公开后再用隔离客户端验证 HTTPS 下载、附件哈希和实际安装。PyPI 上传是独立操作。当前安装链路使用本地候选包与隔离夹具。

## 本地验收结果

候选源码为 `cba5dfe6b402381e0af04c12e6d7a6556fae1804`。验证构建工具 wheel 的锁定哈希并重新安装后，再从同一提交构建，wheel 和完整 bundle 均逐字节一致。制品位于本地 `dist/0.3.0rc1/`。完整哈希见 [制品记录](validation/readiness-phase2/artifacts.json)。

- 隔离矩阵 16 项 PASS。其中协议错配、拒绝安装和不支持架构通过夹具触发。Python 3.9、损坏依赖 wheel、HTTP 截断、离线准备及真实 Gradle 使用实际进程验证。HTTP 为本机夹具。见 [隔离矩阵](validation/readiness-phase2/isolated-matrix.json)。
- 四个目标分别用 pip 的跨目标下载模式重新校验了 10 个 wheel 的类型、版本和哈希。原生安装在 macOS arm64 CPython 3.11.14 通过。macOS Intel、Linux x86_64 和 Windows x86_64 原生运行仍待验收。
- 项目级和用户级 Skill 均从已校验 zip 通过 `npx skills@1.7.6` 复制。用户级验证覆盖安装和转发。独立 Codex 会话验证项目级发现。见 [Skills 安装记录](validation/readiness-phase2/skill-install.json)。
- 真实 Codex A 读取 Skill，报告缺少 CLI，给出本地固定候选与审批方案。A 没有收到授权，Android 工程和 venv 均无写入。B 使用预先获准用于夹具的 RC venv，从 site-packages 加载，读 Skill 后完成计划、安装和幂等复验。首轮 Gradle 受本地套接字沙箱限制，获准重试后 14 项通过。原有文件中仅模块 Gradle 文件因添加依赖而改变，四份管理文件的哈希全部一致。见 [Codex 命令证据](validation/readiness-phase2/codex.json)和 [B 的 Gradle 日志](validation/readiness-phase2/codex-b-gradle.txt)。
- Python 全量 86 项通过，覆盖 Recipe 冲突保护、幂等和恢复。Kotlin 2.0.21/2.2.20、Java/Kotlin/混合布局、Lightweight/Standard Compose/XML 共 9 个真实 Gradle 回归均通过。已安装 wheel 在源码目录外通过六个 Recipe、四个 Skill 及四种工程模板资源检查。见 [Gradle 矩阵](validation/readiness-phase2/gradle-matrix.json)。
- 公开 GitHub 附件链路为 BLOCKED，缺少确认的远程仓库和发布授权。用户级 Codex 自动发现、交互批准后继续同一会话、其他 Agent 和其他 Python 版本未完成验收。

独立矩阵可用 `python -I scripts/verify_release_candidate.py --help` 查看参数。传入可信 bundle 和清单的 SHA-256、经 Phase 1 记录验证的旧 wheel、已实际安装的项目级和用户级网络 Skill 路径、独立 Android 基线夹具和真实 Python 3.9。脚本在 macOS arm64 上执行 15 项，真实 Gradle 项由独立 Codex B 提供证据。脚本使用本地 HTTP 服务，需要允许绑定回环套接字。
