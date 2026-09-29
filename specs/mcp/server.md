# Feature: server

> Description: The Purlin MCP server. It speaks JSON-RPC 2.0 on stdio and serves three
>   tools: the status table, the drift report and the configuration reader and
>   writer. Claude Code starts it when the plugin is enabled, and it answers only
>   what it is asked.
> Scope: scripts/mcp/purlin/server.py, .claude-plugin/plugin.json, scripts/purlin_python.sh
> Stack: python/stdlib, json

## Rules

- RULE-1: The server answers `initialize` with protocol version `2024-11-05`, the server name `purlin`, the version the `VERSION` file carries, and the tools capability a client needs in order to discover that this server serves tools
- RULE-2: `tools/list` returns exactly three tools, `sync_status`, `purlin_config` and `drift`, and every one of them declares the optional `project_root`
- RULE-3: A notification produces no response
- RULE-4: An unknown tool name answers error code `-32601`
- RULE-5: Stdout carries JSON-RPC responses and nothing else; the startup line naming the version and the root goes to stderr
- RULE-6: A call may name its own workspace with `project_root`, which is resolved, a leading `~` standing for the home folder
- RULE-7: A tool called on a root holding no `.purlin/config.json` answers only with that root, how it was chosen and what to do, rather than reporting or writing a project there
- RULE-8: A tool that raises answers the text `Error running <tool>: <message>`, so one bad call never ends the session
- RULE-9: The configuration tool reads the whole of `.purlin/config.json` or one named key, a key that is absent or stored as null answering `{"<key>": null}` in the shape a found key answers; a write sets that key in `.purlin/config.json`, and a save that fails answers `The setting was not saved: <cause>.`
- RULE-10: A write naming no key answers that a key is required, leaving the config as it was
- RULE-22: The plugin manifest starts the server through `sh` and the interpreter resolver, with `PURLIN_PYTHON_SOFT` set to `1`, and the last argument it passes names `scripts/mcp/purlin/server.py`
- RULE-23: Input that is not JSON answers error code `-32700`
- RULE-24: An unknown method answers error code `-32601`
- RULE-25: A call naming no `project_root` uses the root the server resolved at startup, whatever an earlier call named
- RULE-26: An action that is neither read nor write answers that the action is unknown, leaving the config as it was
- RULE-27: A tool called on a workspace whose `.purlin/config.json` cannot be read answers only the sentence `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`
- RULE-28: A write of a setting Purlin knows, `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests` or `ci`, that gives no value answers `A change needs a value; nothing was saved.` and leaves the file byte for byte as it was
- RULE-29: A write of a value a known setting does not take answers `"<value>" is not accepted for <key>; it takes <accepted>. Nothing was saved.` and leaves the file byte for byte as it was: `gate` takes `passed, strong or signed`, `mutation_engine` `none, auto, mutmut, stryker or stryker_net`, `min_strength` `a whole number from 0 to 100, or null`, `audit_parallel` `a whole number from 1 to 16`, `tests` `a list` and `ci` `github, azure or none`
- RULE-30: A write of `version` answers `version is written by purlin:init from Purlin's own version; nothing was saved.` and leaves the file byte for byte as it was
- RULE-31: With no Python 3 found, the interpreter resolver writes its one line to standard error and exits 1, or exits 0 when `PURLIN_PYTHON_SOFT` is `1`

## Proof

