# Feature: server

> Description: The Purlin MCP server. It speaks JSON-RPC 2.0 on stdio and serves three
>   tools: the status table, the drift report and the configuration reader and
>   writer. Claude Code starts it when the plugin is enabled, and it answers only
>   what it is asked.
> Scope: scripts/mcp/purlin/server.py, .claude-plugin/plugin.json, scripts/purlin_python.sh
> Stack: python/stdlib, json
> Highest-Rule: 37
> Highest-Proof: 169

## Rules

- RULE-1: The server answers `initialize` with protocol version `2024-11-05`, the server name `purlin`, the version the `VERSION` file carries, and the tools capability a client needs in order to discover that this server serves tools
- RULE-2: `tools/list` returns exactly three tools, `sync_status`, `purlin_config` and `drift`, and every one of them declares the optional `project_root`
- RULE-5: Stdout carries JSON-RPC responses and nothing else; the startup line naming the version and the root goes to stderr
- RULE-6: A call names its project root with `project_root`, which is resolved, a leading `~` standing for the home folder
- RULE-7: A tool called on a root holding no `.purlin/config.json`, or one that cannot be read, answers only what is wrong and what to do, and reports or writes nothing there
- RULE-8: A tool that raises answers the text `Error running <tool>: <message>`, so one bad call never ends the session
- RULE-9: The configuration tool reads the whole of `.purlin/config.json` or one named key, a key that is absent or stored as null answering `{"<key>": null}`, and a write sets that key in `.purlin/config.json`
- RULE-22: The plugin manifest starts the server through `sh` and the interpreter resolver, with `PURLIN_PYTHON_SOFT` set to `1`, and the last argument it passes names `scripts/mcp/purlin/server.py`
- RULE-31: With no Python 3 found, the interpreter resolver writes its one line to standard error and exits 1, or exits 0 when `PURLIN_PYTHON_SOFT` is `1`
- RULE-35: The server keeps to JSON-RPC 2.0: a notification gets no response, input that is not JSON answers error code `-32700`, and an unknown method or tool answers error code `-32601`
- RULE-36: Each write the configuration tool refuses names why and leaves `.purlin/config.json` byte for byte as it was: a write with no key or no value, an action neither read nor write, a `tests` that is not a list, a write of `version`, and a write of any key but `version` and `tests`
- RULE-37: A tool call that names no `project_root` is refused with the one line `<tool> needs project_root: pass the top folder of the git checkout you are working in.`, and nothing is read from or written to the folder the server started in, whatever an earlier call named

## Proof

