**Purlin command owner: Builder**

If you are not operating as the Purlin Builder, respond: "This is a Builder command. Ask your Builder agent to run /pl-build instead." and stop.

---

If an argument was provided, implement the named feature from `features/<arg>.md`.

If no argument was provided, read `CRITIC_REPORT.md`, identify the highest-priority Builder action item, and begin implementing it. Check `features/tombstones/` first and process any pending tombstones before regular feature work.

Follow the full per-feature implementation protocol from `instructions/BUILDER_BASE.md` Section 5:

- Pre-flight: read anchor nodes and implementation notes
- Implement and document decisions
- Verify locally with tests
- Commit with a separate status tag commit
