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
- RULE-6: A call may name its own workspace with `project_root`, which is resolved, a leading `~` standing for the home folder, and used for that call alone; without it the tool uses the root the server resolved at startup
- RULE-7: A tool called on a root holding no `.purlin/config.json` answers only with that root, how it was chosen and what to do, rather than reporting or writing a project there
- RULE-8: A tool that raises answers the text `Error running <tool>: <message>`, so one bad call never ends the session
- RULE-9: The configuration tool reads the whole of `.purlin/config.json` or one named key, and a write sets that key in `.purlin/config.json`
- RULE-10: A write naming no key answers that a key is required, and an action that is neither read nor write answers that the action is unknown, in both cases leaving the config as it was
- RULE-22: The plugin manifest starts the server through `sh` and the interpreter resolver, and the last argument it passes names `scripts/mcp/purlin/server.py`

## Proof

- PROOF-1 (RULE-1): A client starts the server as its own process and sends `initialize`; the answer carries the protocol version `2024-11-05`, the server name `purlin`, a version equal to the text of the `VERSION` file, and `tools` among its capabilities
- PROOF-2 (RULE-2): A client sends `tools/list`; the answer names exactly three tools, `drift`, `purlin_config` and `sync_status`, and each of the three lists `project_root` among the arguments it takes and not among those it requires
- PROOF-3 (RULE-3): A client sends the notification `notifications/initialized`, which carries no id, and then a `tools/list` request with the id 9; exactly 1 response comes back, and its id is 9
- PROOF-125 (RULE-3): A client sends the line `not json`; exactly 1 response comes back, an error with the code `-32700`
- PROOF-126 (RULE-3): A client sends the notification `notifications/cancelled`, which the server does not know, and then a `tools/list` request with the id 9; exactly 1 response comes back, and its id is 9
- PROOF-4 (RULE-4): A client calls the tool `nope`, which the server does not serve; the answer is an error with the code `-32601` and the message `Unknown tool: nope`
- PROOF-127 (RULE-4): A client sends a request for the method `nope/at/all`, which the server does not know; the answer is an error with the code `-32601` and the message `Unknown method: nope/at/all`
- PROOF-5 (RULE-5): A client starts the server as its own process in a workspace folder and sends `initialize`; stdout holds exactly 1 line, the JSON-RPC answer, and stderr holds the line `Purlin MCP server v<version> started (root: <root>, ...)`, the version being the text of the `VERSION` file and the root that folder
- PROOF-138 (RULE-5): A client starts the server as its own process in a workspace and calls `sync_status`, `drift` and the configuration tool, with the ids 1, 2 and 3; stdout holds exactly 3 lines, each a JSON-RPC answer, with the ids 1, 2 and 3 in that order
- PROOF-6 (RULE-6): The server is started in an empty folder, and a client calls `sync_status` with `project_root` naming a workspace that holds the spec `login`; the answer is that workspace's status table, opening `Purlin status: proj`, and names `login`
- PROOF-128 (RULE-6): The server is started in an empty folder; a client calls `sync_status` naming a workspace with `project_root`, then calls it again naming none; the second answer is for the empty startup folder and opens `No Purlin workspace at` followed by that folder's path
- PROOF-129 (RULE-6): The server is started in an empty folder, the home folder holds the workspace `ws` with the spec `login`, and a client calls `sync_status` with `project_root` written as `~/ws`; the answer is that workspace's status table, opening `Purlin status: proj`, and names `login`
- PROOF-7 (RULE-7): The server is started in an empty folder, and a client calls `sync_status` with no arguments; the first line of the answer reads `No Purlin workspace at <that folder>: .purlin/config.json is not there. That root came from the working directory, with no .purlin/ marker in it or above it.`, the next names `purlin:init`, and no status table follows
- PROOF-130 (RULE-7): The server is started in a workspace, and a client calls `sync_status` with `project_root` naming an empty folder; the answer opens `No Purlin workspace at <that folder>:` and says `That root came from the project_root argument.`
- PROOF-131 (RULE-7): The server is started in an empty folder, and a client asks the configuration tool to write `gate` as `strong`; the answer opens `No Purlin workspace at`, and the folder still holds no `.purlin/config.json`
- PROOF-132 (RULE-7): The server is started in an empty folder, and a client calls `drift`; the answer opens `No Purlin workspace at` followed by that folder's path
- PROOF-8 (RULE-8): In a workspace where building the status table fails with the message `boom`, a client calls `sync_status`; the answer is a text answer, not an error, reading exactly `Error running sync_status: boom`
- PROOF-133 (RULE-8): In a workspace where building the status table fails with `boom` the first time only, a client sends two `sync_status` calls in one session; 2 answers come back, with the ids 1 and 2, the first reading `Error running sync_status: boom` and the second the status table naming `login`
- PROOF-9 (RULE-9): In a workspace whose gate is `passed`, a client asks the configuration tool to read the key `gate`; the answer is exactly `{"gate": "passed"}`
- PROOF-134 (RULE-9): In a workspace whose gate is `passed`, a client asks the configuration tool to write `gate` as `strong`; the answer reads `Set 'gate' = "strong"`, `.purlin/config.json` then holds the gate `strong` and its other keys as they were, and a read of `gate` answers exactly `{"gate": "strong"}`
- PROOF-135 (RULE-9): A client asks the configuration tool to read and names no key; the answer is exactly what `.purlin/config.json` holds, its three keys `gate`, `project_name` and `tests`
- PROOF-10 (RULE-10): A client asks the configuration tool to write the value `x` and names no key; the answer reads exactly `Error: 'key' is required for write action.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-136 (RULE-10): A client asks the configuration tool for the action `delete` on the key `gate`; the answer reads exactly `Unknown action: delete. Use 'read' or 'write'.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-22 (RULE-22): The plugin manifest `.claude-plugin/plugin.json` starts the `purlin` server with the command `sh`; the first argument it passes ends in `scripts/purlin_python.sh` and the last ends in `scripts/mcp/purlin/server.py`
- PROOF-137 (RULE-22): The command the plugin manifest gives for the `purlin` server, with the plugin's folder in place of `${CLAUDE_PLUGIN_ROOT}`, is run in a workspace and sent `initialize`; exactly 1 line comes back, an answer carrying the server name `purlin`
