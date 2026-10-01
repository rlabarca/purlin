# Anchor: security_no_dangerous_patterns

> Type: security
> Description: The dangerous patterns no executable file under `scripts/` may carry, in
>   the form each language `scripts/` holds, Python, shell and JavaScript, spells them,
>   plus the argv hardening that keeps a repository-supplied string out of git's option
>   position. Its tests read every file under `scripts/`, where all of Purlin's executable
>   code lives.
> Highest-Rule: 8
> Highest-Proof: 91

## Rules

- RULE-1: No file under `scripts/` executes a string as code or as a command line, in the form its language spells it: `eval(` and `exec(` in Python; `eval` and backtick substitution in shell; `eval(`, `new Function(`, `execSync(` and `child_process.exec(` in JavaScript
- RULE-2: No file under `scripts/` writes the request that opts a subprocess into a shell, not even in a comment: no `shell=True` in Python, no `shell: true` in JavaScript
- RULE-3: No file under `scripts/` calls the builtin that hands a whole command line to the operating system shell: no `os.system(` in Python
- RULE-4: No file under `scripts/` assigns a credential literal: no quoted value of one character or more is given to a name containing `password`, `secret`, `api_key` or `token`, in any casing, with `=`, or with `:` as a field in JavaScript, outside a file whose name begins `test_`
- RULE-5: Every subprocess launch passes an argument vector rather than a command string: a list in Python, and an args array for JavaScript `spawn` and `execFile`
- RULE-6: No repository-supplied string reaches git in option position: `--end-of-options` precedes an anchor's `> Source:` address and every revision argument that comes from outside Purlin, such as a commit read from git or from a spec, and the fixed word `HEAD`, which Purlin writes itself, needs none
- RULE-7: `--` precedes every path argument handed to git
- RULE-8: A `> Source:` value that begins with `-` or names an `ext::` or `fd::` transport is refused before any subprocess starts, with the status line saying which

## Proof

- PROOF-1 (RULE-1): Every file under `scripts/` ending `.py`, `.sh` or `.js` is read with its comment-only lines set aside and checked for each form this rule names for its file type, as the proofs below find them; 0 are found
- PROOF-14 (RULE-1): A planted `.py` file holding `x = eval(src)` is found, and the finding names its file and the form `eval(`
- PROOF-22 (RULE-1): A planted `.py` file whose one line is the comment `# eval(src) is never called` is not counted
- PROOF-2 (RULE-2): Every file under `scripts/` ending `.py` or `.js` is read whole, comments included, and checked for the request for a shell this rule names for its file type, as the proofs below find it; 0 are found
- PROOF-24 (RULE-2): A planted `.py` file holding `subprocess.run(argv, shell=True)` is found, and the finding names its file and the form `shell=True`
- PROOF-28 (RULE-2): A planted `.py` file holding `subprocess.run(argv, shell=False)`, which turns the shell off, is not counted
- PROOF-3 (RULE-3): Every file under `scripts/` ending `.py` is read with its comment-only lines set aside and checked for `os.system(`, with or without a space before the `(`; 0 are found
- PROOF-29 (RULE-3): A planted `.py` file holding `os.system(cmd)` is found, and the finding names its file and the form `os.system(`
- PROOF-31 (RULE-3): A planted `.py` file whose one line is the comment `# os.system(cmd) is never called` is not counted
- PROOF-4 (RULE-4): Every file under `scripts/` ending `.py`, `.sh` or `.js`, other than one whose name begins `test_`, is read with its comment-only lines set aside and checked for a quoted value given to a credential name, as the proofs below find one; 0 are found
- PROOF-7 (RULE-4): A planted `.py` file holding `API_KEY = "abc"` is found, and the finding names its file and the name that matched, `API_KEY`
- PROOF-34 (RULE-4): A planted file named `test_a.py` holding `password = "x"` is not counted
- PROOF-5 (RULE-5): Every file under `scripts/` ending `.py` or `.js` is read with its comment-only lines set aside and checked for a process launch handed a command string, as the proofs below find one; 0 are found
- PROOF-35 (RULE-5): A planted `.py` file holding `subprocess.run("git status")` is found, and the finding names its file
- PROOF-36 (RULE-5): A planted `.py` file holding `subprocess.run(["git", "status"])` is not counted
- PROOF-9 (RULE-6): A project holds an anchor whose `> Source:` is a local repository holding one commit, and its status is read. `git ls-remote` is run on that repository at least once, and each time `--end-of-options` stands immediately before the repository's path
- PROOF-10 (RULE-6): A project on a branch whose two commits change a spec has its drift read. Drift hands git a commit in a `rev-list`, a `diff` and a `show`, and every git command carrying a commit, a range or a `<commit>:<path>` carries `--end-of-options` immediately before the first; the fixed word `HEAD` alone is not held to it
- PROOF-11 (RULE-7): A project on a branch whose two commits change a spec has its drift read. At least one git command carries a path, `specs/` or a file under it, and each that does carries `--` immediately before its first path
- PROOF-6 (RULE-8): A project holds one anchor, `evil_policy`, whose `> Source:` is `--upload-pack=/bin/echo /tmp/policy.git`, and its status is read. The status carries the line `evil_policy: (source rejected: begins with "-")`, and no command started while it is read carries the value
- PROOF-47 (RULE-8): A project holds one anchor, `ext_policy`, whose `> Source:` is `ext::sh -c "touch /tmp/purlin-pwned" /tmp/policy.git`, and its status is read. The status carries the line `ext_policy: (source rejected: names an ext:: transport)`, and no command started while it is read carries the value
- PROOF-48 (RULE-8): A project holds one anchor, `fd_policy`, whose `> Source:` is `fd::7/policy.git`, and its status is read. The status carries the line `fd_policy: (source rejected: names an fd:: transport)`, and no command started while it is read carries the value