- PROOF-1 (RULE-1): A client starts the server as its own process and sends `initialize`; the answer carries the protocol version `2024-11-05`, the server name `purlin`, a version equal to the text of the `VERSION` file, and `tools` among its capabilities
- PROOF-2 (RULE-2): A client sends `tools/list`; the answer names exactly three tools, `drift`, `purlin_config` and `sync_status`, and each of the three lists `project_root` among the arguments it takes and not among those it requires
- PROOF-3 (RULE-3): A client sends the notification `notifications/initialized`, which carries no id, and then a `tools/list` request with the id 9; exactly 1 response comes back, and its id is 9
- PROOF-126 (RULE-3): A client sends the notification `notifications/cancelled`, which the server does not know, and then a `tools/list` request with the id 9; exactly 1 response comes back, and its id is 9
- PROOF-4 (RULE-4): A client calls the tool `nope`, which the server does not serve; the answer is an error with the code `-32601` and the message `Unknown tool: nope`
- PROOF-5 (RULE-5): A client starts the server as its own process in a workspace folder and sends `initialize`; stdout holds exactly 1 line, the JSON-RPC answer, and stderr holds the line `Purlin MCP server v<version> started (root: <root>, ...)`, the version being the text of the `VERSION` file and the root that folder
- PROOF-138 (RULE-5): A client starts the server as its own process in a workspace and calls `sync_status`, `drift` and the configuration tool, with the ids 1, 2 and 3; stdout holds exactly 3 lines, each a JSON-RPC answer, with the ids 1, 2 and 3 in that order
- PROOF-159 (RULE-5): On Windows, a client starts the server in a workspace folder and sends `initialize`; its output holds exactly 1 line, the answer, with no carriage return, and its error stream holds the line `Purlin MCP server v<version> started` @env(windows)
- PROOF-6 (RULE-6): The server is started in an empty folder, and a client calls `sync_status` with `project_root` naming a workspace that holds the spec `login`; the answer is that workspace's status table, opening `Purlin status: proj`, and names `login`
- PROOF-129 (RULE-6): The server is started in an empty folder, the home folder holds the workspace `ws` with the spec `login`, and a client calls `sync_status` with `project_root` written as `~/ws`; the answer is that workspace's status table, opening `Purlin status: proj`, and names `login`
- PROOF-160 (RULE-6): On Windows, the server is started in an empty folder, the home folder holds the workspace `ws` with the spec `login`, and a client asks for status with the folder written as `~/ws`; the answer opens `Purlin status: proj` and names `login` @env(windows)
- PROOF-7 (RULE-7): The server is started in an empty folder, and a client calls `sync_status` with no arguments; the first line of the answer reads `No Purlin workspace at <that folder>: .purlin/config.json is not there. That root came from the working directory, with no .purlin/ marker in it or above it.`, the next names `purlin:init`, and no status table follows
- PROOF-130 (RULE-7): The server is started in a workspace, and a client calls `sync_status` with `project_root` naming an empty folder; the answer opens `No Purlin workspace at <that folder>:` and says `That root came from the project_root argument.`
- PROOF-131 (RULE-7): The server is started in an empty folder, and a client asks the configuration tool to write `gate` as `strong`; the answer opens `No Purlin workspace at`, and the folder still holds no `.purlin/config.json`
- PROOF-132 (RULE-7): The server is started in an empty folder, and a client calls `drift`; the answer opens `No Purlin workspace at` followed by that folder's path
- PROOF-8 (RULE-8): In a workspace where building the status table fails with the message `boom`, a client calls `sync_status`; the answer is a text answer, not an error, reading exactly `Error running sync_status: boom`
- PROOF-133 (RULE-8): In a workspace where building the status table fails with `boom` the first time only, a client sends two `sync_status` calls in one session; 2 answers come back, with the ids 1 and 2, the first reading `Error running sync_status: boom` and the second the status table naming `login`
- PROOF-9 (RULE-9): In a workspace whose gate is `passed`, a client asks the configuration tool to read the key `gate`; the answer is exactly `{"gate": "passed"}`
- PROOF-134 (RULE-9): In a workspace whose gate is `passed`, a client asks the configuration tool to write `gate` as `strong`; the answer reads `Set 'gate' = "strong"`, `.purlin/config.json` then holds the gate `strong` and its other keys as they were, and a read of `gate` answers exactly `{"gate": "strong"}`
- PROOF-135 (RULE-9): A client asks the configuration tool to read and names no key; the answer is exactly what `.purlin/config.json` holds, its three keys `gate`, `project_name` and `tests`
- PROOF-142 (RULE-9): In a workspace whose settings hold no `ci`, a client asks the configuration tool to read the key `ci`; the answer is the JSON `{"ci": null}`, indented over three lines as a found key's answer is
- PROOF-143 (RULE-9): In a workspace whose settings hold `min_strength` as null, a client asks the configuration tool to read `min_strength`; the answer is the JSON `{"min_strength": null}`, indented over three lines as a found key's answer is
- PROOF-144 (RULE-9): In a workspace whose gate is `passed`, a client asks the configuration tool to write `gate` as `strong` while the disk is full; the answer reads exactly `The setting was not saved: No space left on device.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-145 (RULE-9): In a workspace whose settings hold no `team`, a client asks the configuration tool to write `team` as `blue`, a setting Purlin does not know; the answer reads `Set 'team' = "blue"`, and `.purlin/config.json` then holds `team` as `blue`
- PROOF-10 (RULE-10): A client asks the configuration tool to write the value `x` and names no key; the answer reads exactly `Error: 'key' is required for write action.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-22 (RULE-22): The plugin manifest `.claude-plugin/plugin.json` starts the `purlin` server with the command `sh`; the first argument it passes ends in `scripts/purlin_python.sh` and the last ends in `scripts/mcp/purlin/server.py`
- PROOF-137 (RULE-22): The command the plugin manifest gives for the `purlin` server, with the plugin's folder in place of `${CLAUDE_PLUGIN_ROOT}`, is run in a workspace and sent `initialize`; exactly 1 line comes back, an answer carrying the server name `purlin`
- PROOF-158 (RULE-22): The plugin manifest's entry for the `purlin` server sets the environment variable `PURLIN_PYTHON_SOFT` to `1`, beside its command `sh` and its arguments
- PROOF-161 (RULE-22): On Windows, the command the plugin gives for the `purlin` server, with the plugin's folder filled in, is run in a workspace and sent `initialize`; exactly 1 line comes back, an answer naming the server `purlin` @env(windows)
- PROOF-125 (RULE-23): A client sends the line `not json`; exactly 1 response comes back, an error with the code `-32700`
- PROOF-127 (RULE-24): A client sends a request for the method `nope/at/all`, which the server does not know; the answer is an error with the code `-32601` and the message `Unknown method: nope/at/all`
- PROOF-128 (RULE-25): The server is started in an empty folder; a client calls `sync_status` naming a workspace with `project_root`, then calls it again naming none; the second answer is for the empty startup folder and opens `No Purlin workspace at` followed by that folder's path
- PROOF-136 (RULE-26): A client asks the configuration tool for the action `delete` on the key `gate`; the answer reads exactly `Unknown action: delete. Use 'read' or 'write'.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-139 (RULE-27): In a workspace whose `.purlin/config.json` holds `{` on one line and `  "gate": "passed",}` on the next, a client calls `sync_status`; the answer is exactly `.purlin/config.json cannot be read: <the JSON reader's message> at line 2. Fix the file by hand; nothing ran and nothing was saved.`
- PROOF-140 (RULE-27): In a workspace whose `.purlin/config.json` holds `{` on one line and `  "gate": "passed",}` on the next, a client calls `drift`; the answer is exactly `.purlin/config.json cannot be read: <the JSON reader's message> at line 2. Fix the file by hand; nothing ran and nothing was saved.`
- PROOF-141 (RULE-27): In a workspace whose `.purlin/config.json` holds `{` on one line and `  "gate": "passed",}` on the next, a client asks the configuration tool to write `gate` as `strong`; the answer is exactly `.purlin/config.json cannot be read: <the JSON reader's message> at line 2. Fix the file by hand; nothing ran and nothing was saved.`, and the file is unchanged
- PROOF-146 (RULE-28): A client asks the configuration tool to write `gate` and gives no value; the answer reads exactly `A change needs a value; nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-147 (RULE-29): A client asks the configuration tool to write `gate` as `gold`; the answer reads exactly `"gold" is not accepted for gate; it takes passed, strong or signed. Nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-148 (RULE-29): A client asks the configuration tool to write `mutation_engine` as `pitest`; the answer reads exactly `"pitest" is not accepted for mutation_engine; it takes none, auto, mutmut, stryker or stryker_net. Nothing was saved.`, and the file is byte for byte as it was
- PROOF-149 (RULE-29): A client asks the configuration tool to write `min_strength` as the number 101; the answer reads exactly `"101" is not accepted for min_strength; it takes a whole number from 0 to 100, or null. Nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-150 (RULE-29): A client asks the configuration tool to write `audit_parallel` as the number 17; the answer reads exactly `"17" is not accepted for audit_parallel; it takes a whole number from 1 to 16. Nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-151 (RULE-29): A client asks the configuration tool to write `tests` as the text `pytest`; the answer reads exactly `"pytest" is not accepted for tests; it takes a list. Nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-152 (RULE-29): A client asks the configuration tool to write `ci` as `gitlab`; the answer reads exactly `"gitlab" is not accepted for ci; it takes github, azure or none. Nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-153 (RULE-29): A client asks the configuration tool to write `min_strength` as null; the answer reads `Set 'min_strength' = null`, and `.purlin/config.json` then holds `min_strength` as null
- PROOF-154 (RULE-29): A client asks the configuration tool to write `gate` as null; the answer reads exactly `"null" is not accepted for gate; it takes passed, strong or signed. Nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-155 (RULE-30): A client asks the configuration tool to write `version` as `9.9.9`; the answer reads exactly `version is written by purlin:init from Purlin's own version; nothing was saved.`, and `.purlin/config.json` is byte for byte as it was
- PROOF-156 (RULE-31): The interpreter resolver is started by `/bin/sh` on the server's script with a search path holding no Python and no `py`, and `PURLIN_PYTHON` unset; it exits 1, prints nothing to standard output, and writes to standard error only `purlin: no Python 3 interpreter found; tried $PURLIN_PYTHON, python3, python and py -3. Set PURLIN_PYTHON to the one to use.`
- PROOF-157 (RULE-31): The interpreter resolver is started by `/bin/sh` on the server's script with a search path holding no Python and no `py`, `PURLIN_PYTHON` unset and `PURLIN_PYTHON_SOFT` set to `1`; it exits 0 and writes to standard error only `purlin: no Python 3 interpreter found; tried $PURLIN_PYTHON, python3, python and py -3. Set PURLIN_PYTHON to the one to use.`
