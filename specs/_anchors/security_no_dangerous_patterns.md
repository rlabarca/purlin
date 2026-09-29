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

- RULE-1: No file under `scripts/` executes a string as code or as a command line, in the form its language spells it: `eval(` and `exec(` in Python; `eval` and backtick substitution in shell; `eval(`, `new Function(`, `execSync(` and `child_process.exec(` in JS and TS; `eval(`, `exec(`, `shell_exec(` and backticks in PHP
- RULE-2: No file under `scripts/` writes the request that opts a subprocess into a shell, not even in a comment: no `shell=True` in Python, no `shell: true` in JS or TS, no `UseShellExecute = true` in C#
- RULE-3: No file under `scripts/` calls the builtin that hands a whole command line to the operating system shell: no `os.system(` in Python, no `system(` or `passthru(` in PHP
- RULE-4: No file under `scripts/` assigns a credential literal: no quoted value of one character or more is given to a name containing `password`, `secret`, `api_key` or `token`, in any casing, with `=`, or with `:` as a field in JS and TS, outside a file whose name begins `test_`
- RULE-5: Every subprocess launch passes an argument vector rather than a command string: a list in Python, an array in PHP `proc_open`, an args array for JS and TS `spawn` and `execFile`, and `ArgumentList` rather than an `Arguments` string in C#
- RULE-6: No repository-supplied string reaches git in option position: `--end-of-options` precedes an anchor's `> Source:` address and every revision argument that comes from outside Purlin, such as a commit read from git or from a spec, and the fixed word `HEAD`, which Purlin writes itself, needs none
- RULE-7: `--` precedes every path argument handed to git
- RULE-8: A `> Source:` value that begins with `-` or names an `ext::` or `fd::` transport is refused before any subprocess starts, with the status line saying which

## Proof

