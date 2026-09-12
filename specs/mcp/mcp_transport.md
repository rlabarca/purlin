# Feature: mcp_transport

> Requires: security_no_dangerous_patterns
> Scope: scripts/mcp/purlin_server.py, scripts/mcp/manifest.json
> Stack: python/stdlib, json
> Description: JSON-RPC 2.0 transport layer for the Purlin MCP server. Reads requests from stdin, dispatches to tool handlers, writes responses to stdout. Implements MCP protocol initialization and error handling.

## Rules

- RULE-1: The server implements MCP protocol version `2024-11-05` and responds to `initialize` with protocolVersion, capabilities, and serverInfo
- RULE-2: `tools/list` returns exactly 3 tools: `sync_status`, `purlin_config`, `drift` — matching the manifest definitions
- RULE-3: `notifications/initialized` produces no response (notification, not request)
- RULE-4: Invalid JSON input returns error code `-32700` (Parse error)
- RULE-5: Unknown methods return error code `-32601` with the method name in the message
- RULE-6: Unknown tool names in `tools/call` return error code `-32601` with the tool name in the message
- RULE-7: Server logs startup to stderr — stdout is reserved for JSON-RPC responses
- RULE-8: The main loop reloads its own source only when the environment sets `PURLIN_DEV_RELOAD=1`: with the variable unset or holding any other value the loop never stats the source and never reloads it. When a reload is attempted and raises, the server writes `Purlin MCP: reload failed` plus the traceback to stderr (never to stdout) and answers that request, and every later one, with the module it had already loaded

## Proof

- PROOF-1 (RULE-1): Send an `initialize` request; verify `result.protocolVersion` equals `2024-11-05`, `result.serverInfo.name` equals `purlin`, and `result.capabilities` is present and equals `{"tools": {}}`, the tools capability a client needs to discover that this server serves tools @integration
- PROOF-2 (RULE-2): Send `tools/list`; verify the result holds exactly 3 tools whose sorted names are `drift`, `purlin_config`, `sync_status`, that those names equal the names declared in `scripts/mcp/manifest.json`, and that each tool carries a non-empty `description` plus an `inputSchema` of `type` `object` whose property names are `role` for `sync_status`, `action`, `key`, `value` for `purlin_config`, and `since`, `role` for `drift` @integration
- PROOF-3 (RULE-3): Send the notification `notifications/initialized` with no `id`; verify `handle_request` returns `None` rather than a response object, so there is nothing for the loop to write @integration
- PROOF-4 (RULE-4): Send invalid JSON; verify error code -32700 @integration
- PROOF-5 (RULE-5): Send unknown method; verify error code -32601 with method name @integration
- PROOF-6 (RULE-6): Send tools/call with unknown tool; verify error code -32601 with tool name @integration
- PROOF-7 (RULE-7): Run the server main loop on empty stdin; verify stderr carries the startup text `Purlin MCP server` and that stdout is the empty string @integration
- PROOF-8 (RULE-8): Run a COPY of `scripts/mcp/purlin_server.py` as a subprocess over two `initialize` requests and rewrite the copy between them, three ways. (a) `PURLIN_DEV_RELOAD` unset, the copy's `SERVER_INFO` rewritten to version `9.9.9-reloaded`: stderr carries neither `reloaded` nor `reload failed`, both responses carry `result.protocolVersion` `2024-11-05`, and the second `serverInfo.version` still equals the first, so no reload ran. (b) `PURLIN_DEV_RELOAD=1`, the line `def broken(:` appended to the copy: stderr carries `Purlin MCP: reload failed`, `Traceback (most recent call last):` and `SyntaxError`, and the second response is still the old module's, with `id` 2, `protocolVersion` `2024-11-05` and the first response's `serverInfo.version`. (c) `PURLIN_DEV_RELOAD=1`, the `9.9.9-reloaded` rewrite: stderr carries `Purlin MCP: reloaded` and the second response's `serverInfo.version` is `9.9.9-reloaded` while the first is not @integration
