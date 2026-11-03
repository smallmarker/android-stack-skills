# Agent compatibility

The same four Skills follow the open [Agent Skills specification](https://agentskills.io/specification). The host needs to discover and read `SKILL.md`, access the local Android project, execute `android-stack` and use command results to continue or report failures. The CLI and its bundled Recipes work independently of the agent. Android builds also require the environment listed in the [installation guide](../README_EN.md#2-install-android-stack-cli).

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
