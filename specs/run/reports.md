# Feature: reports

> Description: How a test's result reaches its proof. A test is any test in the project's own
>   suite that carries one comment naming the proof, `purlin: <feature> PROOF-<n>`, or the
>   rule where a rule has no proof. The settings file names each suite's own command, where
>   its report lands, the report's format and the globs its test files live under. Purlin
>   runs the command, reads the report, finds each result's test in its file by name, and
>   gives the result to every marker above that test. A marker it cannot tie to exactly one
>   test is reported by file and line; it never guesses.
> Scope: scripts/run/reports.py, scripts/mcp/purlin/markers.py, references/formats/marker_format.md
> Stack: python/stdlib (xml.etree, json, tokenize, ast, re, shlex), pytest, jest, vitest, dotnet, go, bash, sqlite3

## Rules

- RULE-1: A marker is one whole-line comment, `purlin: <feature> PROOF-<n>` or `purlin: <feature> RULE-<n>`, after any of `#`, `//`, `--`, `;`, `%` and `'`, or inside a one-line `/* */` or `<!-- -->`; a `purlin:` comment of any other shape ties nothing
- RULE-2: A marker-shaped line inside a Python string or inside a shell here document is not a marker
- RULE-3: Only a file one suite's `files` globs match is read for markers; `*` and `?` match within one path segment, `**` matches any number of segments, a glob with no `/` matches that file name in any directory, and a file two suites match belongs to the first
- RULE-4: A marker belongs to the next test declared after it in its file: blank lines, decorators, attributes and other comments may sit between them, every marker between the previous test's declaration and this one belongs to this one, and the test's result counts for each of them
- RULE-5: A marker no test follows is reported as `purlin: <feature> <id> at <file>:<line> is tied to no test` and its result is `not run`, which the evidence writes as `missing`
- RULE-6: A test is declared by a Python function whose name starts with `test`, at module level or in a class; a JavaScript or TypeScript `it` or `test` call with a literal title, inside any number of `describe` calls; a C# method carrying `[Fact]`, `[Theory]`, `[Test]`, `[TestCase]`, `[TestCaseSource]`, `[TestMethod]`, `[DataTestMethod]`, `[SkippableFact]` or `[SkippableTheory]`; a Go `func TestX(t *testing.T)`
- RULE-7: A `junit` report is read case by case: a case with a `failure` or `error` child fails, one with a `skipped` child is skipped, and any other passes; its `classname`, `name` and `file` are what the tie reads
- RULE-8: A `trx` report is read result by result, each joined through its `testId` to the class and method it ran: `Passed`, `Warning`, `Completed` and `PassedButRunAborted` pass, `Failed`, `Error`, `Timeout` and `Aborted` fail, and any other outcome is skipped
- RULE-9: A `gotest` report is the JSON stream a Go test run prints on its standard output, read event by event: an event naming a test whose action is `pass`, `fail` or `skip` is that test's result, and every other event, and every line that is not JSON, is left alone
- RULE-10: A case's file is its `file` attribute where the report writes one, else its class name where that is a path, else the Python module its dotted class name names among the suite's marked files; a `trx` case is found by its class chain, narrowed by namespace, and a `gotest` case by its package, read against the module line of `go.mod`
- RULE-11: The cases of one parametrised test, `test_x[a]` and `test_x[b]`, `TestX/a`, `Method(x: 1)`, or the rows of an `it.each` table, all belong to that one test, and the test passes only when every one of them passes
- RULE-12: A nested title, `outer > inner > title`, is matched by its last part and, where two tests in the file share that part, narrowed by the outer parts; a Python class and a C# class narrow the same way
- RULE-13: A case that matches more than one test is counted for none of them, and the run prints `purlin: the report's <name> matches <n> tests in <file>, so its result is not counted`
- RULE-14: A test whose cases all passed reads `pass`; one with any failed or errored case reads `fail`; any other, its cases all or partly skipped with none failed, or none of them in the report, reads `not run`, which the evidence writes as `missing`
- RULE-15: In an `exit` suite each test file is one test: the command runs once per file, with `{files}` that one file, and the file passes when the command exits 0; every marker in the file takes the file's result
- RULE-16: `{files}` in a suite's command becomes the test files that carry a marker of a feature the run covers, each quoted, on a run over some features, and nothing on a run over every feature; `{report}` becomes the report path
- RULE-17: A suite's report is deleted before the suite runs, file or folder, so a report from an earlier run is never read
- RULE-18: A suite that leaves no report to read makes the run say `Evidence is missing: the <name> suite wrote no report at <path>.`, or `in <path>` where it left a folder with no report in it, and exit 1
- RULE-19: A marker naming a feature no spec has, or a proof or a rule its feature's spec does not have, is printed as `<file>:<line> names <feature> <ID>, which no spec has. Correct the comment, or run purlin:build to repair it.`, and one naming a rule that has proofs as `purlin: <feature> <id> at <file>:<line> names a rule that has proofs; name one of them`; either exits the run 1 whatever its tests did
- RULE-20: A `tests` entry with no `run`, a `format` other than `junit`, `trx`, `gotest` and `exit`, or no `files` is left out with one line naming the suite and why
- RULE-21: `markers.py --near-misses --project-root <dir>` prints one JSON array holding `{"file", "line", "text", "fix", "why"}` for each comment that is nearly a marker, in a file one suite's globs match, and exits 0; any other command line exits 2
- RULE-22: A comment whose `purlin` is misspelled by one letter or written in capitals, or that has no space after the colon, is a near miss whose fix is the marker it meant, and a marker naming what a spec has is none
- RULE-23: A `purlin:` comment that cannot be read as a feature and a PROOF or RULE id is a near miss with no fix
- RULE-24: A marker whose feature, or whose PROOF or RULE id, is one character from exactly one that exists is a near miss whose fix names only an id a comment may name: that feature, that proof, that rule where it has no proof, or its one proof where it has exactly one; one character from a rule with two or more proofs, or from two or more that exist, is none
- RULE-25: A suite's command runs through bash
- RULE-26: A suite's command runs from the project root
- RULE-27: A report path that is a folder is read file by file
- RULE-28: A report path of `-` is read from the command's standard output