- PROOF-1 (RULE-1): A client starts the server as its own process and sends `initialize`; the answer carries the protocol version `2024-11-05`, the server name `purlin`, a version equal to the text of the `VERSION` file, and `tools` among its capabilities
- PROOF-2 (RULE-2): A client sends `tools/list`; the answer names exactly three tools, `drift`, `purlin_config` and `sync_status`, and each of the three lists `project_root` among the arguments it takes and not among those it requires
- PROOF-138 (RULE-5): A client starts the server as its own process in a workspace and calls `sync_status`, `drift` and the configuration tool, with the ids 1, 2 and 3; stdout holds exactly 3 lines, each a JSON-RPC answer, with the ids 1, 2 and 3 in that order
- PROOF-159 (RULE-5): On Windows, a client starts the server in a workspace folder and sends `initialize`; its output holds exactly 1 line, the answer, with no carriage return, and its error stream holds the line `Purlin MCP server v<version> started` @env(windows)
- PROOF-129 (RULE-6): The server is started in an empty folder, the home folder holds the workspace `ws` with the spec `login`, and a client calls `sync_status` with `project_root` written as `~/ws`; the answer is that workspace's status table, opening `Purlin status: ws,`, and names `login`
- PROOF-160 (RULE-6): On Windows, the server is started in an empty folder, the home folder holds the workspace `ws` with the spec `login`, and a client asks for status with the folder written as `~/ws`; the answer opens `Purlin status: ws,` and names `login` @env(windows)
- PROOF-168 (RULE-7): A client calls `sync_status` with `project_root` naming an empty folder; the first line of the answer opens `No Purlin project root at <that folder>: .purlin/config.json is not there.`
- PROOF-169 (RULE-7): A client asks the configuration tool, with `project_root` naming an empty folder, to write `tests` as an empty list; the answer opens `No Purlin project root at`, and the folder still holds no `.purlin/config.json`
- PROOF-141 (RULE-7): In a workspace whose `.purlin/config.json` holds `{` on one line and `  "tests": [],}` on the next, a client asks the configuration tool to write `tests` as `[]`; the answer is exactly `.purlin/config.json cannot be read: <the JSON reader's message> at line 2. Fix the file by hand; nothing ran and nothing was saved.`, and the file is unchanged
- PROOF-133 (RULE-8): In a workspace where building the status table fails with `boom` the first time only, a client sends two `sync_status` calls in one session; 2 answers come back, with the ids 1 and 2, the first reading `Error running sync_status: boom` and the second the status table naming `login`
- PROOF-9 (RULE-9): In a workspace whose settings hold `tests` as an empty list, a client asks the configuration tool to read the key `tests`; the answer is exactly `{"tests": []}`
- PROOF-134 (RULE-9): In a project whose settings hold `tests` as an empty list, a client asks the configuration tool to write `tests` as `[{"name": "pytest"}]`; the answer reads exactly `tests is now [{"name": "pytest"}]; saved to .purlin/config.json.`, and `.purlin/config.json` then holds that `tests` and its `version` as it was
- PROOF-142 (RULE-9): In a workspace whose settings hold no `tests`, a client asks the configuration tool to read the key `tests`; the answer is the JSON `{"tests": null}`, indented over three lines as a found key's answer is
- PROOF-137 (RULE-22): The command the plugin manifest gives for the `purlin` server, with the plugin's folder in place of `${CLAUDE_PLUGIN_ROOT}`, is run in a workspace and sent `initialize`; exactly 1 line comes back, an answer carrying the server name `purlin`
- PROOF-158 (RULE-22): The plugin manifest's entry for the `purlin` server sets the environment variable `PURLIN_PYTHON_SOFT` to `1`, beside its command `sh` and its arguments
- PROOF-156 (RULE-31): The interpreter resolver is started by `/bin/sh` on the server's script with a search path holding no Python and no `py`, and `PURLIN_PYTHON` unset; it exits 1, prints nothing to standard output, and writes to standard error only `purlin: no Python 3 interpreter found; tried $PURLIN_PYTHON, python3, python and py -3. Set PURLIN_PYTHON to the one to use.`
- PROOF-157 (RULE-31): The interpreter resolver is started by `/bin/sh` on the server's script with a search path holding no Python and no `py`, `PURLIN_PYTHON` unset and `PURLIN_PYTHON_SOFT` set to `1`; it exits 0 and writes to standard error only `purlin: no Python 3 interpreter found; tried $PURLIN_PYTHON, python3, python and py -3. Set PURLIN_PYTHON to the one to use.`
- PROOF-3 (RULE-35): A client sends the notification `notifications/initialized`, which carries no id, and then a `tools/list` request with the id 9; exactly 1 response comes back, and its id is 9
- PROOF-125 (RULE-35): A client sends the line `not json`; exactly 1 response comes back, an error with the code `-32700`
- PROOF-127 (RULE-35): A client sends a request for the method `nope/at/all`, which the server does not know; the answer is an error with the code `-32601` and the message `Unknown method: nope/at/all`
- PROOF-155 (RULE-36): A client asks the configuration tool to write `version` as `9.9.9`; the answer reads exactly `version is written by purlin:init from Purlin's own version; nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-151 (RULE-36): A client asks the configuration tool to write `tests` as the text `pytest`; the answer reads exactly `"pytest" is not accepted for tests; it takes a list. Nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-164 (RULE-36): A client asks the configuration tool to write `gate` as `signed`; the answer reads exactly `gate is not a setting; .purlin/config.json holds version and tests. Nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-166 (RULE-37): The server is started in a workspace with the spec `login`; a client calls `sync_status` with no arguments; the answer is exactly `sync_status needs project_root: pass the top folder of the git checkout you are working in.` and does not name `login`
- PROOF-167 (RULE-37): The server is started in a workspace; a client calls `sync_status` naming another workspace with `project_root`, then asks the configuration tool to write `tests` as `[]` naming none; the second answer opens `purlin_config needs project_root:`, and the startup workspace's `.purlin/config.json` is byte for byte as it was
