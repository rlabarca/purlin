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

- PROOF-1 (RULE-1): Send an `initialize` request to the server as a subprocess; verify the protocol version is exactly `2024-11-05`, the server name is `purlin`, the version equals the contents of the `VERSION` file, and the capabilities carry the tools key
- PROOF-2 (RULE-2): Send `tools/list`; verify the sorted tool names are exactly `drift`, `purlin_config` and `sync_status`, and that every one of the three declares `project_root` among its input properties
- PROOF-3 (RULE-3): Send a notification with no id followed by a `tools/list` request; verify exactly 1 response comes back and its id is 9. Then send the text `not json` on stdin and verify the response carries error code `-32700`
- PROOF-4 (RULE-4): Send a `tools/call` naming the tool `nope` and then the method `nope/at/all`; verify both answer error code `-32601`
- PROOF-5 (RULE-5): Run the server over an `initialize` request and verify every line of stdout parses as JSON, while stderr carries the text `Purlin MCP server`
- PROOF-6 (RULE-6): Start the server in an empty directory and send `sync_status` with `project_root` naming a real workspace; verify the answer carries the feature name `login` from that workspace
- PROOF-7 (RULE-7): Start the server in an empty directory and send `sync_status` with no arguments; verify the answer carries `No Purlin workspace` and names `purlin:init`
- PROOF-8 (RULE-8): Patch the status tool to raise `RuntimeError("boom")` and send a `sync_status` call; verify the answer opens `Error running sync_status` and carries `boom`, and that a second call in the same session still answers normally
- PROOF-9 (RULE-9): Send a read of the key `gate` and verify the answer is exactly `{"gate": "passed"}`; send a write setting it to `strong` and read it again, verifying `{"gate": "strong"}`; then read `.purlin/config.json` from disk and verify its gate reads `strong`
- PROOF-10 (RULE-10): Call the configuration handler with the action `write` and no key; verify the answer names `key` as required. Call it with the action `delete`; verify the answer opens `Unknown action` and that the merged config is unchanged
- PROOF-22 (RULE-22): Read `.claude-plugin/plugin.json` and verify the server entry's command is exactly `sh`, that its first argument ends in `scripts/purlin_python.sh` and that its last ends in `scripts/mcp/purlin/server.py`
