**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-qa-report instead." and stop.

---

Run `tools/cdd/status.sh --role qa` to get QA-filtered status and produce a QA-focused summary:

1.  **Features in TESTING:** List each feature with its manual scenario count, verification scope (full/targeted/cosmetic/dependency-only), and any open discoveries.
2.  **Open Discoveries:** List all OPEN and SPEC_UPDATED discoveries across all features, grouped by type (BUG / DISCOVERY / INTENT_DRIFT / SPEC_DISPUTE). Include the feature name, discovery title, and status for each.
3.  **Completion Blockers:** For each TESTING feature, list what is blocking it from `[Complete]`:
    *   Open discoveries (count and types)
    *   Unverified scenarios
    *   Pending delivery phases
4.  **Delivery Plan Context:** If `.purlin/cache/delivery_plan.md` exists, show which features are fully delivered (eligible for `[Complete]`) vs. phase-gated (more work coming in future phases).
5.  **Effort Estimate:** Total items requiring manual verification across all TESTING features after scope filtering.
