**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-verify instead." and stop.

---

If an argument was provided, begin interactive verification for `features/<arg>.md`.

If no argument was provided, run `tools/cdd/status.sh` and identify the next TESTING feature with manual scenarios.

For the target feature, execute the interactive verification workflow from `instructions/QA_BASE.md` Section 5:

1. Present the feature name, Critic report summary, and verification scope.
2. Walk through each manual scenario step by step, asking PASS / FAIL / DISPUTE after each.
3. Run the visual verification pass if the feature has a `## Visual Specification` section.
4. Record any discoveries and commit them.
5. After all scenarios pass with zero discoveries, run `/pl-complete <name>` to mark it done.
