# V1 Release Candidate 验收报告

> 本文记录 0.1.1 RC 的历史验收。首个 Early Preview 候选版本为 0.2.0，其 Compose、XML / ViewBinding、Coil 和 Glide 支持范围见 [兼容性说明](compatibility.md)。

验收日期：**2026-11-03**。候选构建：**android-stack-skills 0.1.1**。结论：**本次要求的命令行自动化验收通过，未发现遗留发布阻塞项**。Android Studio GUI、模拟器/真机与 UI 体验按开发者要求留待人工验证，**不作为本次自动验收阻塞条件**。未推送远程、未创建 Release 或发布标签。

本次只做可靠性审查、缺陷修复与验收，没有加入 V2 功能。所有结果来自本次新运行，未用此前遗留日志替代测试。此前 V1 开发报告已保存在 [历史报告](delivery-v1-2026-11-02.md)。

## 自动化验证已通过

| 验收项 | 本次真实结果 | 证据 |
|---|---|---|
| Python 回归 | **38 passed** | 最终输出（本地留档） |
| 独立 venv 安装 wheel | 非 editable 安装，隔离 site-packages，CLI version/help/recipes list 正常 | 安装日志（本地留档）、环境（本地留档）、包清单（本地留档） |
| wheel 资源完整性 | 5 个 Recipe、模板、Schema、官方 Wrapper/许可证、隐藏 .gitignore、**4 个 Skills** 齐全 | wheel 清单及 SHA-256（本地留档） |
| 非源码目录生成 | 从 `/tmp` 用独立 venv 生成 Lightweight 与 Standard；未依赖开发仓库导入 | 打包复现结果（本地留档） |
| Lightweight | 实际 assembleDebug/testDebugUnitTest 成功；**18 tests，0 failures，0 skipped** | 构建日志（本地留档） |
| Standard / Hilt | 实际 assembleDebug/testDebugUnitTest 成功；**18 tests，0 failures，0 skipped** | 构建日志（本地留档） |
| 独立 Android 工程增量集成 | 不使用生成器的 Notes 工程；基线→Network→Image→Logging 均实际构建成功 | 增量结果（本地留档） |
| 源码保护与幂等 | 原有文件哈希保留；每项再次安装无变化 | CLI 安全检查（本地留档）、增量脚本断言 |
| 依赖/文件冲突 | 不兼容 Retrofit 与已有生成文件均返回 exit 2，工程哈希不变 | CLI 安全检查（本地留档） |
| 实际依赖兼容 | Retrofit/Coil 共同解析到 OkHttp **4.12.0**，没有冲突升级 | Gradle dependencyInsight（本地留档） |
| Skills 格式与镜像 | 四个 quick_validate 均通过；源码与 wheel 资源镜像一致的 pytest 通过 | 38 项 Python 回归中的 distribution 测试 |
| 独立 Codex Skills 行为 | 四个新会话均自然语言选择正确 Skill，实际读取文件、调用 CLI 并构建成功 | 核验结果与命令（本地留档） |
| 日志 Release 回归 | assembleRelease / testReleaseUnitTest 成功；**4 tests，0 failures，0 skipped** | Release 日志（本地留档） |

### 独立 Codex 会话的实际验证方式

使用本机 `codex-cli 0.166.0-alpha.5.1` 的 `codex exec`。每次均为新会话，**没有 resume/fork，也没有携带原开发聊天上下文**；使用 `--ephemeral --ignore-user-config --skip-git-repo-check`。CLI 默认账户认证与宿主内置规则仍存在，因此这是无开发历史上下文的真实宿主测试，不宣称完全空白的操作系统环境。

在四个独立 `/tmp/android-stack-rc-audit-20261103/agent-*` 工作区，将 **wheel 内** `data/skills/` 的四个目录复制到 `.agents/skills/`。PATH 仅指向新 venv 的 CLI；会话不访问原开发仓库。自然语言提示只说明用户需求（Compose 工程、Retrofit、Coil 或 Timber），**没有显式指定 Skill 文件名**。AGENTS.md 仅限制测试范围、GUI 与发布操作，并要求报告真实结果。

| 自然语言需求 | 实际读取 Skill | 构建与单元测试 |
|---|---|---|
| 创建轻量 Compose + MVVM 工程 | android-project | 新工程构建通过，18 tests |
| 为独立 Notes 工程集成 Retrofit + OkHttp | android-network | 构建通过，15 tests；重复安装无变化 |
| 为 Notes Compose 工程集成 Coil / AppImage | android-image | 构建通过，原有 1 test 通过；重复安装无变化 |
| 为 Notes 工程集成 Timber 统一日志 | android-logging | Debug/Release 均通过，各 4 tests；重复安装无变化 |