- PROOF-1 (RULE-1): Every file under `scripts/` ending `.py`, `.sh`, `.js`, `.ts` or `.php` is read with its comment-only lines set aside and checked for each form this rule names for its file type, as the proofs below find them; 0 are found
- PROOF-14 (RULE-1): A planted `.py` file holding `x = eval(src)` is found, and the finding names its file and the form `eval(`
- PROOF-49 (RULE-1): A planted `.py` file holding `exec (src)` is found, and the finding names its file and the form `exec(`
- PROOF-50 (RULE-1): A planted `.py` file holding `x = eval(src)  # only a comment follows` is found, and the finding names its file and the form `eval(`
- PROOF-15 (RULE-1): A planted `.sh` file holding `eval "$cmd"` is found, and the finding names its file and the form `eval`
- PROOF-51 (RULE-1): A planted `.sh` file holding `    eval "$cmd"`, indented, is found, and the finding names its file and the form `eval`
- PROOF-52 (RULE-1): A planted `.sh` file holding `if eval "$cmd"; then :; fi` is found, and the finding names its file and the form `eval`
- PROOF-53 (RULE-1): A planted `.sh` file holding `out=$(eval "$cmd")` is found, and the finding names its file and the form `eval`
- PROOF-54 (RULE-1): A planted `.sh` file holding `true && eval "$cmd"` is found, and the finding names its file and the form `eval`
- PROOF-16 (RULE-1): A planted `.sh` file holding `` out=`date` `` is found, and the finding names its file and the form `backticks`
- PROOF-17 (RULE-1): A planted `.js` file holding `eval(src);` is found, and the finding names its file and the form `eval(`
- PROOF-55 (RULE-1): A planted `.js` file holding `const f = new Function(src);` is found, and the finding names its file and the form `new Function(`
- PROOF-56 (RULE-1): A planted `.js` file holding `execSync(cmd);` is found, and the finding names its file and the form `execSync(`
- PROOF-57 (RULE-1): A planted `.js` file holding `child_process.exec(cmd);` is found, and the finding names its file and the form `child_process.exec(`
- PROOF-58 (RULE-1): A planted `.js` file holding `eval(src); // only a comment follows` is found, and the finding names its file and the form `eval(`
- PROOF-18 (RULE-1): A planted `.ts` file holding `eval(src);` is found, though `scripts/` holds no `.ts` file today, and the finding names its file and the form `eval(`
- PROOF-59 (RULE-1): A planted `.ts` file holding `const f = new Function(src);` is found, though `scripts/` holds no `.ts` file today, and the finding names its file and the form `new Function(`
- PROOF-60 (RULE-1): A planted `.ts` file holding `execSync(cmd);` is found, though `scripts/` holds no `.ts` file today, and the finding names its file and the form `execSync(`
- PROOF-61 (RULE-1): A planted `.ts` file holding `child_process.exec(cmd);` is found, though `scripts/` holds no `.ts` file today, and the finding names its file and the form `child_process.exec(`
- PROOF-19 (RULE-1): A planted `.php` file holding `eval($src);` is found, and the finding names its file and the form `eval(`
- PROOF-62 (RULE-1): A planted `.php` file holding `exec($cmd);` is found, and the finding names its file and the form `exec(`
- PROOF-63 (RULE-1): A planted `.php` file holding `shell_exec($cmd);` is found, and the finding names its file and the form `shell_exec(`
- PROOF-64 (RULE-1): A planted `.php` file holding `` $o = `ls`; `` is found, and the finding names its file and the form `backticks`
- PROOF-22 (RULE-1): A planted `.py` file whose one line is the comment `# eval(src) is never called` is not counted
- PROOF-65 (RULE-1): A planted `.sh` file whose one line is the comment `  # eval "$cmd" is never run` is not counted
- PROOF-66 (RULE-1): A planted `.js` file whose one line is the comment `// eval(src) is never called` is not counted
- PROOF-23 (RULE-1): A planted `.py` file holding `x = evaluate(src)`, a word that only contains a form, is not counted
- PROOF-67 (RULE-1): A planted `.sh` file holding `run_evaluation "$x"`, a word that only contains a form, is not counted
- PROOF-68 (RULE-1): A planted `.js` file holding `const x = evaluate(src);`, a word that only contains a form, is not counted
- PROOF-2 (RULE-2): Every file under `scripts/` ending `.py`, `.js`, `.ts` or `.cs` is read whole, comments included, and checked for the request for a shell this rule names for its file type, as the proofs below find it; 0 are found
- PROOF-24 (RULE-2): A planted `.py` file holding `subprocess.run(argv, shell=True)` is found, and the finding names its file and the form `shell=True`
- PROOF-69 (RULE-2): A planted `.py` file holding `subprocess.run(argv, shell = True)` is found, and the finding names its file and the form `shell=True`
- PROOF-25 (RULE-2): A planted `.py` file whose one line is the comment `# subprocess.run(argv, shell=True)` is found, and the finding names its file and the form `shell=True`
- PROOF-26 (RULE-2): A planted `.js` file holding `spawn("ls", [], { shell: true });` is found, and the finding names its file and the form `shell: true`
- PROOF-70 (RULE-2): A planted `.ts` file holding `spawn("ls", [], { shell :true });` is found, and the finding names its file and the form `shell: true`
- PROOF-27 (RULE-2): A planted `.cs` file holding `psi.UseShellExecute = true;` is found, and the finding names its file and the form `UseShellExecute = true`
- PROOF-71 (RULE-2): A planted `.cs` file holding `psi.UseShellExecute=true;` is found, and the finding names its file and the form `UseShellExecute = true`
- PROOF-28 (RULE-2): A planted `.py` file holding `subprocess.run(argv, shell=False)`, which turns the shell off, is not counted
- PROOF-72 (RULE-2): A planted `.js` file holding `spawn("ls", [], { shell: false });`, which turns the shell off, is not counted
- PROOF-73 (RULE-2): A planted `.cs` file holding `psi.UseShellExecute = false;`, which turns the shell off, is not counted
- PROOF-3 (RULE-3): Every file under `scripts/` ending `.py` or `.php` is read with its comment-only lines set aside and checked for `os.system(` in a `.py` file and for `system(` or `passthru(` in a `.php` file, with or without a space before the `(`; 0 are found
- PROOF-29 (RULE-3): A planted `.py` file holding `os.system(cmd)` is found, and the finding names its file and the form `os.system(`
- PROOF-74 (RULE-3): A planted `.py` file holding `os.system (cmd)` is found, and the finding names its file and the form `os.system(`
- PROOF-30 (RULE-3): A planted `.php` file holding `system($cmd);` is found, though `scripts/` holds no `.php` file today, and the finding names its file and the form `system(`
- PROOF-75 (RULE-3): A planted `.php` file holding `passthru ($cmd);` is found, and the finding names its file and the form `passthru(`
- PROOF-31 (RULE-3): A planted `.py` file whose one line is the comment `# os.system(cmd) is never called` is not counted
- PROOF-76 (RULE-3): A planted `.php` file whose one mention is the comment line `// system($cmd) is never called` is not counted
- PROOF-4 (RULE-4): Every file under `scripts/` ending `.py`, `.sh`, `.js`, `.ts`, `.php` or `.cs`, other than one whose name begins `test_`, is read with its comment-only lines set aside and checked for a quoted value given to a credential name, as the proofs below find one; 0 are found
- PROOF-7 (RULE-4): A planted `.py` file holding `API_KEY = "abc"` is found, and the finding names its file and the name that matched, `API_KEY`
- PROOF-77 (RULE-4): A planted `.py` file holding `db_password='x'` is found, and the finding names its file and the name that matched, `db_password`
- PROOF-78 (RULE-4): A planted `.py` file holding `TOKEN_NAME = "abc"` is found, and the finding names its file and the name that matched, `TOKEN_NAME`
- PROOF-79 (RULE-4): A planted `.sh` file holding `GITHUB_TOKEN="abc"` is found, and the finding names its file and the name that matched, `GITHUB_TOKEN`
- PROOF-32 (RULE-4): A planted `.js` file holding `{ password: "x" }` is found, and the finding names its file and the name that matched, `password`
- PROOF-80 (RULE-4): A planted `.ts` file holding `{ Token : "abc" }` is found, and the finding names its file and the name that matched, `Token`
- PROOF-8 (RULE-4): A planted `.py` file holding `API_KEY = ""`, an empty value, is not counted
- PROOF-81 (RULE-4): A planted `.py` file holding `row = {"password": ""}`, an empty value, is not counted
- PROOF-82 (RULE-4): A planted `.js` file holding `{ password: "" }`, an empty value, is not counted
- PROOF-33 (RULE-4): A planted `.py` file holding the comparison `if token == "x":` is not counted
- PROOF-34 (RULE-4): A planted file named `test_a.py` holding `password = "x"` is not counted
- PROOF-5 (RULE-5): Every file under `scripts/` ending `.py`, `.php`, `.js`, `.ts` or `.cs` is read with its comment-only lines set aside and checked for a process launch handed a command string, as the proofs below find one; 0 are found
- PROOF-35 (RULE-5): A planted `.py` file holding `subprocess.run("git status")` is found, and the finding names its file
- PROOF-83 (RULE-5): A planted `.py` file holding `subprocess.run(cmd)`, whose first argument opens with neither `[` nor `*`, is found, and the finding names its file
- PROOF-36 (RULE-5): A planted `.py` file holding `subprocess.run(["git", "status"])` is not counted
- PROOF-84 (RULE-5): A planted `.py` file holding `subprocess.run(*argv)` is not counted
- PROOF-37 (RULE-5): A planted `.py` file holding `subprocess.Popen("git status")` is found, and the finding names its file
- PROOF-85 (RULE-5): A planted `.py` file holding `subprocess.Popen(f"git {verb}")` is found, and the finding names its file
- PROOF-38 (RULE-5): A planted `.py` file holding `subprocess.Popen(command, cwd=root)` on its third line, handed a name and not a list written in place, is found, and the finding names its file and line 3
- PROOF-86 (RULE-5): A planted `.py` file holding `subprocess.Popen(*argv)` on its third line, handed no list written in place, is found, and the finding names its file and line 3
- PROOF-87 (RULE-5): A planted `.py` file holding `subprocess.Popen([*command], cwd=root)`, a list written in place, is not counted
- PROOF-39 (RULE-5): A planted `.py` file holding `run("git status")` after `from subprocess import run` is found, and the finding names its file
- PROOF-88 (RULE-5): A planted `.py` file holding `co("git status")` after `from subprocess import check_output as co, call` is found, and the finding names its file
- PROOF-89 (RULE-5): A planted `.py` file holding `Popen("git status")` after `from subprocess import Popen` is found, and the finding names its file
- PROOF-40 (RULE-5): A planted `.py` file holding `run(["git", "status"])` after `from subprocess import run` is not counted
- PROOF-41 (RULE-5): A planted `.php` file holding `proc_open("ls -la", $spec, $pipes);` is found, and the finding names its file
- PROOF-42 (RULE-5): A planted `.php` file holding `proc_open(["ls", "-la"], $spec, $pipes);` is not counted
- PROOF-43 (RULE-5): A planted `.js` file holding `spawn("ls", "-la");`, whose second argument does not open with `[`, is found, and the finding names its file
- PROOF-90 (RULE-5): A planted `.js` file holding `spawn("ls -la");`, with no second argument, is found, and the finding names its file
- PROOF-91 (RULE-5): A planted `.ts` file holding `execFileSync(cmd);`, with no second argument, is found, and the finding names its file
- PROOF-44 (RULE-5): A planted `.js` file holding `spawn("ls", ["-la"]);` is not counted
- PROOF-45 (RULE-5): A planted `.cs` file holding `psi.Arguments = "status --short";` is found, and the finding names its file
- PROOF-46 (RULE-5): A planted `.cs` file holding `psi.ArgumentList.Add("status");` is not counted
- PROOF-6 (RULE-8): A project holds one anchor, `evil_policy`, whose `> Source:` is `--upload-pack=/bin/echo /tmp/policy.git`, and its status is read. The status carries the line `evil_policy: (source rejected: begins with "-")`, and no command started while it is read carries the value
- PROOF-47 (RULE-8): A project holds one anchor, `ext_policy`, whose `> Source:` is `ext::sh -c "touch /tmp/purlin-pwned" /tmp/policy.git`, and its status is read. The status carries the line `ext_policy: (source rejected: names an ext:: transport)`, and no command started while it is read carries the value
- PROOF-48 (RULE-8): A project holds one anchor, `fd_policy`, whose `> Source:` is `fd::7/policy.git`, and its status is read. The status carries the line `fd_policy: (source rejected: names an fd:: transport)`, and no command started while it is read carries the value
- PROOF-9 (RULE-6): A project holds an anchor whose `> Source:` is a local repository holding one commit, and its status is read. `git ls-remote` is run on that repository at least once, and each time `--end-of-options` stands immediately before the repository's path
- PROOF-10 (RULE-6): A project on a branch whose two commits change a spec has its drift read. Drift hands git a commit in a `rev-list`, a `diff` and a `show`, and every git command carrying a commit, a range or a `<commit>:<path>` carries `--end-of-options` immediately before the first; the fixed word `HEAD` alone is not held to it
- PROOF-11 (RULE-7): A project on a branch whose two commits change a spec has its drift read. At least one git command carries a path, `specs/` or a file under it, and each that does carries `--` immediately before its first path
- PROOF-12 (RULE-6): A project on a branch whose two commits change a spec has its drift read since `2000-01-01`. Git is handed the commit before the first one in that range as `<commit>^`, and every git command carrying a commit carries `--end-of-options` immediately before the first
- PROOF-13 (RULE-6): A project on a branch whose two commits change a spec has its drift read over its last 1 commit. Git is handed the commit the range starts from in a `diff`, and every git command carrying a commit carries `--end-of-options` immediately before the first
