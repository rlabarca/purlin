# Feature: server

> Description: The Purlin MCP server. It speaks JSON-RPC 2.0 on stdio and serves three
>   tools: the status table, the drift report and the configuration reader and
>   writer. Claude Code starts it when the plugin is enabled, and it answers only
>   what it is asked.
> Scope: scripts/mcp/purlin/server.py, .claude-plugin/plugin.json
> Stack: python/stdlib, json

## Rules

- RULE-1: The server answers `initialize` with protocol version `2024-11-05`, the server name `purlin`, the version the `VERSION` file carries, and the tools capability a client needs in order to discover that this server serves tools
- RULE-2: `tools/list` returns exactly three tools, `sync_status`, `purlin_config` and `drift`, and every one of them declares the optional `project_root`
- RULE-3: A notification produces no response, and input that is not JSON answers error code `-32700`
- RULE-4: An unknown tool name and an unknown method each answer error code `-32601`
- RULE-5: Stdout carries JSON-RPC responses and nothing else; the startup line naming the version and the root goes to stderr
- RULE-6: A call may name its own workspace with `project_root`, which is resolved and used for that call alone; without it the tool uses the root the server resolved at startup
- RULE-7: A root holding no `.purlin/config.json` answers with a line naming that root, how it was chosen and what to run, rather than reporting a project with nothing in it
- RULE-8: A tool that raises answers with the text `Error running <tool>` and the message, so one bad call never ends the session
- RULE-9: The configuration tool reads the whole of `.purlin/config.json` or one named key, and a write sets that key in `.purlin/config.json`
- RULE-10: A write naming no key answers that a key is required, and an action that is neither read nor write answers that the action is unknown, in both cases leaving the config as it was
- RULE-22: The plugin manifest starts the server through `sh` and the interpreter resolver, and the last argument it passes names `scripts/mcp/purlin/server.py`

## Proof

- PROOF-1 (RULE-1): A client starts the server as its own process and sends `initialize`; the answer carries the protocol version `2024-11-05`, the server name `purlin` and a version equal to the text of the `VERSION` file
- PROOF-2 (RULE-2): A client sends `tools/list`; the answer names exactly three tools, `drift`, `purlin_config` and `sync_status`, and each of the three lists `project_root` among the arguments it takes
- PROOF-3 (RULE-3): A client sends a notification, which carries no id, and then a `tools/list` request with the id 9; exactly 1 response comes back, and its id is 9. A client that sends the line `not json` gets back an error with the code `-32700`
- PROOF-4 (RULE-4): A client calls the tool `nope`, which the server does not serve, and then the method `nope/at/all`, which it does not know; each answer is an error with the code `-32601`
- PROOF-5 (RULE-5): A client starts the server as its own process and sends `initialize`; every line the server writes to stdout reads as JSON, and the startup line, carrying `Purlin MCP server`, is on stderr and not on stdout
- PROOF-6 (RULE-6): The server is started in an empty folder, and a client calls `sync_status` with `project_root` naming a workspace that holds the spec `login`; the answer is that workspace's status and names `login`
- PROOF-7 (RULE-7): The server is started in an empty folder, and a client calls `sync_status` with no arguments; the answer carries `No Purlin workspace` and names `purlin:init` as the command to run
- PROOF-8 (RULE-8): The status tool is made to fail with the message `boom`, and a client calls `sync_status`; the answer opens `Error running sync_status` and carries `boom`. Once the fault is gone, a second call to the same server answers with the status table, which carries `Tests`
- PROOF-9 (RULE-9): In a workspace whose gate is `passed`, a client reads the key `gate` and gets exactly `{"gate": "passed"}`; it writes `gate` as `strong` and reads it again, getting exactly `{"gate": "strong"}`; `.purlin/config.json` on disk then carries the gate `strong`
- PROOF-10 (RULE-10): A client asks the configuration tool to write the value `x` and names no key; the answer carries `'key' is required`. It asks for the action `delete` on the key `gate`; the answer opens `Unknown action`. After both, the configuration reads back exactly as it did before either
- PROOF-22 (RULE-22): The plugin manifest `.claude-plugin/plugin.json` starts the `purlin` server with the command `sh`; the first argument it passes ends in `scripts/purlin_python.sh` and the last ends in `scripts/mcp/purlin/server.py`
