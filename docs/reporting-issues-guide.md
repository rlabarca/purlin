# Reporting Purlin Issues

## When to Use This

Use `purlin:purlin-issue` when you find a bug in the **Purlin framework itself** — not in your project's application code.

Examples: a skill behaves incorrectly, `purlin:init` fails, agent startup crashes, or a documented workflow doesn't work as described.

For application-level bugs (features not working correctly), use `purlin:discovery` instead — that records findings in your project's discovery files and routes them to the right mode.

---

## How to Use It

From any session:

```
purlin:purlin-issue Spec Gate reports FAIL for a feature with all required sections
```

Or run it without arguments and describe the issue when asked.

The command automatically collects your Purlin version, deployment mode, OS, current branch, recent git history, and working tree state. It produces a formatted report you can copy.

---

## Where to Send the Report

Copy the text between the dividers and either:

1. **Paste it into a PM session** in the Purlin framework repository.
2. **File an issue** at the Purlin project's repository.
3. **Send it to a framework maintainer** directly.

The report is self-contained — the recipient won't need to ask follow-up questions about your environment.

---

## Tips

- Run it immediately when you hit the issue — your git state and conversation context are captured as-is.
- Include reproduction steps in your description — the command collects environment data, but only you know the exact sequence of actions.
- Check `purlin:status` first — the issue may already be flagged.
