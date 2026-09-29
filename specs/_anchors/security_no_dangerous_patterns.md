# Anchor: security_no_dangerous_patterns

> Type: security
> Global: true
> Description: The dangerous patterns no executable file under `scripts/` may carry, in
>   the form each of the six file types the scope names spells them, plus the argv
>   hardening that keeps a repository-supplied string out of git's option position. The
>   scope names file types `scripts/` does not hold today, so a file in one of them is
>   watched from the day it arrives. The anchor is global: every feature's code lives
>   under `scripts/`, so every feature counts these rules.
> Scope: scripts/**/*.py, scripts/**/*.sh, scripts/**/*.js, scripts/**/*.ts, scripts/**/*.php, scripts/**/*.cs

## Rules

- RULE-1: No file under `scripts/` executes a string as code or as a command line, in the form its language spells it: `eval(` and `exec(` in Python; `eval` and backtick substitution in shell; `eval(`, `new Function(`, `execSync(` and `child_process.exec(` in JS and TS; `eval(`, `exec(`, `shell_exec(`, `system(`, `passthru(` and backticks in PHP; `Process.Start(` given a command string in C#
- RULE-2: No file under `scripts/` writes the request that opts a subprocess into a shell, not even in a comment: no `shell=True` in Python, no `shell: true` in JS or TS, no `UseShellExecute = true` in C#
- RULE-3: No file under `scripts/` calls the builtin that hands a whole command line to the operating system shell: no `os.system(` in Python, no `system(` or `passthru(` in PHP
- RULE-4: No file under `scripts/` assigns a credential literal: no quoted value of one character or more is given to a name containing `password`, `secret`, `api_key` or `token`, in any casing, with `=`, or with `:` as a field in JS and TS, outside a file whose name begins `test_`
- RULE-5: Every subprocess launch passes an argument vector rather than a command string: a list in Python, an array in PHP `proc_open`, an args array for JS and TS `spawn` and `execFile`, and `ArgumentList` rather than an `Arguments` string in C#
- RULE-6: No repository-supplied string reaches git in option position: `--end-of-options` precedes an anchor's `> Source:` address and every revision argument that comes from outside Purlin, such as a commit read from git or from a spec, and the fixed word `HEAD`, which Purlin writes itself, needs none; `--` precedes every path argument; and a `> Source:` value that begins with `-` or names an `ext::` or `fd::` transport is refused before any subprocess starts, with the status line saying which

## Proof

