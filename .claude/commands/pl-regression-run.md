**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-regression-run instead." and stop.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Overview

Execute existing regression scenarios. This is the routine regression operation -- composing and presenting a copy-pasteable command for the user to run externally.

**MANDATORY UX RULE:** Whenever you ask the user to run something in an external terminal, you MUST print the exact, complete, copy-pasteable command. Never describe what to run in prose.

---

## Arguments

```
/pl-regression-run [--frequency <per-feature|pre-release>]
```

- **--frequency per-feature** (default): Include only standard-frequency suites.
- **--frequency pre-release**: Include all suites, including long-running `pre-release` suites (e.g., skill behavior tests using `claude --print`).

When no `--frequency` flag is provided, `pre-release` suites are excluded from the eligible list.

---

## Step 1 -- Discovery

Run `${TOOLS_ROOT}/cdd/status.sh --role qa` and parse the output. Identify regression-eligible features:

- `tests/qa/scenarios/<feature_name>.json` exists for the feature.
- **AND** one of:
  - `tests.json` has `status: "FAIL"` (FAIL)
  - `tests.json` is missing or has `total: 0` (NOT_RUN)
  - Feature source was modified after `tests.json` mtime (STALE)

**Frequency filtering:** For each eligible scenario file, read the `frequency` field:
- If `--frequency pre-release` was specified: include all suites regardless of frequency.
- Otherwise (default): exclude suites where `frequency` is `pre-release`.

Sort eligible features: STALE first, then FAIL, then NOT_RUN.

---

## Step 2 -- Present Options

If zero features are eligible:
- Print: "No regression-eligible features found. All regression results are current."
- Stop.

If features are found:

```
Found N features eligible for regression:

  1. [STALE] instruction_audit -- last tested 2h ago, source modified 1h ago
  2. [FAIL]  pl_web_test -- 3/5 scenarios failing
  3. [NOT_RUN] new_feature -- no test results

Run all, select specific features, or skip? [all / 1,2,... / skip]
```

Wait for user selection.

---

## Step 3 -- Compose Command

Based on user selection, compose the run command.

**Single feature (via meta-runner):**
```
${TOOLS_ROOT}/test_support/run_regression.sh --scenarios-dir tests/qa/scenarios
```

Or for the consumer wrapper:
```
./tests/qa/run_all.sh
```

**Multiple features (sequential chain):**
```
python3 ${TOOLS_ROOT}/test_support/harness_runner.py tests/qa/scenarios/<feature1>.json && \
python3 ${TOOLS_ROOT}/test_support/harness_runner.py tests/qa/scenarios/<feature2>.json
```

Print the command in a clearly formatted, self-contained, copy-pasteable block:

```
Run this in a separate terminal:

    ./tests/qa/run_all.sh

Tell me when it finishes.
```

---

## Step 4 -- Productive Wait

After printing the command block, offer concurrent work:

```
While tests run, I can:
  - Author regression scenarios for other features (/pl-regression-author)
  - Review open discoveries
  - Generate a QA report (/pl-qa-report)

Say "continue" for other work, or tell me when tests finish.
```

If the user says "continue", proceed with suggested work. When the user reports test completion, direct them to run `/pl-regression-evaluate` to process results.
