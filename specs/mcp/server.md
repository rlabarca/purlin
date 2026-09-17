# Feature: server

> Description: The Purlin MCP server and the one background hook that calls
>   into it. The server speaks JSON-RPC 2.0 on stdio and serves three tools:
>   the status table, the drift report and the configuration reader and
>   writer. `generate_digest` builds the dashboard's data file from what is
>   already on disk, and the refresh hook calls it after a tool call or a turn
>   changed an input, silently and without ever blocking.
> Scope: scripts/mcp/purlin/server.py, scripts/hooks/refresh_digest.py, hooks/hooks.json, .claude-plugin/plugin.json
> Stack: python/stdlib, json, Claude Code plugin hooks

## Rules

- RULE-1: The server answers `initialize` with protocol version `2024-11-05`, the server name `purlin`, the version the `VERSION` file carries, and the tools capability a client needs in order to discover that this server serves tools [risk: high] [origin: eng]
- RULE-2: `tools/list` returns exactly three tools, `sync_status`, `purlin_config` and `drift`, and every one of them declares the optional `project_root` [risk: high] [origin: eng]
- RULE-3: A notification produces no response, and input that is not JSON answers error code `-32700` [risk: medium] [origin: eng]
- RULE-4: An unknown tool name and an unknown method each answer error code `-32601` [risk: medium] [origin: eng]
- RULE-5: Stdout carries JSON-RPC responses and nothing else; the startup line naming the version and the root goes to stderr [risk: high] [origin: eng]
- RULE-6: A call may name its own workspace with `project_root`, which is resolved and used for that call alone; without it the tool uses the root the server resolved at startup [risk: high] [origin: eng]
- RULE-7: A root holding no `.purlin/config.json` answers with a line naming that root, how it was chosen and what to run, rather than reporting a project with nothing in it [risk: high] [origin: eng]
- RULE-8: A tool that raises answers with the text `Error running <tool>` and the message, so one bad call never ends the session [risk: medium] [origin: eng]
- RULE-9: The configuration tool reads the whole merged config or one named key, and a write reaches `config.local.json` and never the committed `config.json` [risk: high] [origin: eng]
- RULE-10: A write naming no key answers that a key is required, and an action that is neither read nor write answers that the action is unknown, in both cases leaving the config as it was [risk: medium] [origin: eng]
- RULE-11: `generate_digest` writes the dashboard's data file at schema version 4, naming the producer it was given [risk: high] [origin: eng]
- RULE-12: A root holding no config writes no data file and returns nothing [risk: medium] [origin: eng]
- RULE-13: The refresh hook exits 0 and writes zero bytes to stdout and to stderr on every path, including a directory that is not a git repository, a held lock, and a run the environment asked it to skip: a refresh that did not happen is a stale dashboard, never a blocked tool call [risk: high] [origin: eng]
- RULE-14: The hook regenerates only when an input is newer than the data file: the spec directory, the runtime proof files, the records and `.purlin/config.json`, with a missing data file counting as newer. Nothing else under `.purlin/runtime/` is an input, so a run can never make the next run dirty [risk: high] [origin: eng]
- RULE-15: The spec directory the hook walks is the literal `specs`, read from no config key, so a stray directory setting in a project's config cannot redirect the check [risk: medium] [origin: eng]
- RULE-16: One generation at a time: the hook takes a lock that does not wait, and a second instance finding it held leaves without generating, because the holder re-reads the inputs after writing [risk: high] [origin: eng]
- RULE-17: After writing, the hook re-reads the inputs against the moment it started generating and builds again when something landed meanwhile, at most three times in one run [risk: medium] [origin: eng]
- RULE-18: The hook leaves without generating when `.purlin/config.json` is missing or unreadable, when its `digest` reads `off`, when `PURLIN_SKIP_DIGEST` is `1`, or when the repository holds an index lock, because a commit is in flight and the pre-commit hook owns that regeneration [risk: high] [origin: eng]
- RULE-19: Those are the only conditions that stop a refresh: the config `purlin:init` stamps into a new project names neither `digest` nor `report`, and a project holding exactly that config refreshes [risk: high] [origin: eng]
- RULE-20: The hook generates with the producer `hook`, the network off and a write only if the payload changed, so no remote is ever listed from a background hook and an unchanged payload is touched rather than rewritten into a dirty working tree [risk: high] [origin: eng]
- RULE-21: `hooks/hooks.json` registers this one script under exactly the events `PostToolUse` with the matcher `Bash|Write|Edit|MultiEdit`, `SubagentStop` and `Stop`, every entry a command with an integer timeout that runs without waiting, each command reaching the script through the interpreter resolver so that no interpreter is named; no entry exists under any event through which a hook could gate or steer a turn [risk: high] [origin: eng]
- RULE-22: The plugin manifest starts the server through `sh` and the interpreter resolver, and the last argument it passes names `scripts/mcp/purlin/server.py` [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Send an `initialize` request to the server as a subprocess; verify the protocol version is exactly `2024-11-05`, the server name is `purlin`, the version equals the contents of the `VERSION` file, and the capabilities carry the tools key @integration
- PROOF-2 (RULE-2): Send `tools/list`; verify the sorted tool names are exactly `drift`, `purlin_config` and `sync_status`, and that every one of the three declares `project_root` among its input properties @integration
- PROOF-3 (RULE-3): Send a notification with no id followed by a `tools/list` request; verify exactly 1 response comes back and its id is 9. Then send the text `not json` on stdin and verify the response carries error code `-32700` @integration
- PROOF-4 (RULE-4): Send a `tools/call` naming the tool `nope` and then the method `nope/at/all`; verify both answer error code `-32601` @integration
- PROOF-5 (RULE-5): Run the server over an `initialize` request and verify every line of stdout parses as JSON, while stderr carries the text `Purlin MCP server` @integration
- PROOF-6 (RULE-6): Start the server in an empty directory and send `sync_status` with `project_root` naming a real workspace; verify the answer carries the feature name `login` from that workspace @integration
- PROOF-7 (RULE-7): Start the server in an empty directory and send `sync_status` with no arguments; verify the answer carries `No Purlin workspace` and names `purlin:init` @integration
- PROOF-8 (RULE-8): Patch the status tool to raise `RuntimeError("boom")` and send a `sync_status` call; verify the answer opens `Error running sync_status` and carries `boom`, and that a second call in the same session still answers normally @integration
- PROOF-9 (RULE-9): Send a read of the key `gate` and verify the answer is exactly `{"gate": "passed"}`; send a write setting it to `strong` and read it again, verifying `{"gate": "strong"}`; then read `.purlin/config.json` from disk and verify its gate still reads `passed` @integration
- PROOF-10 (RULE-10): Call the configuration handler with the action `write` and no key; verify the answer names `key` as required. Call it with the action `delete`; verify the answer opens `Unknown action` and that the merged config is unchanged @integration
- PROOF-11 (RULE-11): Call `generate_digest` with the producer `hook` and the network off; verify the file it names exists, that the payload read back carries `generated_by` `hook` and that its schema version is exactly 4 @integration
- PROOF-12 (RULE-12): Call `generate_digest` on a directory holding no `.purlin/config.json`; verify it returns nothing and writes no file @integration
- PROOF-13 (RULE-13): Run the hook as a subprocess with hook-shaped JSON on stdin in five settings: a temporary git project with no data file; a directory that is not a git repository; a project whose config turns the digest off; a project whose lock the test holds; and a run with the skip variable set to `1`. Verify every run exits 0 with zero bytes on stdout and zero bytes on stderr, and that only the first writes the data file @integration
- PROOF-14 (RULE-14): Run the hook and record the data file's bytes and modification time; run it again with nothing changed and verify both are identical; create a file under `.purlin/runtime/` newer than the data file and verify both are still identical; append a second proof entry to the feature's proof file and verify the digest's proved count rises from 1 to 2; then touch `.purlin/config.json` and verify the modification time advances @integration
- PROOF-15 (RULE-15): Read the hook's source and verify it reads no key named `spec_dir` from the config; then write that key into a project's config naming another directory, run the hook, and verify the digest still reports the 1 proof under `specs/` @integration
- PROOF-16 (RULE-16): Make the project dirty, take the hook's lock from the test, run the hook as a subprocess and verify it exits 0 with no output and writes no data file; release the lock, run it again and verify the data file appears @integration
- PROOF-17 (RULE-17): Call the hook in-process with the generator replaced by a wrapper that, on its first call only, appends a proof entry after delegating; verify the wrapper ran exactly 2 times and the data file carries the appended proof. Replace it with a wrapper that always appends and verify it ran exactly 3 times @integration
- PROOF-18 (RULE-18): Run the hook in a dirty temporary git project under each of: no `.purlin/config.json`; a config whose `digest` reads `off`; the skip variable set to `1`; and an index lock present in the git directory. Verify no data file is written in any of them and every run exits 0 in silence; then remove the index lock and verify the data file is written @integration
- PROOF-19 (RULE-19): Read `templates/config.json`, the file `purlin:init` stamps into a new project, and verify it carries neither a `digest` nor a `report` key; run the hook in a project configured with exactly that file and verify the data file is written and reports the 1 proof the project has @integration
- PROOF-20 (RULE-20): Declare an anchor with a git source and a pin, call the hook in-process with every git call captured, and verify no captured call lists a remote and that the data file names the producer `hook` and carries the anchor's source and pin. Then set the data file's modification time into the past and call again with the inputs unchanged, verifying the bytes are identical while the modification time advanced @integration
- PROOF-21 (RULE-21): Read `hooks/hooks.json` and verify its event keys are exactly `PostToolUse`, `SubagentStop` and `Stop`, that the first matcher is `Bash|Write|Edit|MultiEdit`, that all 3 entries are commands with an integer timeout that run without waiting, that every command is exactly the interpreter resolver invoked on the hook script, that the token `python3` appears nowhere in the file, and that no key named `PreToolUse`, `PermissionRequest` or `UserPromptSubmit` exists
- PROOF-22 (RULE-22): Read `.claude-plugin/plugin.json` and verify the server entry's command is exactly `sh`, that its first argument ends in `scripts/purlin_python.sh` and that its last ends in `scripts/mcp/purlin/server.py`