- PROOF-1 (RULE-1): Every file under `scripts/` ending `.py`, `.sh`, `.js`, `.ts`, `.php` or `.cs` is read with its comment-only lines set aside and checked for each form this rule names for its file type, as the proofs below find them; 0 are found
- PROOF-14 (RULE-1): Planted `.py` files holding `x = eval(src)`, `exec (src)` and `x = eval(src)  # only a comment follows`, one per file, are each found, and each finding names its file and the form, `eval(` or `exec(`
- PROOF-15 (RULE-1): Planted `.sh` files holding `eval "$cmd"`, `    eval "$cmd"`, `if eval "$cmd"; then :; fi`, `out=$(eval "$cmd")` and `true && eval "$cmd"`, one per file, are each found, and each finding names its file and the form `eval`
- PROOF-16 (RULE-1): A planted `.sh` file holding `` out=`date` `` is found, and the finding names its file and the form `backticks`
- PROOF-17 (RULE-1): Planted `.js` files holding `eval(src);`, `const f = new Function(src);`, `execSync(cmd);`, `child_process.exec(cmd);` and `eval(src); // only a comment follows`, one per file, are each found, and each finding names its file and the form it holds
- PROOF-18 (RULE-1): Planted `.ts` files holding `eval(src);`, `const f = new Function(src);`, `execSync(cmd);` and `child_process.exec(cmd);`, one per file, are each found, though `scripts/` holds no `.ts` file today, and each finding names its file and the form it holds
- PROOF-19 (RULE-1): Planted `.php` files holding `eval($src);`, `exec($cmd);`, `shell_exec($cmd);`, `system($cmd);`, `passthru($cmd);` and `` $o = `ls`; ``, one per file, are each found, and each finding names its file and the form it holds, the last as `backticks`
- PROOF-20 (RULE-1): A planted `.cs` file holding `Process.Start("cmd.exe /c dir");` is found, and the finding names its file and the form `Process.Start("`
- PROOF-21 (RULE-1): A planted `.cs` file holding `Process.Start(info);`, which is handed a name and not a quoted string, is not counted
- PROOF-22 (RULE-1): Planted files whose one line is a comment naming a form, `# eval(src) is never called` in `.py`, `  # eval "$cmd" is never run` in `.sh` and `// eval(src) is never called` in `.js`, are not counted
- PROOF-23 (RULE-1): Planted files holding a word that only contains a form, `x = evaluate(src)` in `.py`, `run_evaluation "$x"` in `.sh` and `const x = evaluate(src);` in `.js`, are not counted
- PROOF-2 (RULE-2): Every file under `scripts/` ending `.py`, `.js`, `.ts` or `.cs` is read whole, comments included, and checked for the request for a shell this rule names for its file type, as the proofs below find it; 0 are found
- PROOF-24 (RULE-2): Planted `.py` files holding `subprocess.run(argv, shell=True)` and `subprocess.run(argv, shell = True)` are each found, and each finding names its file and the form `shell=True`
- PROOF-25 (RULE-2): A planted `.py` file whose one line is the comment `# subprocess.run(argv, shell=True)` is found, and the finding names its file and the form `shell=True`
- PROOF-26 (RULE-2): A planted `.js` file holding `spawn("ls", [], { shell: true });` and a planted `.ts` file holding `spawn("ls", [], { shell :true });` are each found, and each finding names its file and the form `shell: true`
- PROOF-27 (RULE-2): Planted `.cs` files holding `psi.UseShellExecute = true;` and `psi.UseShellExecute=true;` are each found, and each finding names its file and the form `UseShellExecute = true`
- PROOF-28 (RULE-2): Planted files that turn the shell off, `shell=False` in `.py`, `{ shell: false }` in `.js` and `psi.UseShellExecute = false;` in `.cs`, one per file, are not counted
- PROOF-3 (RULE-3): Every file under `scripts/` ending `.py` or `.php` is read with its comment-only lines set aside and checked for `os.system(` in a `.py` file and for `system(` or `passthru(` in a `.php` file, with or without a space before the `(`; 0 are found
- PROOF-29 (RULE-3): Planted `.py` files holding `os.system(cmd)` and `os.system (cmd)` are each found, and each finding names its file and the form `os.system(`
- PROOF-30 (RULE-3): Planted `.php` files holding `system($cmd);` and `passthru ($cmd);` are each found, though `scripts/` holds no `.php` file today, and each finding names its file and the form, `system(` or `passthru(`
- PROOF-31 (RULE-3): A planted `.py` file whose one line is the comment `# os.system(cmd) is never called`, and a `.php` file whose one mention is the comment line `// system($cmd) is never called`, are not counted
- PROOF-4 (RULE-4): Every file under `scripts/` ending `.py`, `.sh`, `.js`, `.ts`, `.php` or `.cs`, other than one whose name begins `test_`, is read with its comment-only lines set aside and checked for a quoted value given to a credential name, as the proofs below find one; 0 are found
- PROOF-7 (RULE-4): Planted files holding `API_KEY = "abc"`, `db_password='x'` and `TOKEN_NAME = "abc"` in `.py` and `GITHUB_TOKEN="abc"` in `.sh`, one per file, are each found, and each finding names its file and the name that matched
- PROOF-32 (RULE-4): Planted files holding `{ password: "x" }` in `.js` and `{ Token : "abc" }` in `.ts` are each found, and each finding names its file and the name that matched, `password` and `Token`
- PROOF-8 (RULE-4): Planted files giving a credential name an empty value, `API_KEY = ""` and `row = {"password": ""}` in `.py` and `{ password: "" }` in `.js`, one per file, are not counted
- PROOF-33 (RULE-4): A planted `.py` file holding the comparison `if token == "x":` is not counted
- PROOF-34 (RULE-4): A planted file named `test_a.py` holding `password = "x"` is not counted
- PROOF-5 (RULE-5): Every file under `scripts/` ending `.py`, `.php`, `.js`, `.ts` or `.cs` is read with its comment-only lines set aside and checked for a process launch handed a command string, as the proofs below find one; 0 are found
- PROOF-35 (RULE-5): Planted `.py` files holding `subprocess.run("git status")` and `subprocess.run(cmd)`, whose first argument opens with neither `[` nor `*`, are each found, and each finding names its file
- PROOF-36 (RULE-5): Planted `.py` files holding `subprocess.run(["git", "status"])` and `subprocess.run(*argv)` are not counted
- PROOF-37 (RULE-5): Planted `.py` files holding `subprocess.Popen("git status")` and `subprocess.Popen(f"git {verb}")` are each found, and each finding names its file
- PROOF-38 (RULE-5): A planted `.py` file holding `subprocess.Popen(command, cwd=root)`, whose first argument is a name and not a quoted string, is not counted
- PROOF-39 (RULE-5): Planted `.py` files holding `run("git status")` after `from subprocess import run`, `co("git status")` after `from subprocess import check_output as co, call`, and `Popen("git status")` after `from subprocess import Popen` are each found, and each finding names its file
- PROOF-40 (RULE-5): A planted `.py` file holding `run(["git", "status"])` after `from subprocess import run` is not counted
- PROOF-41 (RULE-5): A planted `.php` file holding `proc_open("ls -la", $spec, $pipes);` is found, and the finding names its file
- PROOF-42 (RULE-5): A planted `.php` file holding `proc_open(["ls", "-la"], $spec, $pipes);` is not counted
- PROOF-43 (RULE-5): Planted files holding `spawn("ls", "-la");` and `spawn("ls -la");` in `.js` and `execFileSync(cmd);` in `.ts`, none with a second argument opening with `[`, are each found, and each finding names its file
- PROOF-44 (RULE-5): A planted `.js` file holding `spawn("ls", ["-la"]);` is not counted
- PROOF-45 (RULE-5): A planted `.cs` file holding `psi.Arguments = "status --short";` is found, and the finding names its file
- PROOF-46 (RULE-5): A planted `.cs` file holding `psi.ArgumentList.Add("status");` is not counted
- PROOF-6 (RULE-6): A project holds one anchor, `evil_policy`, whose `> Source:` is `--upload-pack=/bin/echo /tmp/policy.git`, and its status is read. The status carries the line `evil_policy: (source rejected: begins with "-")`, and no command started while it is read carries the value
- PROOF-47 (RULE-6): A project holds one anchor, `ext_policy`, whose `> Source:` is `ext::sh -c "touch /tmp/purlin-pwned" /tmp/policy.git`, and its status is read. The status carries the line `ext_policy: (source rejected: names an ext:: transport)`, and no command started while it is read carries the value
- PROOF-48 (RULE-6): A project holds one anchor, `fd_policy`, whose `> Source:` is `fd::7/policy.git`, and its status is read. The status carries the line `fd_policy: (source rejected: names an fd:: transport)`, and no command started while it is read carries the value
- PROOF-9 (RULE-6): A project holds an anchor whose `> Source:` is a local repository holding one commit, and its status is read. `git ls-remote` is run on that repository at least once, and each time `--end-of-options` stands immediately before the repository's path
- PROOF-10 (RULE-6): A project on a branch whose two commits change a spec has its drift read. Drift hands git a commit in a `rev-list`, a `diff` and a `show`, and every git command carrying a commit, a range or a `<commit>:<path>` carries `--end-of-options` immediately before the first; the fixed word `HEAD` alone is not held to it
- PROOF-11 (RULE-6): A project on a branch whose two commits change a spec has its drift read. At least one git command carries a path, `specs/` or a file under it, and each that does carries `--` immediately before its first path
- PROOF-12 (RULE-6): A project on a branch whose two commits change a spec has its drift read since `2000-01-01`. Git is handed the commit before the first one in that range as `<commit>^`, and every git command carrying a commit carries `--end-of-options` immediately before the first
- PROOF-13 (RULE-6): A project on a branch whose two commits change a spec has its drift read over its last 1 commit. Git is handed the commit the range starts from in a `diff`, and every git command carrying a commit carries `--end-of-options` immediately before the first
