# Implementation Notes: Push to Remote Repository

This is the only global release step with a non-null `code` field. The shell command `git push && git push --tags` is the canonical execution path. However, the Architect always verifies pre-push conditions (Sections 2.1–2.2) before invoking it.

In Purlin's own `.purlin/release/config.json`, this step is `enabled: true`.
