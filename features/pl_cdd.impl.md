# Implementation Notes: CDD Dashboard Skill

*   **No Manual Scenarios (Intentional):** This skill is a thin orchestration wrapper around `start.sh` and `stop.sh`. All behavior is testable via automated scenarios exercising the skill's argument parsing, process detection, and script invocation.
*   **Restart Logic Lives in start.sh:** The skill does not manage restart or port preference itself. All restart-on-rerun logic (detect running instance, stop, restart on same port) is handled by `start.sh` per `cdd_lifecycle.md` Section 2.9. The skill is a thin wrapper that invokes the script and relays its output.
