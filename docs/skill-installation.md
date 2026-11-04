# Agent Skill Prompt 安装验收

2026-11-04 验证公开开发分支 `900b57f8ff78ba1048c2ded4475e8c5bfc8f4210`。测试使用 macOS、Codex CLI 0.166.0-alpha.6 和 npx Skills 1.7.6。公开 Skill 目录与本地工作树中的对应文件一致。验收限定为安装与发现，不包括 Recipe 运行。文件清单、SHA-256、会话场景和复制结果见 [验收证据](validation/skill-installation/results.json)。

## 参考行为

[SkillsMP 的 Prompt](https://skillsmp.com/skill-install/prompt.md) 实际返回 HTTP 200，检索内容的 SHA-256 为 `94e2ef371c8fec9264cc154a7863774c2a266c8be8b29037ddefc852e614295f`。网页检索工具无法访问该 URL，改用直接 HTTPS 读取成功，Codex 安装会话也实际读取了该指令。

- URL 可以指向 GitHub 仓库、Skill 目录或 `SKILL.md`。保留指定版本，从实际 `SKILL.md` 所在目录判定边界，核对 README 和必需的伴随资源。目录或文件 URL 已表明选择，仓库 URL 则先列出技能、用途、目录和前置条件，等待选择。
- 按当前 Agent 支持的位置安装。默认采用项目级，用户明确要求时才使用用户级，无法确定目标时应询问。安装选定的完整目录，保留相对路径。安装时可以临时取得源码，最终目标只留下选定的 Skill。发现冲突应先询问，再决定是否替换。
- 验证目标文件和相对引用，报告来源、版本、目标位置及限制。SkillsMP 提供第三方安装指令，不负责写入文件，也未规定必须使用 npx 或专用 CLI。Agent 可复用其已有工具。本次仓库多选会话实际调用了 Codex 的 skill-installer；部分单目录会话使用临时 Git 检出和完整目录复制。
- 开放 Agent Skills 规范定义目录、`SKILL.md`、YAML frontmatter、可选资源和相对引用。安装范围、覆盖政策及目标 Agent 的查找目录由宿主和安装流程决定。 [Agent Skills 规范](https://agentskills.io/specification)
- Anthropic 的 `frontend-design` 根目录包含 `SKILL.md` 与 frontmatter 引用的 `LICENSE.txt`。NextLevelBuilder 的 `ui-ux-pro-max` 位于 `.claude/skills/` 下，含 `data/`、`references/`、`scripts/`，且使用了宿主特定的脚本路径。两例都说明应复制完整选中目录。后者的 Python 运行依赖和宿主路径需要在执行时判断。 [frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) · [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/main/.claude/skills/ui-ux-pro-max)

## Codex 实测

| 场景 | 结果 |
| --- | --- |
| 指定 android-network URL | PASS。项目级只安装该 Skill 的四个文件，含 `scripts/cli_gate.py`。 |
| 另外三个指定 URL | PASS。各自独立安装三个文件。图片 Skill 初次遇到临时目录的沙箱写入限制，明确限定目标目录后重试通过。 |
| 仓库 URL，等待选择 | PASS。列出四个 Skill、用途和范围选项，未安装。 |
| 用户取消 | PASS。同一会话收到取消后无写入，随后重新开启选择流程。 |
| 用户选择两项 | PASS。同一会话只安装 `android-project` 与 `android-image`。 |
| 选择全部 | PASS。项目级四个目录共 13 个文件。 |
| 指定用户级 | PASS。只向临时 HOME 的 `.agents/skills/` 写入 `android-logging`。 |
| 自定义同名 Skill | PASS。识别修改并询问，保留原字节。 |
| 新会话发现 | 项目级及用户级 PASS。项目新会话读取网络 Skill；隔离 HOME 与 CODEX_HOME 的新会话在网络重试后读取用户级日志 Skill。 |
| 安装阶段的 Python CLI | PASS。审查安装会话的命令，未准备或安装 Android Stack CLI。 |

四个 Skill 的 frontmatter 已独立解析并核对名称、说明和伴随链接。所有成功安装的文件集合与公开源码 SHA-256 一致。当前 `skills/<name>/` 结构已能满足两种安装方式。

## npx 对照

- 运行用户提供的 `npx skills add smallmarker/android-stack-skills`。在检测到 Codex 的环境中，Skills 1.7.6 进入非交互流程，项目级安装全部四个 Skill。清空 Agent 环境标记后，同一命令显示 Skill 与 Agent 的交互选择；在 Agent 选择界面取消后未写入。
- 显式 `--agent codex --skill android-image android-project` 只安装两个 Skill，`--global --agent codex --skill android-logging` 写入临时 HOME。选中目录、frontmatter、伴随文件及哈希与 Prompt 安装等价。项目级 npx 还生成了 `skills-lock.json`。
- 对未修改的目录重复安装，npx 返回 `installed`，文件字节一致。对加入自定义注释的临时同名 Skill 重装，npx 覆盖了改动。默认推荐选择式 Prompt，直接使用 npx 时先检查同名目录并显式指定 Skill 和 Agent。 [npx Skills](https://github.com/vercel-labs/skills)

上述 Prompt 安装在临时环境中执行，哈希对应当时的公开提交。

## 开发版 CLI 准备复验

更新指南后，在工程外的新 Python 3.11 venv 从同一个公开 GitHub 提交安装 CLI。网络 Skill 的 gate 返回 `ready`，运行版本与安装元数据均为 `0.3.0rc1`。单独启动只读 Codex 会话，模拟 PATH 中没有 CLI 且用户拒绝安装。会话识别固定提交并停止，未执行 venv、pip 或 Recipe 命令，测试工程文件 SHA-256 保持一致。
