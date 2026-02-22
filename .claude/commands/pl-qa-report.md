**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-qa-report instead." and stop.

---

Run `tools/cdd/status.sh` and read `CRITIC_REPORT.md` to produce a QA-focused summary:

1. **Features in TESTING:** List each feature with its scenario count, verification scope, and any open discoveries.
2. **Open Discoveries:** List all OPEN and SPEC_UPDATED discoveries across all features, grouped by type (BUG / DISCOVERY / INTENT_DRIFT / SPEC_DISPUTE).
3. **Completion Blockers:** For each TESTING feature, list what is blocking it from being marked [Complete] (open discoveries, unverified scenarios, pending delivery phases).
4. **Delivery Plan Context:** If a delivery plan exists, show which features are fully delivered vs. phase-gated.
