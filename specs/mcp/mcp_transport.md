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

## Proof

- PROOF-1 (RULE-1): Send an `initialize` request; verify `result.protocolVersion` equals `2024-11-05`, `result.serverInfo.name` equals `purlin`, and `result.capabilities` is present and equals `{"tools": {}}`, the tools capability a client needs to discover that this server serves tools @integration
- PROOF-2 (RULE-2): Send `tools/list`; verify the result holds exactly 3 tools whose sorted names are `drift`, `purlin_config`, `sync_status`, that those names equal the names declared in `scripts/mcp/manifest.json`, and that each tool carries a non-empty `description` plus an `inputSchema` of `type` `object` whose property names are `role` for `sync_status`, `action`, `key`, `value` for `purlin_config`, and `since`, `role` for `drift` @integration
- PROOF-3 (RULE-3): Send the notification `notifications/initialized` with no `id`; verify `handle_request` returns `None` rather than a response object, so there is nothing for the loop to write @integration
- PROOF-4 (RULE-4): Send invalid JSON; verify error code -32700 @integration
- PROOF-5 (RULE-5): Send unknown method; verify error code -32601 with method name @integration
- PROOF-6 (RULE-6): Send tools/call with unknown tool; verify error code -32601 with tool name @integration
- PROOF-7 (RULE-7): Run the server main loop on empty stdin; verify stderr carries the startup text `Purlin MCP server` and that stdout is the empty string @integration
