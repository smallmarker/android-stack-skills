# Skills RC 独立会话复现

2026-11-03：四个自然语言测试已在独立 `codex exec` 会话中真实通过。见 [RC 报告](delivery.md)、命令与测试核验（本地留档）。这不认证其他 Agent 宿主。

## 准备

1. 在新 venv 安装候选 wheel，不做 editable install。将 venv/bin 放在 PATH 首位；配置实际 JDK17、ANDROID_HOME 与必要的网络代理。先确认 `android-stack version` 为0.1.1。
2. 在 `/tmp` 创建4个互相隔离的工作区：project、network、image、logging。不要复制本聊天或原开发会话记录。
3. 从 wheel 资源复制四个 Skill 到每个工作区 `.agents/skills/`。可使用：

```python
from importlib.resources import files
from pathlib import Path
import shutil
source = files("android_stack_skills").joinpath("data", "skills")
workspace = Path("/tmp/my-rc-project")  # 使用新的空目录
workspace.mkdir()
shutil.copytree(str(source), workspace / ".agents/skills")
```

4. Project 工作区保持空工程；Network/Image/Logging 各复制 `tests/fixtures/rc-notes/` 的原始内容。仅配备可信 Gradle Wrapper，不复制生成器的 Application/业务/Recipe 源码：可从上一步仓库外生成的 `/tmp/rc-fresh-packaging/lightweight` 复制 `gradlew` 和 `gradle/wrapper/`。保留目录原有 `gradle/libs.versions.toml`。
5. AGENTS.md 可仅写测试边界：只修改当前隔离工程；不访问开发仓库；不使用GUI/IDE/模拟器/设备；不发布；报告所选Skill、真实命令和测试结果。不要在这里提示应选择哪个Skill。

## 每次启动新的会话

使用当前可用的已登录 Codex CLI，无需创建侧边栏聊天，不使用 resume/fork。示例：

```sh
codex exec --ephemeral --ignore-user-config --skip-git-repo-check \
  --approve-for-me --add-dir "$HOME/.gradle" --json \
  -C /tmp/my-rc-project \
  '创建一个叫 FreshCompose 的 Android Compose + MVVM 轻量项目，包名 dev.rc.freshcompose，使用这里安装的能力和已安装CLI，实际构建和测试。禁止GUI/设备/IDE，不访问开发仓库，不推送。报告使用的Skill、命令和真实结果。' \
  </dev/null > /tmp/my-rc-project.jsonl 2>/tmp/my-rc-project.stderr.txt
```

Gradle 在受限沙箱内可能无法创建缓存锁或本地socket；仅开放缓存目录不一定足够。通过 `--approve-for-me` 对构建所需权限作自动审核，不使用 bypass 参数，不复制整个用户缓存。如果当前宿主不支持审批或无法运行，报告环境阻塞/未验证，保留日志，让开发者在允许构建的终端复现。

其余三次对各自原始Notes工作区使用自然语言，不显式写Skill名：

| 需求提示 | 本次实际观察 |
|---|---|
| “集成Retrofit + OkHttp，保留Notes业务与测试，实际构建并重复安装确认幂等” | 读取android-network；CLI计划/安装/验证；15 tests；哈希不变 |
| “为Compose工程集成Coil图片加载和AppImage，处理初始化，实际构建、测试并重复安装” | 读取android-image；Application添加初始化；原业务文件保留；1 test；编译及幂等通过 |
| “集成Timber统一日志，处理初始化，确保Release安全，实际构建、测试并重复安装” | 读取android-logging；Debug/Release各4 tests；原业务保留；幂等通过 |

## 核对通过条件

- JSONL 中存在成功读取对应 `.agents/skills/android-*/SKILL.md` 的命令；仅模型口头说“使用了Skill”不够。
- 确实调用安装环境的 android-stack，不能回到开发仓库动态生成另一套实现。
- `.android-stack/verification.json` 为success，完整Gradle日志包含BUILD SUCCESSFUL，JUnit XML实际tests>0且failures/errors/skipped为0。
- 原NotesActivity、NotesRepository和原业务测试哈希一致；Application只允许集成所需初始化。记录Diff。
- 重复安装返回already-installed，非构建文件与安装记录快照无变化。
- 失败不能宣称通过；诊断并重试的失败过程也应保留。

本次父会话用 `scripts/summarize_rc_sessions.py --workspace /tmp/android-stack-rc-audit-20261103 --evidence docs/validation/rc-audit-20261103` 对上述证据作二次核验。

额外的状态查询/版本冲突场景由CLI子进程及安全测试覆盖，不声称本次另开模型会话测试过这些提示的自动路由。无需为它们操作GUI。

官方说明：[Codex非交互运行](https://learn.chatgpt.com/docs/non-interactive-mode)、[Skills发现目录](https://learn.chatgpt.com/docs/build-skills)。
