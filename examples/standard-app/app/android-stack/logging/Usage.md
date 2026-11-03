# Logging

Call `AppLogger.initialize(BuildConfig.DEBUG)` once from Application.onCreate.
Call `AppLogger.d("Home", "Page created")` or inject `Logger` in an existing Hilt project.

Release calls through this facade are silent. Existing Timber trees are not removed.
Use only constant developer-authored messages and non-sensitive tags with d/i/w/e.
Use `event("Home", "page.created", listOf(LogField.Count(3)))` for dynamic numeric data.
Passwords, tokens, cookies and personal data must never enter message/tag strings.
Unknown sensitive fields must be represented by `LogField.Redacted`.
Exception class names may be emitted in debug; exception messages and stacks are excluded.
This is an allowlist policy, not a claim to automatically sanitize arbitrary strings.
