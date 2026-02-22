**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-complete instead." and stop.

---

Given the feature name provided as an argument, gate completion on all requirements:

1. Confirm the feature is in TESTING state (run `tools/cdd/status.sh` if needed).
2. Confirm all manual scenarios have been verified (PASS) in the current session or a prior session.
3. Confirm there are zero OPEN or SPEC_UPDATED discoveries in the feature's `## User Testing Discoveries` section.
4. Check for an active delivery plan at `.agentic_devops/cache/delivery_plan.md`. If the feature appears in any PENDING phase, do NOT mark complete — inform the user it is deferred until all phases are delivered.
5. If all gates pass, commit the Complete status tag:
   `git commit --allow-empty -m "status(<scope>): [Complete features/<name>.md]"`
6. Run `tools/cdd/status.sh` to confirm the feature transitions to COMPLETE.
