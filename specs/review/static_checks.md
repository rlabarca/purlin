# Feature: static_checks

> Description: The free structural checks on test bodies. The extension table
>   decides which of the five checkers reads a file: Python through the abstract
>   syntax tree, JavaScript and TypeScript through a brace-balancing reader,
>   shell through the marker lines, C# and SQL through the same driver as
>   JavaScript. Findings use one vocabulary and no other names: `tautology`,
>   `assert_true_literal`, `no_assertion`, `bare_except`, `logic_mirroring`,
>   `mock_of_target`. The whole-project sweep runs the same checks over every
>   executed backing of every proof, reads the runtime proof files, and writes
>   nothing.
> Scope: scripts/review/static_checks.py
> Stack: python/stdlib (ast, re, glob, json), fcntl on POSIX and msvcrt on Windows

## Rules

- RULE-1: A marked Python test whose assertion is a literal true is reported `assert_true_literal` [risk: high] [origin: eng]
- RULE-2: A marked Python test whose assertion cannot fail, comparing a result with `None`, a length at or above zero, or two constants, is reported `tautology` [risk: high] [origin: eng]
- RULE-3: A marked Python test with no assertion statement at all is reported `no_assertion` [risk: high] [origin: eng]
- RULE-4: A marked Python test that wraps the code under test in an except clause whose whole body is a pass is reported `bare_except` [risk: high] [origin: eng]
- RULE-5: A marked Python test whose expected value comes from the same call as the result is reported `logic_mirroring` [risk: high] [origin: eng]
- RULE-6: A marked Python test whose patch target names a word the rule text uses is reported `mock_of_target` [risk: high] [origin: eng]
- RULE-7: A marked Python test that asserts a literal value passes the structural checks, whatever a reader would still want to ask about it [risk: medium] [origin: eng]
- RULE-8: A shell proof recorded once with no test logic before it is reported `tautology`, and an if/else pair recording one proof both ways is one result judged by the condition above it [risk: high] [origin: eng]
- RULE-9: A JavaScript or TypeScript body asserting `expect(true).toBe(true)` is reported `tautology`, a body with no `expect(` call is reported `no_assertion`, and a body with a real assertion passes [risk: high] [origin: eng]
- RULE-10: The JavaScript reader bounds a test body by balancing braces, so a nested options object does not truncate it and an apostrophe inside a title does not drop the test [risk: high] [origin: eng]
- RULE-11: A C# body asserting `Assert.True(true)` is reported `tautology` and one with no assertion is reported `no_assertion`; xUnit, NUnit, MSTest, FluentAssertions and a Playwright matcher chain each count as an assertion, while a bare `Expect(x)` with no matcher does not [risk: high] [origin: eng]
- RULE-12: A C# test whose record names no file has its source resolved from the fully-qualified test name, preferring the file whose stem is the declaring type, skipping build output, and returning empty when the type is declared nowhere [risk: medium] [origin: eng]
- RULE-13: A SQL block whose first PASS producer is unconditional is reported `tautology`, while a predicate naming a column, a function or a subquery passes [risk: high] [origin: eng]
- RULE-14: A SQL block that runs no SELECT observes nothing and is reported `no_assertion`, and a block with no `-- Test:` line is named by its proof id [risk: high] [origin: eng]
- RULE-15: A SQL proof block runs from its marker to the next marker, so a block another feature owns never enters this feature's results [risk: medium] [origin: eng]
- RULE-16: Every result carries the proof id, the rule id, the test name, the status and the reason, whichever checker produced it [risk: medium] [origin: eng]
- RULE-17: The command exits 0 for any completed analysis however weak the test it read, and 2 only for a real error such as a file that is not on disk [risk: high] [origin: eng]
- RULE-18: Spec coverage counts a spec's rules and its proofs, a trailing tier tag is metadata rather than part of the description, and a spec with no rule counts zero of both [risk: low] [origin: eng]
- RULE-19: One proof id targeting two rules inside one record is reported `proof_id_collision`, whatever language wrote the record [risk: medium] [origin: eng]
- RULE-20: A proof naming a rule the spec does not declare is reported `proof_rule_orphan`, a rule an anchor owns is not, and with no spec named the check does not run at all [risk: medium] [origin: eng]
- RULE-21: One extension table decides which checker reads a file: an extension outside it reaches no checker and yields no extracted body, and the extractor set is that table less shell [risk: high] [origin: eng]
- RULE-22: The brace-body checkers are one-line wrappers over one driver, and each keeps the reason its own language's proofs assert [risk: medium] [origin: eng]
- RULE-23: The sweep grades every executed backing of every proof the project's specs declare [risk: high] [origin: eng]
- RULE-24: A backing the sweep cannot measure is reported `no_checker`, `missing_file` or `marker_not_found`, never as a defect [risk: high] [origin: eng]
- RULE-25: Across several backings of one proof a failure outranks an unmeasurable backing, which outranks a pass [risk: high] [origin: eng]
- RULE-26: The sweep opens nothing for writing, so the project it read is byte-identical afterwards [risk: high] [origin: eng]
- RULE-27: `--sweep` prints the sweep as JSON and exits 0, and over this repository no backing is unmeasurable for want of a checker [risk: medium] [origin: eng]
- RULE-28: Inside one run scope each file is read once and each Python file parsed once, however many features or proofs ask for it, and the answers match those taken outside one [risk: medium] [origin: eng]
- RULE-29: Outside a run scope nothing is memoized, so an edit to a test file is seen at once [risk: high] [origin: eng]
- RULE-30: A function's source is sliced from one line split that matches the standard library byte for byte [risk: high] [origin: eng]
- RULE-31: The test-source extractor returns a body for every extension the table names but shell, which has no body to return [risk: medium] [origin: eng]
- RULE-32: Every `--flag` the command dispatches on appears in its usage text, the usage advertises no flag the command never dispatches on, and the module docstring states the exit convention rather than contradicting it [risk: low] [origin: eng]
- RULE-33: A bad invocation prints every usage line on the error stream and exits 2, and `--help` prints them with both exit codes and exits 0 [risk: low] [origin: eng]
- RULE-34: An exclusive lock the module takes is held against a second process until it is released, and releasing it closes the handle [risk: high] [origin: eng]
- RULE-35: The module imports where there is no fcntl: the import sits under a try that catches an import error, both branches set the flag every lock helper reads, and the Windows lock branch is in the source [risk: high] [origin: eng]
- RULE-36: Every text file the module opens is opened as UTF-8, whatever the console codec is [risk: medium] [origin: eng]
- RULE-37: On Windows the exclusive lock is taken through msvcrt on one byte, and a second process cannot take it until it is released [risk: high] [origin: eng]
- RULE-38: The JavaScript reader skips a regex literal whole, so a `}`, a quote or a `/` inside its character class or behind a backslash never ends a test body, and skips a `}` inside a line or block comment the same way; a `/` that follows a value, or one whose literal would run past the end of its line, is read as division [risk: medium] [origin: eng]
- RULE-39: Without `--json` an analysis prints one line per proof, `pass <proof> <test name>` or `fail <proof> <check>: <reason>`, and `--sweep` prints one line of counts naming features, backings, pass, failing and unmeasurable, then one line per failing or unmeasurable backing [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Run the Python checker over a marked test whose body is `assert True`; verify exactly 1 result comes back, its status is `fail` and its check is `assert_true_literal` @integration
- PROOF-2 (RULE-2): Run the Python checker over a marked test asserting `result is not None`; verify its status is `fail` and its check is `tautology` @integration
- PROOF-3 (RULE-2): Run the Python checker over a marked test asserting `len(items) >= 0`; verify its status is `fail` and its check is `tautology` @integration
- PROOF-4 (RULE-3): Run the Python checker over a marked test that calls the code and only prints the result; verify its status is `fail` and its check is `no_assertion` @integration
- PROOF-5 (RULE-4): Run the Python checker over a marked test wrapping the call in `except Exception: pass`; verify its status is `fail` and its check is `bare_except` @integration
- PROOF-6 (RULE-4): Run the Python checker over a marked test wrapping the call in a bare `except: pass`; verify its status is `fail` and its check is `bare_except` @integration
- PROOF-7 (RULE-5): Run the Python checker over a marked test that computes both the expected value and the result with `hash_func`; verify its status is `fail` and its check is `logic_mirroring` @integration
- PROOF-8 (RULE-7): Run the Python checker over a marked test comparing `hash_func("secret")` with a literal digest; verify exactly 1 result comes back and its status is `pass` @integration
- PROOF-9 (RULE-6): Run the Python checker over a marked test patching `auth.bcrypt.checkpw` against a rule reading `Passwords hashed with bcrypt`; verify its status is `fail` and its check is `mock_of_target` @integration
- PROOF-10 (RULE-7): Run the Python checker over a marked test patching `email.send_notification` against that same rule; verify its status is `pass` @integration
- PROOF-11 (RULE-16): Run the command with `--json` over a file carrying one clean and one always-true marked test; verify 2 proofs come back and each names a proof id, a rule id, a test name, a status and a reason @integration
- PROOF-12 (RULE-17): Run the command over a file whose marked test asserts a real value; verify it exits 0 @integration
- PROOF-13 (RULE-17): Run the command with `--json` over a file whose marked test is `assert True`; verify it exits 0 and at least one proof carries the status `fail` @integration
- PROOF-14 (RULE-17): Run the command naming a test file that is not on disk; verify it exits 2, prints an error naming that file, and reports no analysis at all @integration
- PROOF-15 (RULE-18): Read the coverage of a spec carrying 3 rules and 3 proofs; verify both counts are 3 @integration
- PROOF-16 (RULE-18): Read the coverage of a spec whose two proof lines end in a tier tag; verify both counts are 2 and that each description reads `test` with the tag removed @integration
- PROOF-17 (RULE-18): Read the coverage of a spec whose rules section is empty; verify both counts are zero @integration
- PROOF-18 (RULE-8): Run the shell checker over a script recording one proof in both branches of an `if ... grep`; verify exactly 1 result comes back with status `pass` for `PROOF-1` @integration
- PROOF-19 (RULE-8): Run the shell checker over a script whose only line is a bare `purlin_proof ... pass`; verify its status is `fail` and its check is `tautology` @integration
- PROOF-20 (RULE-8): Run the shell checker over a script recording one proof in both branches of `if true`; verify the pair is merged into exactly 1 result rather than two @integration
- PROOF-21 (RULE-1): Run the Python checker over a marked test whose body is `assert True`; verify the check is named `assert_true_literal` and not the broader name @integration
- PROOF-22 (RULE-2): Run the Python checker over a marked test asserting `result is not None`; verify the check is named `tautology` and not the literal name @integration
- PROOF-23 (RULE-19): Write a record in which `PROOF-1` names `RULE-1` and `RULE-2`, for each of the five languages a plugin writes; verify exactly 1 collision comes back naming `PROOF-1` with both rules @integration
- PROOF-24 (RULE-19): Write a record whose three proof ids are distinct; verify zero findings come back @integration
- PROOF-25 (RULE-19): Write a record in which a Python entry and a TypeScript entry both claim `PROOF-1` for different rules; verify exactly 1 collision comes back naming `RULE-1` and `RULE-3` @integration
- PROOF-26 (RULE-19): Write a record carrying two separate collisions; verify 2 collisions come back, naming `PROOF-1` and `PROOF-3` @integration
- PROOF-27 (RULE-20): Write a spec declaring three rules and a record naming `RULE-99`, for each of the five languages; verify exactly 1 orphan comes back naming `RULE-99` @integration
- PROOF-28 (RULE-20): Write a record whose every rule is declared by the spec; verify zero orphans come back @integration
- PROOF-29 (RULE-20): Write a record naming `security_policy/RULE-1`, a rule an anchor owns; verify zero orphans come back @integration
- PROOF-30 (RULE-20): Run the record check with no spec named over a record naming `RULE-99`; verify zero orphans come back @integration
- PROOF-31 (RULE-34): Take the exclusive lock on a file, then run a second process that tries the same lock without blocking; verify it prints `held`, then release the lock and verify a second run prints `free` and the handle is closed @integration
- PROOF-32 (RULE-35): Parse the module's own source; verify no top-level statement imports fcntl outright, that the flag is assigned inside the try and inside an except that catches an import error, and that `msvcrt` appears in the source
- PROOF-33 (RULE-37): Take the exclusive lock on a file on Windows, then run a second process that tries `msvcrt.locking` without blocking; verify it prints `held`, then release the lock and verify a second run prints `free` @integration @env(windows)
- PROOF-34 (RULE-9): Run the command with `--json` over a TypeScript file carrying a tautological test, an empty body and a real assertion; verify the three results read `tautology`, `no_assertion` and `pass` @integration
- PROOF-35 (RULE-16): Read those same three results; verify each carries a proof id, a rule id, a test name, a status and a reason, that the first names `RULE-1`, and that the third's test name opens `real assertion` @integration
- PROOF-36 (RULE-10): Run the command with `--json` over a TypeScript file whose first test passes an options object to a call and whose second title carries an apostrophe; verify both proofs come back with status `pass` @integration
- PROOF-37 (RULE-35): Parse the module's own source; verify fcntl is imported inside a try, that `_HAS_FCNTL` is assigned in the try and in an except catching an import error, and that the module exposes that flag
- PROOF-38 (RULE-36): Parse the module's own source and read every call to open; verify each call that opens text passes the encoding `utf-8` and that the offending line numbers are zero
- PROOF-39 (RULE-11): Run the C# checker over a marked method whose body is `Assert.True(true);`; verify its status is `fail` and its check is `tautology` @integration
- PROOF-40 (RULE-11): Run the C# checker over a marked method that computes a value and asserts nothing; verify its status is `fail` and its check is `no_assertion` @integration
- PROOF-41 (RULE-11): Run the C# checker over four marked methods asserting through xUnit, NUnit, MSTest and FluentAssertions in turn; verify each comes back with status `pass` @integration
- PROOF-42 (RULE-21): Run the dispatcher over a `.cs` file carrying `PROOF-7`; verify the result names `PROOF-7` with the check `tautology`, and run it over a `.txt` file and verify zero results come back @integration
- PROOF-43 (RULE-11): Run the C# checker over a method asserting only through `Assertions.Expect(...).ToBeVisibleAsync()`; verify its status is `pass`, then over a method whose only call is `Expect(result);` and verify its check is `no_assertion` @integration
- PROOF-44 (RULE-12): Write `tests/AuthLogicTests.cs` declaring the class and a build copy under `bin/`, then resolve `Demo.Tests.AuthLogicTests.Evaluate_NullRow`; verify it returns `tests/AuthLogicTests.cs`, that a class declared nowhere returns empty, and that asking for the extension `.java` returns empty @integration
- PROOF-45 (RULE-13): Run the SQL checker over a bare `SELECT 'PASS'`, over a `CASE WHEN 1 = 1`, and over a `CASE WHEN 'alice' = 'alice'`; verify each is `fail` with the check `tautology` and the test name `the thing` @integration
- PROOF-46 (RULE-14): Run the SQL checker over a block whose only statement is an INSERT and which carries no `-- Test:` line; verify its status is `fail`, its check is `no_assertion` and its test name is `PROOF-3` @integration
- PROOF-47 (RULE-13): Run the SQL checker over three blocks whose predicates read a subquery, a function and a column; verify all three come back with status `pass` @integration
- PROOF-48 (RULE-15): Run the SQL checker over a file whose fourth block belongs to another feature; verify the results are exactly `PROOF-1`, `PROOF-2` and `PROOF-3` @integration
- PROOF-49 (RULE-21): Run the dispatcher over one always-true fixture per shipped extension; verify each yields exactly 1 result checked `tautology`, that an `.rb` file yields zero results and no body, and that the extractor set is the checker set less the shell extension @integration
- PROOF-50 (RULE-23): Build a project holding 12 specs and one test file per checked language, then sweep it; verify the sweep counts 12 features, 17 backings, and returns the expected status and check for every one of its 14 proofs @integration
- PROOF-51 (RULE-24): Run the sweep over that same project; verify the record naming a file nobody wrote is `missing_file`, the file carrying no marker for its proof is `marker_not_found`, the `.rb` backing is `no_checker`, and that none of them appears among the failing rows @integration
- PROOF-52 (RULE-25): Run the sweep over that same project; verify the proof with a clean and an always-true backing takes the failing file, the proof with a clean and an unreadable backing takes the unreadable one, and the proof with a failing and an unreadable backing takes the failing one @integration
- PROOF-53 (RULE-26): Hash every file of that project, run the sweep, and hash them again; verify the two mappings are equal, so 0 files changed @integration
- PROOF-54 (RULE-27): Run `--sweep --json` over this repository; verify it exits 0, that it swept one feature per spec file on disk, that zero backings are unmeasurable for want of a checker, and that the checkout and the runtime directory are byte-identical afterwards @integration
- PROOF-55 (RULE-32): Parse the command's own source; verify every `--flag` it compares against the argument list appears in the usage text, that the usage advertises no other flag, and that the docstring cites the exit convention
- PROOF-56 (RULE-33): Run the command with no argument at all; verify it exits 2 and prints every usage line on the error stream @integration
- PROOF-57 (RULE-33): Run the command with `--help`; verify it exits 0, prints every usage line, and prints `0 for a completed analysis` and `2 for a real error` @integration
- PROOF-58 (RULE-28): Extract the bodies of 7 proofs across two Python files and one shell file outside a run scope, then twice inside one; verify the Python files are parsed exactly 2 times in total and the three answers are equal @integration
- PROOF-59 (RULE-29): Extract a body outside any run scope, edit `value == 1` to `value == 10` in that test, and extract it again; verify the second body differs from the first and that no cache is left open @integration
- PROOF-60 (RULE-31): Read out the body of a Python proof and of a shell proof; verify the Python body comes back and the shell body is `none` @integration
- PROOF-61 (RULE-28): Run the checks for two features over one file and extract a body inside one run scope; verify the file is parsed exactly 1 time, that the scoped results equal the unscoped ones, and that the second feature's result names `PROOF-2` @integration
- PROOF-62 (RULE-30): Parse and split a source carrying carriage returns, a form feed and non-ASCII characters; verify the split equals the standard library's and that the sliced source of all 5 functions and decorators equals what the standard library returns
- PROOF-63 (RULE-28): Run the sweep over a project of 4 specs sharing 2 test files with a spy on open; verify every spec file and every test file is opened exactly 1 time and that no path is opened twice @integration
- PROOF-64 (RULE-22): Parse the module's own source; verify each brace-language wrapper is one return of a driver call, that the driver is defined exactly 1 time, and that running each wrapper over its always-true fixture returns the reason string that language's own proofs assert @integration
- PROOF-65 (RULE-1): Run the Python checker over a marked test asserting `r or True` after calling the code; verify its status is `fail` and its check is `assert_true_literal` @integration
- PROOF-66 (RULE-7): Run the Python checker over a marked test that asserts only against its own fixture list; verify its status is `pass`, because a fixture-only test is not a structural defect @integration
- PROOF-67 (RULE-7): Run the Python checker over a marked test that exercises only the accepting direction of a rejecting rule; verify its status is `pass`, because a missing case is not a structural defect @integration
- PROOF-68 (RULE-7): Run the Python checker over a marked test whose name says rejects and whose assertion says accepted; verify its status is `pass`, because a name that drifts is not a structural defect @integration
- PROOF-69 (RULE-3): Run the Python checker over a marked test that builds a payload, encrypts it and decodes it without asserting; verify its status is `fail` @integration
- PROOF-70 (RULE-38): Run the JavaScript checker over one file whose first test divides across a line break after `"a" +`, whose second builds `/[}/"']+/g`, whose third builds `/\/}/`, whose fourth holds a `}` in a `//` comment and in a `/* */` comment, and whose fifth and sixth sit on one line dividing `4 / 2` and `8 / 4`, each with its assertion after that character; verify exactly the 6 proofs `PROOF-1` to `PROOF-6` come back, every one with status `pass` and none with the check `no_assertion` @integration
- PROOF-71 (RULE-39): Call the command in the same process without `--json` over a file holding one marked test asserting a literal and one asserting `True`; verify it exits 0 and prints exactly the two lines `pass PROOF-1 test_good` and `fail PROOF-2 assert_true_literal: <reason>`. Scaffold a project whose one proof is backed by `assert True` and call `--sweep --project-root <it>`; verify it exits 0, that its first line is `1 features, 1 backings, 0 pass, 1 failing, 0 unmeasurable`, and that its second names the feature, `PROOF-1`, `fail`, `assert_true_literal` and the test file @integration
