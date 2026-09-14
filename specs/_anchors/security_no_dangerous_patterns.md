# Anchor: security_no_dangerous_patterns

> Source: ./dev/external-refs/security-policy.git
> Note: the Source is a local bare repository this checkout creates with `bash dev/setup-external-refs.sh`. Until that script has run the source is unreachable and the status line says so; the script is safe to re-run and prints the sha that belongs on the Pinned line.
> Path: security_policy.md
> Pinned: 379a046172a68c86d14935bfd2ffdf463af52fae
> Type: security
> Description: The dangerous patterns no executable file under `scripts/` may carry, in
>   the form each of the six file types the scope names spells them, plus the argv
>   hardening that keeps a repository-supplied string out of git's option position. PHP
>   ships no plugin in this release and the guard stays anyway, because a language the
>   check drops is a language the next file in it enters unwatched. The tree is clean
>   today; this anchor is what keeps it clean. A feature that requires this anchor
>   inherits every rule.
> Scope: scripts/**/*.py, scripts/**/*.sh, scripts/**/*.js, scripts/**/*.ts, scripts/**/*.php, scripts/**/*.cs

## Rules

- RULE-1: No file under `scripts/` executes a string as code or as a command line, in the form its language spells it: `eval(` and `exec(` in Python; `eval` and backtick substitution in shell; `eval(`, `new Function(`, `execSync(` and `child_process.exec(` in JS and TS; `eval(`, `exec(`, `shell_exec(`, `system(`, `passthru(` and backticks in PHP; `Process.Start(` given a command string in C# [risk: high] [origin: eng]
- RULE-2: No file under `scripts/` opts a subprocess into a shell: no `shell=True` in Python, no `shell: true` in JS or TS, no `UseShellExecute = true` in C# [risk: high] [origin: eng]
- RULE-3: No file under `scripts/` calls the builtin that hands a whole command line to the operating system shell: no `os.system(` in Python, no `system(` or `passthru(` in PHP [risk: high] [origin: eng]
- RULE-4: No file under `scripts/` assigns a credential literal: no quoted value assigned to a name containing `password`, `secret`, `api_key` or `token`, in any casing, outside a test file [risk: high] [origin: eng]
- RULE-5: Every subprocess launch passes an argument vector rather than a command string: a list in Python, an array in PHP `proc_open`, an args array for JS and TS `spawn` and `execFile`, and `ArgumentList` rather than an `Arguments` string in C# [risk: high] [origin: eng]
- RULE-6: No repository-supplied string reaches git in option position: `--end-of-options` precedes every revision argument, `--` precedes every path argument, and a `> Source:` value that begins with `-` or names an `ext::` or `fd::` transport is refused before any subprocess starts, with the status line saying which [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): For every file under `scripts/` ending `.py`, `.sh`, `.js`, `.ts`, `.php` or `.cs`, drop the lines that are nothing but a comment and search that language's pattern set; verify zero matches, naming the file and the pattern on failure. A line carrying both a comment and code is still searched, so a dangerous call hidden behind a trailing comment still fails
- PROOF-2 (RULE-2): Over the same file list, grep each language's opt-in to a shell (`shell\s*=\s*True`, `shell\s*:\s*true`, `UseShellExecute\s*=\s*true`); verify zero matches, naming the file on failure
- PROOF-3 (RULE-3): Over the same file list, grep `os\.system\s*\(` in Python and `system\s*\(` and `passthru\s*\(` in PHP; verify zero matches, naming the file on failure
- PROOF-4 (RULE-4): Over the same file list, skipping files whose name begins `test_` and dropping whole-line comments, grep `(password|secret|api_key|token)\s*=\s*["'][^"']+["']` without regard to case; verify zero matches, naming the file and what matched on failure
- PROOF-5 (RULE-5): Over the same file list, verify every launch site passes a container rather than a string: the first argument of Python `subprocess.run`, `call`, `check_call` and `check_output` begins `[` or `*`, the first argument of PHP `proc_open(` begins `[`, the second argument of JS and TS `spawn`, `spawnSync`, `execFile` and `execFileSync` begins `[`, and no C# file assigns a string to `.Arguments`; verify zero violations, naming the file and the offending call
- PROOF-6 (RULE-6): In a temporary project holding four anchors whose sources are `--upload-pack=/bin/echo`, an `ext::` command, `fd::7` and a real local bare repository, call `sync_status` with the subprocess runner wrapped by a recording spy. Verify none of the three refused values appears in any captured argument vector, so each was refused before a subprocess started; that at least one `git ls-remote` was captured and every one carries `--end-of-options` immediately before the bare repository url; that at least one captured git vector carries a path operand under `specs/` and every such vector carries `--` immediately before its first path operand; and that the status text names all three refusals @integration