Image 单独集成场景只证明封装编译、原业务测试及幂等，**不将 1 个原业务测试说成图片 UI 测试**。图片运行时状态属于下方开发者人工清单。

父会话通过 `scripts/summarize_rc_sessions.py` 校验 JSONL 中成功读取相应 SKILL.md、CLI 实际命令、会话正常完成，并独立核对磁盘上的验证 JSON、完整构建日志、JUnit XML 和 Notes 业务文件字节内容。完整会话事件保存在：

- Project（本地留档）
- Network（本地留档）
- Image（本地留档）
- Logging（本地留档）

环境变量中的 SDK 路径与网络代理只用于测试进程。Network 会话在其临时工作区写入了被忽略的 local.properties，未写入本仓库或生成器模板。所有会话均仅使用命令行，没有启动或控制 GUI、IDE、模拟器/真机。

### 独立 Android 工程集成

[`tests/fixtures/rc-notes`](../tests/fixtures/rc-notes/README.md) 是一个独立编写的非生产 Compose Notes 工程，含自己的 Application、Activity、Repository 和业务单元测试；**没有调用 create，也没有从生成工程删除 Recipe 文件来模拟既有工程**。脚本仅给它配备哈希验证过的 Gradle Wrapper，再复制到 `/tmp` 执行。

| 阶段 | 执行测试数 | 结果 |
|---|---:|---|
| 原始 Notes 基线 | 1 | 构建/测试成功 |
| 安装 retrofit-standard | 15 | 构建/测试成功 |
| 再安装 coil-standard | 15 | 构建/测试成功 |
| 再安装 timber-standard | 18 | 构建/测试成功 |

全部 0 failures、0 errors、0 skipped。每次安装后重复安装并对比非构建文件快照，再执行真实 Gradle。自动安装只修改模块依赖块和新文件，原有 Application/Activity/Repository/测试均保持原样。

独立 Skills 会话另外完成必要初始化：Image 和 Logging 仅在现有 Application 中添加 onCreate 调用，Network 保持原 Application。页面、Repository 和已有测试文件仍逐字节相同。初始化 Diff（本地留档） 可审查。

### 代码质量审查与修复

| 范围 | 审查结论与处理 | 回归 |
|---|---|---|
| 网络错误映射 | 接续工作区已有修复：识别全请求超时 InterruptedIOException、截断 JSON 的 EOFException；传输异常映射前 ensureActive，保留取消语义 | 14 个真实 Kotlin 网络测试方法，包含 MockWebServer |
| 凭据安全 | Token 只注入同来源；本次进一步把配置的公共 Headers 同样限制到 scheme/host/port 相同的来源，防止绝对 URL 外发 API Key | `commonHeadersAndTokensAreOriginScoped` 和跨来源 Token 测试 |
| URL 配置 | 使用 OkHttp HttpUrl 校验 HTTPS、URL 内账号密码、query/fragment 与路径结尾，不靠 startsWith 判断 | 配置拒绝测试 |
| 日志 | 接续已有修复：Release event 在输入校验前直接 no-op；异常只输出类型；静态消息/结构化数值白名单，不宣称能清洗任意字符串 | debug/release JVM 测试、真实 Release 构建 |
| 图片 | 复用 Coil 共享 Loader、原生缓存/下载/解码；AppImage 仅提供 shape/scale/占位与状态插槽；未添加另一套下载器 | 独立 Compose 工程、两种预设实际编译 |
| DI | Standard 的 NetworkModule、AppModule、LoggerModule 与 Hilt 编译通过；已有复杂 DI 绑定仍须审查 qualifiers，不声称能自动合并任意图 | Standard 18 项测试与 Hilt 构建 |
| Gradle | 固定稳定基线不变；明确依赖块增量追加；匹配版本复用，不匹配则停止 | 独立增量/冲突测试、实际 dependencyInsight |
| 分发 | 原 wheel 未包含 Skills；本次加入四个随包资源和镜像一致性回归，避免依赖原源码目录 | 独立 venv、仓库外生成与独立会话实际读取 |

没有增加通用插件系统、自动升级框架或复杂架构抽象。Network 与 Logging Recipe 修订为 **0.1.1**；Coil、Lightweight、Standard 保持 **0.1.0**。已有 0.1.0 安装仍按现有规则要求人工审查升级，不自动覆盖源码。

## 自动化验证失败

