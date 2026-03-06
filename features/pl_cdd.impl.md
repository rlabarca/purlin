# Implementation Notes: CDD Dashboard Skill

*   **No Manual Scenarios (Intentional):** This skill is a thin orchestration wrapper around `start.sh` and `stop.sh`. All behavior is testable via automated scenarios exercising the skill's argument parsing, process detection, and script invocation.
*   **Port Preference Mechanism:** The `start.sh` script needs to accept a port preference (via `--port` argument or `CDD_PORT` env var). The skill reads `.purlin/runtime/cdd.port` before stopping the existing server, then passes the port to `start.sh`. If `start.sh` cannot bind to the preferred port, it falls back to OS-assigned port selection.