## Proof

- PROOF-1 (RULE-1): A file holds eight lines, each a marker of `login`: after `#`, `//`, `--`, `;`, `%` and `'`, inside `/* */` naming `RULE-7`, and inside `<!-- -->`; all eight read as markers, each with its feature, its id and its line, 1 to 8
- PROOF-26 (RULE-1): The line `# purlin: login`, which names no proof and no rule, is not read as a marker
- PROOF-27 (RULE-1): In a plain text file, the line `x = 1  # purlin: login PROOF-1`, a marker after code on the same line, is not read as a marker
- PROOF-40 (RULE-1): In a Python file, the line `x = 1  # purlin: login PROOF-1`, a marker after code on the same line, is not read as a marker
- PROOF-2 (RULE-2): A Python test file holds `# purlin: login PROOF-1` on line 2, inside a triple-quoted string, and the same line as a comment on line 5; one marker is read, at line 5
- PROOF-41 (RULE-2): A shell script writes `# purlin: login PROOF-1` into another file through a here document, then carries `# purlin: login PROOF-2` as a comment; `PROOF-2` is the only marker read
- PROOF-3 (RULE-3): Of the paths `dev/test_a.py`, `dev/sub/test_b.py` and `a/b/c.test.ts`, the glob `dev/test_*.py` matches `dev/test_a.py` alone, since `*` does not cross a `/`
- PROOF-42 (RULE-3): Of the paths `dev/test_a.py`, `dev/sub/test_b.py` and `a/b/c.test.ts`, the glob `**/*.test.ts` matches `a/b/c.test.ts` alone, two folders down
- PROOF-43 (RULE-3): Of the paths `dev/test_a.py`, `dev/sub/test_b.py` and `a/b/c.test.ts`, the glob `test_*.py`, which has no `/`, matches the first two and not the third
- PROOF-44 (RULE-3): The glob `dev/test_?.py` matches `dev/test_a.py` and neither `dev/test_ab.py` nor `dev/test_/.py`, since `?` is exactly one character and never a `/`
- PROOF-45 (RULE-3): The glob `**/*.py` matches `x.py`, a file at the top of the project, since `**` may stand for no folder at all
- PROOF-46 (RULE-3): The glob `dev/**/test_*.py` matches `dev/test_a.py`, with no folder between `dev` and the file
- PROOF-47 (RULE-3): With a suite `first` on `tests/*.py` and then a suite `second` on `**/*.py`, `tests/test_a.py`, which both match, belongs to `first`, and `other/test_b.py`, which only `second` matches, belongs to `second`
- PROOF-48 (RULE-3): With one suite, on `tests/*.py`, markers are read from `tests/test_a.py` and not from `other/test_b.py`, which carries a marker too
- PROOF-4 (RULE-4): A Python test file holds the marker `login PROOF-1` above a decorator above the passing test `test_decorated`; the run's evidence holds exactly one result, `PROOF-1` `pass` under `tests/test_login.py::test_decorated`
- PROOF-49 (RULE-4): A Python test file holds the markers `login PROOF-1` and `login PROOF-2`, one above the other, over the passing test `test_two`; the evidence holds exactly two results, each proof `pass` under `tests/test_login.py::test_two`
- PROOF-50 (RULE-4): A Python test file holds `login PROOF-1`, then a blank line, an ordinary comment and a decorator, then the passing test `test_decorated`; the evidence holds exactly one result, `PROOF-1` `pass` under `tests/test_login.py::test_decorated`
- PROOF-51 (RULE-4): The markers `login PROOF-1` and `login PROOF-2` sit over `test_two`, which fails; the run exits 1 and the evidence holds exactly two entries, each proof once, `fail` under `tests/test_login.py::test_two`
- PROOF-5 (RULE-5): A Python test file ends with the marker `login PROOF-3` on its line 9, with no test after it; the run prints `purlin: login PROOF-3 at tests/test_login.py:9 is tied to no test`, exits 1, and the evidence holds `PROOF-3` with no test and the result `missing`
- PROOF-52 (RULE-5): In the same file, `login PROOF-1` and `login PROOF-2` each sit above a passing test; the evidence holds both `pass` under their tests, and the run prints `Evidence is missing: 1 marker has no passing or failing result: login PROOF-3 at tests/test_login.py:9.`
- PROOF-6 (RULE-6): A Python file of a module-level `helper`, `test_a`, and a class `TestB` holding `test_c` and a method `helper` declares exactly two tests, `test_a` and `test_c` in `TestB`
- PROOF-53 (RULE-6): A TypeScript file declares exactly its five `it` and `test` calls: `accepts` at the top, `same name` inside `outer` and then `inner`, and `same name`, `skipped` and `param %i` inside `outer`
- PROOF-54 (RULE-6): A C# file declares `GreetsByName` under `[Fact]`, `Param` under `[Theory]` and `Skipped` in the class `GreetingTests`, and `Inner` in its nested class `Nested`, all four in the namespace `App.Tests`
- PROOF-55 (RULE-6): A Go file declares its four `TestX` functions, `TestTotal`, `TestParse`, `TestDiscount` and `TestTotalIsWrong`, in the order written
- PROOF-56 (RULE-6): A C# class `C` in the namespace `N` holds one method under each of `[Test]`, `[TestCase(1)]`, `[TestCaseSource]`, `[TestMethod]`, `[DataTestMethod]`, `[SkippableFact]` and `[SkippableTheory]`, and a method `Helper` with no attribute; it declares exactly the seven attributed methods
- PROOF-57 (RULE-6): A script calling `it` with a title held in a variable, then `test("lit", ...)`, declares exactly one test, `lit`
- PROOF-58 (RULE-6): A Go file of `helper(t *testing.T)`, `TestA(t *testing.T)`, `BenchmarkB(b *testing.B)` and `TestLike(n int)` declares exactly one test, `TestA`
- PROOF-7 (RULE-7): The JUnit report written by running four Python tests, one passing, one failing an assertion, one skipped and one whose setup raises an error, reads as four cases in that order: `test_passes` `pass`, `test_fails` `fail`, `test_skipped` `skip` and `test_errors` `fail`, each with the class name `tests.test_login`
- PROOF-8 (RULE-8): The TRX report `dotnet test --logger trx` wrote reads, in its order, as `GreetsByName` `pass`, `Param` `pass` for the row `x: 2`, `Param` `fail` for the row `x: 1`, `Skipped` `skip` from `NotExecuted`, `Inner` `pass` in `App.Tests.GreetingTests+Nested`, and `GreetsByName` `fail` in `Other.Tests.GreetingTests`, the first four in `App.Tests.GreetingTests`
- PROOF-59 (RULE-8): A TRX report of four results whose outcomes are `Error`, `Timeout`, `Aborted` and `Inconclusive` reads as `fail`, `fail`, `fail` and `skip`
- PROOF-94 (RULE-8): A TRX report of one result whose outcome is `Warning` reads as `pass`
- PROOF-95 (RULE-8): A TRX report of one result whose outcome is `Completed` reads as `pass`
- PROOF-96 (RULE-8): A TRX report of one result whose outcome is `PassedButRunAborted` reads as `pass`
- PROOF-9 (RULE-9): The stream `go test -json` printed for two packages reads as exactly eight cases: `TestRate` `pass` and `TestLookupPanics` `fail` in `example.com/shop/tax`, then `TestTotal` `pass`, `TestParse/empty` `fail`, `TestParse/one` `pass`, `TestParse` `fail`, `TestDiscount` `skip` and `TestTotalIsWrong` `fail` in `example.com/shop/cart`
- PROOF-60 (RULE-9): The same stream with a line that is not JSON, `ok`, the module and a time, added at its end reads as the same eight cases, in the same order
- PROOF-10 (RULE-10): A passing Python case whose class reads `tests.test_login.TestGroup` gives `pass` to the marked method `test_same` of the class `TestGroup` in `tests/test_login.py`
- PROOF-61 (RULE-10): In a Vitest report, where each case's class reads `tests/login.test.ts`, the passing case `accepts` gives `pass` to the marker `login PROOF-1` in that file
- PROOF-62 (RULE-10): In a Jest report, where each case's `file` reads `tests/login.test.js` and its class names no file, the passing case `accepts` gives `pass` to the marker `login PROOF-1` in that file
- PROOF-63 (RULE-10): Two TRX cases of a class `GreetingTests`, one in the namespace `App.Tests` passing and one in `Other.Tests` failing, give `pass` to `App.Tests/GreetingTests.cs` and `fail` to `App.Tests/OtherGreetingTests.cs`, with no problem reported
- PROOF-64 (RULE-10): Under a `go.mod` reading `module example.com/shop`, `TestTotal` of the package `example.com/shop/cart` gives `pass` to `cart/cart_test.go`, and `TestRate` of `example.com/shop/tax` gives `pass` to `tax/tax_test.go`
- PROOF-65 (RULE-10): A failing Python case of the class `tests.test_elsewhere`, a file that does not exist, is tied to no test: every other result stays as it was, and no problem is reported
- PROOF-66 (RULE-10): A failing TRX case of the class `Nowhere.Tests.MissingTests`, which no marked file declares, is tied to no test: every other result stays as it was, and no problem is reported
- PROOF-67 (RULE-10): A failing Go case of the package `example.com/shop/nowhere`, which no folder of the module holds, is tied to no test: every other result stays as it was
- PROOF-11 (RULE-11): A marked Python test run over the two values 1 and 2, both passing, reads `pass`
- PROOF-68 (RULE-11): A marked Python test run over the two values 1 and -2, where -2 fails, reads `fail`
- PROOF-69 (RULE-11): A marked C# theory of two rows, one passing and one failing, reads `fail`
- PROOF-70 (RULE-11): A marked Go test whose subtest `TestParse/empty` failed beside a passing `TestParse/one` reads `fail`
- PROOF-71 (RULE-11): A marked Vitest `test.each` table of two passing rows, `param 1` and `param 2`, reads `pass`
- PROOF-12 (RULE-12): A test file declares `same name` inside `outer` and then `inner`, marked and passing, and `same name` directly inside `outer`, unmarked and failing; from the Vitest report the marker reads `pass`, and no case is reported as matching two tests
- PROOF-72 (RULE-12): A test file declares `same name` inside `outer` and then `inner`, marked and passing, and `same name` directly inside `outer`, unmarked and failing; from the Jest report the marker reads `pass`, and no case is reported as matching two tests
- PROOF-73 (RULE-12): In a Python file the classes `TestGroup` and `TestOther` each declare `test_same`, the marked one in `TestGroup` passing and the other failing; the marker reads `pass`, and no case is reported as matching two tests
- PROOF-74 (RULE-12): In a C# file the classes `First` and `Second` of the namespace `N` each declare a test `Same`, `First`'s marked and passing and `Second`'s failing; the marker reads `pass`, and no case is reported as matching two tests
- PROOF-13 (RULE-13): A Python test file declares `test_x` twice, marked `login PROOF-1` and `login PROOF-2`, and its one case passes; the run prints `purlin: the report's test_x matches 2 tests in tests/test_login.py, so its result is not counted` on a line of its own, the evidence holds both proofs `missing`, and it exits 1
- PROOF-14 (RULE-14): Of five marked Python tests run together, the one that passes is `pass` in the evidence
- PROOF-75 (RULE-14): Of five marked Python tests run together, the one that fails an assertion is `fail` in the evidence
- PROOF-76 (RULE-14): Of five marked Python tests run together, the one that is skipped is `missing` in the evidence
- PROOF-77 (RULE-14): Of five marked Python tests run together, the one whose setup raises an error is `fail` in the evidence
- PROOF-78 (RULE-14): Of five marked Python tests run together, the one run over two values, one passing and one skipped, is `missing` in the evidence
- PROOF-79 (RULE-14): A suite's command writes a report holding a passing case for `test_a` and none for `test_b`, both marked; the evidence holds `test_a`'s proof `pass` and `test_b`'s `missing`
- PROOF-15 (RULE-15): An `exit` suite covers `tests/good.sh`, which carries two markers and exits 0, and `tests/bad.sh`, which carries one and exits 3; the evidence reads `pass` for both markers of the first, under `tests/good.sh::good.sh`, and `fail` for the second's, under `tests/bad.sh::bad.sh`; the run exits 1 and never says `Evidence is missing`
- PROOF-80 (RULE-15): With the same two scripts, the suite's command, which also writes down the files it is given, ran exactly twice: once given `tests/bad.sh` alone and once given `tests/good.sh` alone
- PROOF-16 (RULE-16): `login` and `signup` each have one marked test file, and the suite's command writes down its arguments; a run over `login` alone gives it exactly `tests/test_login.py` and the report path `.purlin/runtime/reports/pytest.xml`
- PROOF-81 (RULE-16): `login` and `signup` each have one marked test file, and the suite's command writes down its arguments; a run over every feature gives it the report path alone, with no test file
- PROOF-82 (RULE-16): The marked test file of `signup` is `tests/test_sign up.py`, whose name holds a space; a run over `signup` alone gives the command that path as one argument, then the report path
- PROOF-83 (RULE-25): A suite's command, asked which shell runs it, answers bash
- PROOF-84 (RULE-26): A run started from a folder outside the project runs the suite's command in the project root: the command, asked the folder it runs in, answers the project root
- PROOF-17 (RULE-17): A report left from an earlier run, holding one passing case, sits at the suite's report path, and the suite's command writes nothing; the run exits 1 saying `wrote no report`, and the old report is gone
- PROOF-85 (RULE-17): The suite's report path is a folder holding an old report of one passing case, and the command writes nothing; the run exits 1 saying `wrote no report at .purlin/runtime/reports/out`, and the folder is gone
- PROOF-86 (RULE-27): A suite's report path is a folder, and its command writes two TRX reports into it, one passing the test `A` and one failing the test `B`; the evidence holds `A`'s proof `pass` and `B`'s `fail`
- PROOF-87 (RULE-28): A suite whose report path is `-` and whose command prints the stream of a Go run gives every Go test in the evidence its result from that stream: `TestTotal` `pass`, `TestLookupPanics` `fail` and `TestDiscount` `missing`
- PROOF-18 (RULE-18): A suite whose command exits 0 and writes no report ends the run with `Evidence is missing: the pytest suite wrote no report at .purlin/runtime/reports/pytest.xml.` and exit code 1
- PROOF-93 (RULE-18): A `trx` suite whose command makes its report folder and leaves it empty ends the run with `Evidence is missing: the dotnet suite wrote no report in .purlin/runtime/reports/out.` and exit code 1
- PROOF-19 (RULE-19): Every rule of `login` has a passing test, and one more passing test, on line 13, is marked `purlin: nosuch PROOF-1`; the run prints `tests/test_login.py:13 names nosuch PROOF-1, which no spec has. Correct the comment, or run purlin:build to repair it.` and exits 1
- PROOF-21 (RULE-19): `login` has `PROOF-1` to `PROOF-3`, each with a passing test, and one more passing test, on line 13, is marked `purlin: login PROOF-9`; the run prints `tests/test_login.py:13 names login PROOF-9, which no spec has. Correct the comment, or run purlin:build to repair it.` and exits 1
- PROOF-22 (RULE-19): `login` has `RULE-1` to `RULE-3`, each with a passing test, and one more passing test, on line 13, is marked `purlin: login RULE-9`; the run prints `tests/test_login.py:13 names login RULE-9, which no spec has. Correct the comment, or run purlin:build to repair it.` and exits 1
- PROOF-23 (RULE-19): Every rule of `login` has a passing test, and one more passing test, on line 13, is marked `purlin: login RULE-1`, a rule that has `PROOF-1`; the run prints `purlin: login RULE-1 at tests/test_login.py:13 names a rule that has proofs; name one of them` and exits 1
- PROOF-24 (RULE-19): The same project with only the three markers `login PROOF-1`, `PROOF-2` and `PROOF-3`, each above a passing test, exits 0, and nothing it prints contains `which no spec has` or `names a rule that has proofs`
- PROOF-25 (RULE-19): Two passing tests are marked for features no spec has, `nosuch` on line 13 and `other` on line 17; the run prints `tests/test_login.py:13 names nosuch PROOF-1, which no spec has.` and `tests/test_login.py:17 names other PROOF-2, which no spec has.`, each at the start of its own line with the advice after it, and exits 1
- PROOF-20 (RULE-20): Beside one complete suite, a `tests` entry `a` names no `run`; the run prints `purlin: the a suite names no run command.`, starts only the complete suite, printing `Running the pytest suite.` alone, and exits 0 when its tests pass
- PROOF-88 (RULE-20): Beside one complete suite, a `tests` entry `b` names the format `tap`; the run prints `purlin: the b suite names the format "tap", which is not one of junit, trx, gotest, exit.`, starts only the complete suite, and exits 0 when its tests pass
- PROOF-89 (RULE-20): Beside one complete suite, a `tests` entry `c` names no `files`; the run prints `purlin: the c suite names no files.`, starts only the complete suite, and exits 0 when its tests pass
- PROOF-28 (RULE-21): In a project whose pytest suite reads `tests/test_login.py`, where line 1 reads `# purln: login PROOF-1`, `--near-misses` prints one JSON array holding one entry: file `tests/test_login.py`, line 1, that text, the fix `# purlin: login PROOF-1`, and a `why` naming `purln`; it exits 0
- PROOF-29 (RULE-21): `markers.py --near-misses --nonsense` prints the line `Usage: markers.py --near-misses [--project-root DIR]` and exits 2
- PROOF-30 (RULE-21): A misspelled comment in a file no suite's globs match is not listed, and the array is empty
- PROOF-31 (RULE-22): A test file carrying `# PURLIN: login PROOF-1` is listed with the fix `# purlin: login PROOF-1`, and its why is the one sentence saying `PURLIN` is `purlin` in capitals
- PROOF-32 (RULE-22): A test file carrying `# purlin:login PROOF-1` is listed with the fix `# purlin: login PROOF-1`, and its why reads `There is no space after the colon.`
- PROOF-90 (RULE-22): A test file carrying `# purlim: login PROOF-1` is listed with the fix `# purlin: login PROOF-1`, and its why is the one sentence saying `purlim` is one letter from `purlin`
- PROOF-33 (RULE-22): A test file carrying `# purlin: login PROOF-1`, naming a feature and a proof a spec has, is not listed: the array is empty
- PROOF-34 (RULE-23): A test file carrying `# purlin: login`, which names no id, is listed with the fix null
- PROOF-38 (RULE-23): A test file carrying `# purlin: login TEST-1`, whose id is neither a PROOF nor a RULE, is listed with the fix null
- PROOF-35 (RULE-24): Where the spec `login` exists, a test file carrying `# purlin: logn PROOF-1` is listed with the fix `# purlin: login PROOF-1`, and why names `logn` and `login`
- PROOF-36 (RULE-24): Where `login` has `PROOF-1`, `PROOF-2` and `PROOF-3`, a test file carrying `# purlin: login PROOF-30` is listed with the fix `# purlin: login PROOF-3`
- PROOF-39 (RULE-24): Where `login` has `PROOF-2`, a test file carrying `# purlin: login PROF-2` is listed with the fix `# purlin: login PROOF-2`
- PROOF-91 (RULE-24): Where `login`'s `RULE-3` has the one proof `PROOF-3`, a test file carrying `# purlin: login RULE-30` is listed with the fix `# purlin: login PROOF-3`, and its why is the one sentence saying `RULE-30` is one character from `RULE-3`, which login has, and that a comment names its one proof, `PROOF-3`
- PROOF-97 (RULE-24): Where `login`'s `RULE-3` has two proofs, `PROOF-3` and `PROOF-4`, a test file carrying `# purlin: login RULE-30` is not listed: the array is empty
- PROOF-98 (RULE-24): Where `login`'s `RULE-3` has no proof, a test file carrying `# purlin: login RULE-30` is listed with the fix `# purlin: login RULE-3`
- PROOF-37 (RULE-24): Where `login` has `PROOF-1`, `PROOF-2` and `PROOF-3`, a test file carrying `# purlin: login PROOF-4`, one character from all three, is not listed: the array is empty
- PROOF-92 (RULE-24): Where the specs `login` and `logon` both exist, a test file carrying `# purlin: logn PROOF-1`, one character from each, is not listed: the array is empty
