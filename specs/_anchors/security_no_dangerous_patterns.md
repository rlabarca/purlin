# Anchor: security_no_dangerous_patterns

> Source: ./dev/external-refs/security-policy.git
> Note: the Source is a local bare repo that this checkout creates with `bash dev/setup-external-refs.sh`. Until that script has run, the source is unreachable and the status line says so; the script is safe to re-run and prints the SHA that belongs on the Pinned line.
> Path: security_policy.md
> Pinned: d1e2816ba07717d11542be09a64068ccf2f73038
> Scope: scripts/**/*.py, scripts/**/*.sh, scripts/**/*.js, scripts/**/*.ts, scripts/**/*.php, scripts/**/*.cs
> Description: Enforces the absence of dangerous code patterns across all executable Purlin framework code. The codebase is currently clean — this anchor exists to prove and maintain that state. Any feature requiring this anchor inherits these constraints.

## Rules

- RULE-1: FORBIDDEN — No dynamic-code or command-string execution anywhere in `scripts/`, in the form each language spells it: `eval()` and `exec()` in Python; `eval` and backtick command substitution in shell; `eval()`, `new Function()`, `execSync()` and `child_process.exec()` in JS/TS; `eval()`, `exec()`, `shell_exec()`, `system()`, `passthru()` and backticks in PHP; `Process.Start()` given a command string in C#
- RULE-2: FORBIDDEN — No `subprocess` calls with `shell=True` in scripts/
- RULE-3: FORBIDDEN — No `os.system()` calls in scripts/
- RULE-4: FORBIDDEN — No hardcoded credential assignments (password/secret/api_key/token literals) in scripts/
- RULE-5: Every subprocess launch passes an argument vector, never a command string: Python `subprocess.*` with a list, PHP `proc_open` with an array, JS/TS `spawn`/`execFile` with an args array, C# `ProcessStartInfo.ArgumentList`
- RULE-6: No repository-supplied or tool-supplied string reaches git in option position: `--end-of-options` precedes every revision argument, `--` precedes every path argument, and a `> Source:` value that begins with `-` or names an `ext::` or `fd::` transport is rejected before any subprocess starts

## Proof

- PROOF-1 (RULE-1): For every file under `scripts/` with extension `.py`, `.sh`, `.js`, `.ts`, `.php` or `.cs`, drop whole-line comments and search the language's pattern set (Python `eval(`/`exec(`; shell `eval ` and backtick substitution; JS/TS `eval(`, `new Function(`, `execSync(`, `child_process.exec(`; PHP `eval(`, `exec(`, `shell_exec(`, `system(`, `passthru(`, backticks; C# `Process.Start("`); verify zero matches, naming the file and the pattern on failure. Only whole-line comments are dropped, so a match on a line that also carries code still fails
- PROOF-2 (RULE-2): Over the same six-extension file list, search each language's opt-in to a shell (`shell\s*=\s*True` in `.py`, `shell\s*:\s*true` in `.js`/`.ts`, `UseShellExecute\s*=\s*true` in `.cs`); verify zero matches, naming the file on failure
- PROOF-3 (RULE-3): Over the same six-extension file list, search the builtins that hand a whole command line to the OS shell (`os\.system\s*\(` in `.py`, `system\s*\(` and `passthru\s*\(` in `.php`); verify zero matches, naming the file on failure
- PROOF-4 (RULE-4): Over the same six-extension file list, excluding files whose name starts with `test_`, drop whole-line comments and search `(password|secret|api_key|token)\s*=\s*["'][^"']+["']` case-insensitively; verify zero matches, naming the file and the matched names on failure
- PROOF-5 (RULE-5): Over the same six-extension file list, verify every launch site passes a container rather than a string: in `.py` the first argument of `subprocess.run/call/check_call/check_output` starts with `[` or `*`; in `.php` the first argument of `proc_open(` starts with `[`; in `.js`/`.ts` the second argument of `spawn`/`spawnSync`/`execFile`/`execFileSync` starts with `[`; in `.cs` no `.Arguments = "..."` assignment exists. Verify zero violations, naming the file and the offending call @integration
- PROOF-6 (RULE-6): In a temp project holding two anchors, one whose `> Source:` is `--upload-pack=/bin/echo` and one whose Source is a real local bare repo, call `sync_status` with `subprocess.run` wrapped by a recording spy. Verify no captured argv carries `--upload-pack=/bin/echo` in option position (before any `--end-of-options` or `--`), that at least one `git ls-remote` argv was captured and every such argv has `--end-of-options` immediately before the url, and that the status text carries `(source rejected: begins with "-")` for the rejected anchor @integration
