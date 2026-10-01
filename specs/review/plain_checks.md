# Feature: plain_checks

> Description: The heuristic spot tests, the audit's first step. They read each marked test as
>   text, without running it, and flag a test that cannot fail, as
>   `references/review_criteria.md`, "Heuristic spot tests", gives them: six checks, each with
>   what it flags, what it does not flag and the finding it reports, naming the test's file and
>   name. Python is read by its syntax tree; JavaScript, TypeScript, C#, Go and shell by the
>   token reading the markers already use. A check a language cannot be read for is skipped and
>   named once. No model is called.
> Scope: scripts/review/plain_checks.py
> Stack: python/stdlib (ast, re)
> Highest-Rule: 9
> Highest-Proof: 30

## Rules

- RULE-1: A test whose body, and the helpers it calls in the same file, hold no assertion of its test framework reads `<file>::<test>: the test checks nothing.`; a test that calls a helper defined in another file, or that only expects an error, is not flagged
- RULE-2: An assertion that is true whatever the code does, a literal true, a value compared with itself or a size compared as at least zero, reads `<file>::<test>: the check cannot fail: <the assertion>.`; a weak but failable check is not flagged
- RULE-3: A `try` around the code under test whose `except` or `catch` does nothing and neither asserts nor re-raises reads `<file>::<test>: the test swallows the error the code raises.`; a handler that asserts on the error, or a `try` used only for cleanup, is not flagged
- RULE-4: An assertion whose expected value is computed by the same function whose result it checks reads `<file>::<test>: the expected value comes from <function>(), the code under test.`; an expected value from a different function, a library or a literal is not flagged
- RULE-5: A mock, patch, stub or fake whose target is the same function whose result the test asserts on reads `<file>::<test>: the test mocks <function>(), the function it checks.`; a mock of something the code depends on is not flagged
- RULE-6: A test whose file holds none of the values its proof marks in backticks reads `<file>::<test>: the proof expects <value> and the test never checks it.`; a proof with no value in backticks, the same number written another way, or a value held in a data file the test's file names, is not flagged
- RULE-7: A check that cannot be read in a test's language is skipped, and the audit prints `<check> is not read in <language> tests.` once per check and language
- RULE-9: The spot tests start no `claude`

## Proof

- PROOF-1 (RULE-1): `tests/test_age.py` holds `test_age`, which calls `age("2026-01-01")` and asserts nothing; the finding is `tests/test_age.py::test_age: the test checks nothing.`
- PROOF-3 (RULE-1): `test_age` asserts nothing itself and calls `check_age()`, which `tests/test_age.py` imports from `tests/helpers.py`; nothing is found
- PROOF-4 (RULE-1): `test_bad_zone` holds only `with pytest.raises(ValueError): age("2026-01-01", zone="Mars")`; nothing is found
- PROOF-9 (RULE-2): `test_age` holds `assert days == days`; the finding is `tests/test_age.py::test_age: the check cannot fail: assert days == days.`
- PROOF-10 (RULE-2): `test_age` holds only `assert result is not None`; nothing is found
- PROOF-11 (RULE-2): `tests/age.test.ts` holds the test `age` with `expect(true).toBe(true)`; the finding is `tests/age.test.ts::age: the check cannot fail: expect(true).toBe(true).`
- PROOF-13 (RULE-3): `test_bad_zone` calls `age` inside a `try` whose `except ValueError:` holds only `pass`; the finding is `tests/test_age.py::test_bad_zone: the test swallows the error the code raises.`
- PROOF-14 (RULE-3): `test_bad_zone` calls `age` inside a `try` whose `except ValueError as e:` holds `assert "zone" in str(e)`; nothing is found
- PROOF-17 (RULE-3): `Tests/AgeTests.cs` holds the test `BadZone`, calling `Age` inside a `try` whose `catch { }` is empty; the finding is `Tests/AgeTests.cs::BadZone: the test swallows the error the code raises.`
- PROOF-18 (RULE-4): `test_age` holds `expected = age(s)` then `assert age(s) == expected`; the finding is `tests/test_age.py::test_age: the expected value comes from age(), the code under test.`
- PROOF-19 (RULE-4): `test_age` holds `assert age(s) == days_between(s, today)`, where `days_between` is not `age`; nothing is found
- PROOF-20 (RULE-4): `tests/age.test.ts` holds the test `age` with `const expected = age(s)` then `expect(age(s)).toBe(expected)`; the finding is `tests/age.test.ts::age: the expected value comes from age(), the code under test.`
- PROOF-22 (RULE-5): `test_age` patches `app.age` to return `90` and then asserts `age(s) == 90`; the finding is `tests/test_age.py::test_age: the test mocks age(), the function it checks.`
- PROOF-23 (RULE-5): `test_age` patches `app.clock.now` to a fixed date and then asserts `age(s) == 90`; nothing is found
- PROOF-24 (RULE-5): `tests/age.test.ts` holds the test `age` with `jest.spyOn(lib, "age").mockReturnValue(90)` then `expect(lib.age(s)).toBe(90)`; the finding is `tests/age.test.ts::age: the test mocks age(), the function it checks.`
- PROOF-25 (RULE-6): `PROOF-1` reads "has an age of `90` minutes" and `tests/test_age.py` holds no `90`; the finding is `tests/test_age.py::test_age: the proof expects 90 and the test never checks it.`
- PROOF-26 (RULE-6): `PROOF-1` reads "has an age of `90` minutes" and `tests/test_age.py` holds `assert minutes == 90.0`; nothing is found
- PROOF-27 (RULE-6): `PROOF-1` reads "has an age of `90` minutes"; `tests/test_age.py` holds no `90` but names `tests/data/ages.json`, which holds `90`; nothing is found
- PROOF-28 (RULE-7): A project's marked tests are two shell tests; the audit prints `The test replaces what it is testing is not read in shell tests.` exactly once
- PROOF-30 (RULE-9): With a `claude` on the path that records each start, the spot tests read every marked test of a project of three features; `claude` is started `0` times