**最终候选构建没有未解决的自动化失败。** 以下真实失败/中断保留，不把首次尝试说成通过：

1. 旧 0.1.0 wheel 资源检查：SKILL.md 数量为 0；修复后的 0.1.1 数量为 4。最终资源清单（本地留档）。此项是发行资源审查，未把旧包当作本次候选包。
2. 初次独立 Project 会话因无法写入用户 Gradle 缓存锁失败；另一个初始 Network 会话随测试权限调整中断。其事件保存在 `codex-project.jsonl`、`codex-network.jsonl`，**不计通过**。
3. 重跑时即使显式开放缓存目录，Gradle 本地 socket 仍被 workspace sandbox 限制（`java.net.SocketException: Operation not permitted`）。会话按授权经 `--approve-for-me` 请求构建权限，随后真实 verify 成功。完整重跑 JSONL 同时包含首次失败和后续成功。

没有使用 `--dangerously-bypass-approvals-and-sandbox`，没有删除失败测试。历史工作区中更早的未提交日志已完整移至 `/tmp/android-stack-rc-audit-20261103/preexisting-evidence` 保留，未作为本次验收证据或纳入新提交。

## 因环境限制未验证

- **本次要求的四个独立 Codex 会话、wheel 安装/资源检查、独立 Android 集成和命令行构建没有剩余未验证项。** 初始 sandbox 限制已经通过审批重试解决。
- 没有验证 Claude Code 等其他 Agent 宿主、Windows/Linux 执行环境及不同 AGP/Kotlin 组合。这些不属于本次已认证范围，不能从 macOS/Codex 结果推断通过。
- 自动化未做真实第三方 HTTPS 服务联调；网络测试使用 MockWebServer 和受控拦截器，未使用真实账号或密钥。

## 留待开发者手动验证

以下按本次明确排除范围保留为简短清单，**不作为 Codex 自动验收或 RC 报告的阻塞条件**：

- 用 Android Studio 打开 Lightweight / Standard，检查 Gradle Sync、索引、代码补全及开发体验。
- 在模拟器或真机安装运行，检查首页、生命周期和基本交互。
- 按应用后端契约配置受控 HTTPS 服务，检查真实网络和图片的加载、失败、占位及可访问性表现。

本次没有尝试完成这些 GUI 或设备操作，也没有使用此前已有截图将它们标记为通过。

## 可复现命令

```sh
# 源码回归与构建 wheel
.venv/bin/pytest -q
.venv/bin/python -m build --wheel

# 全新环境；从 /tmp 等非源码目录运行
python3.11 -m venv /tmp/rc-fresh-venv
/tmp/rc-fresh-venv/bin/pip install /absolute/path/android-stack-skills/dist/android_stack_skills-0.1.1-py3-none-any.whl
cd /tmp
/tmp/rc-fresh-venv/bin/android-stack --help
/tmp/rc-fresh-venv/bin/android-stack version
/tmp/rc-fresh-venv/bin/android-stack recipes list
/tmp/rc-fresh-venv/bin/python /absolute/path/android-stack-skills/scripts/verify_wheel_distribution.py --output /tmp/rc-fresh-packaging

# 独立 Notes 工程；输出目录必须不存在，设置本机 ANDROID_HOME/JDK/网络代理
/tmp/rc-fresh-venv/bin/python /absolute/path/android-stack-skills/scripts/verify_rc_incremental.py --output /tmp/rc-fresh-notes

# 验证预设
/tmp/rc-fresh-venv/bin/android-stack verify --project /tmp/rc-fresh-packaging/lightweight
/tmp/rc-fresh-venv/bin/android-stack verify --project /tmp/rc-fresh-packaging/standard
```

实际 Gradle 验证命令均记录在日志第一行，核心任务为 `:app:assembleDebug :app:testDebugUnitTest --console=plain --stacktrace`。依赖解析命令为 `:app:dependencyInsight --configuration debugRuntimeClasspath --dependency okhttp`。

Skills 新会话可复现步骤与原始自然语言提示见 [Skills RC 步骤](skill-scenarios.md)。当前执行环境若缺少 Codex CLI/登录/构建权限，应报告该项未验证，不能用人工预期替代本报告的真实会话证据。

## 发布判断

**本次自动验收未发现发布阻塞项，可供开发者进行后续 RC 发布决策。** 自动验收不代表所有平台、任意 Gradle/DI 工程或 GUI 体验已经通过。发行资源使用 SHA-256 清单（本地留档） 标识；本次只生成本地 wheel 和 Git 提交，未推送或发布。
