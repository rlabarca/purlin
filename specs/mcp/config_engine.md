# Feature: config_engine

> Description: One settings file, `.purlin/config.json`, committed with the
>   project. The resolver reads it whole and the settings tool writes one key
>   into it. The same module decides where the project root is and names how
>   it found it.
> Scope: scripts/mcp/config_engine.py
> Stack: python/stdlib, json

## Rules

- RULE-1: The project root is the `PURLIN_PROJECT_ROOT` environment variable when it names a directory that exists
- RULE-2: Failing that, the root is found by climbing from the start directory to the nearest ancestor holding a `.purlin/` marker directory
- RULE-3: Failing both, the root is the working directory
- RULE-4: The config is `.purlin/config.json` read whole, the one settings file a project has
- RULE-7: With no `config.json` on disk the config is empty
- RULE-8: A write sets one top-level key in `.purlin/config.json`, the committed file, creating it when it is absent
- RULE-9: A write preserves every other key `config.json` already held
- RULE-10: A write is atomic: the whole file is written beside the target and then moved onto it, so a write that fails at any point leaves the previous contents whole, removes the file it wrote beside the target, and says so
- RULE-13: The project root comes with the name of how it was found, `env`, `climb` or `cwd`, by the precedence RULE-1 to RULE-3 describe, each name with the sentence a report prints for it, so a root that is only the working directory is named as that guess and not handed back as if a marker were found. Asked for alone, without the name, the root is the same answer
- RULE-14: A `.purlin/config.json` that cannot be read is named by the sentence `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`, the cause being `it is not UTF-8 text`, the JSON reader's own message followed by `at line <n>`, `it holds a <list | string | number> where an object belongs`, or the system's own message for an open that failed
- RULE-15: A write while `.purlin/config.json` cannot be read is refused with that sentence, and the file is left byte for byte as it was

## Proof

- PROOF-1 (RULE-1): With `PURLIN_PROJECT_ROOT` naming `<tmp>/chosen`, an existing folder with no `.purlin/` marker, starting from `<tmp>/other/src` under a marker at `<tmp>/other` gives the project root `<tmp>/chosen`
- PROOF-16 (RULE-1): With `PURLIN_PROJECT_ROOT` naming `<tmp>/gone`, which does not exist, and a `.purlin/` marker at `<tmp>/real_project`, starting from `<tmp>/real_project/src` gives the project root `<tmp>/real_project`
- PROOF-17 (RULE-1): With `PURLIN_PROJECT_ROOT` naming `<tmp>/settings.txt`, a file and not a folder, and a `.purlin/` marker at `<tmp>/real_project`, starting from `<tmp>/real_project/src` gives the project root `<tmp>/real_project`
- PROOF-2 (RULE-2): With `PURLIN_PROJECT_ROOT` unset and a `.purlin/` marker in `<tmp>/a` and none below it, starting from `<tmp>/a/b/c` gives the project root `<tmp>/a`
- PROOF-18 (RULE-2): With `PURLIN_PROJECT_ROOT` unset and `.purlin/` markers in both `<tmp>/outer` and `<tmp>/outer/inner`, starting from `<tmp>/outer/inner/src` gives the nearest, `<tmp>/outer/inner`, and not `<tmp>/outer`
- PROOF-3 (RULE-3): With `PURLIN_PROJECT_ROOT` unset, the working directory `<tmp>/work`, and no `.purlin/` marker in or above it or the start folder `<tmp>/bare`, starting from `<tmp>/bare` gives the project root `<tmp>/work`, not the start folder
- PROOF-4 (RULE-4): With the settings file holding `{"team": "default", "shared": {"paths": ["a", "b"]}}`, the config reads as exactly that, the nested value included
- PROOF-7 (RULE-7): With `.purlin/` holding no settings file, the config reads as exactly `{}`
- PROOF-8 (RULE-8): With the settings file holding `{"team": "v1"}`, setting `user_pref` to `dark` leaves it holding exactly `{"team": "v1", "user_pref": "dark"}`, and `.purlin/` holds no other file
- PROOF-24 (RULE-8): With `.purlin/` holding no settings file, setting `new` to true creates `.purlin/config.json` holding exactly `{"new": true}`
- PROOF-12 (RULE-8): With the settings file holding `{"gate": "passed", "version": "0.9.0"}`, setting `gate` to `strong` makes the config read as exactly `{"gate": "strong", "version": "0.9.0"}`
- PROOF-9 (RULE-9): With the settings file holding `{"existing": "keep", "nested": {"list": [1, 2]}}`, setting `added` to `new` leaves it holding exactly `{"existing": "keep", "nested": {"list": [1, 2]}, "added": "new"}`
- PROOF-25 (RULE-9): With the settings file holding `{"existing": "keep", "shade": "old"}`, setting `shade` to `new` leaves it holding exactly `{"existing": "keep", "shade": "new"}`
- PROOF-10 (RULE-10): With the settings file holding `{"key": "old"}`, setting `key` to `val` writes the whole new file, `{"key": "val"}`, as `.purlin/config.json.tmp` and moves it once onto `.purlin/config.json`; afterwards `.purlin/` holds only `config.json`, reading exactly `{"key": "val"}`
- PROOF-26 (RULE-10): With the settings file holding `{"key": "val"}`, a write of `key` as `other` whose move onto the settings file fails stops with that failure's error, and leaves the file reading exactly `{"key": "val"}` and `.purlin/` holding only `config.json`
- PROOF-27 (RULE-10): With the settings file holding `{"key": "val"}`, a write of `key` as `other` that fails partway through writing the new contents, because the disk is full, stops with the error `No space left on device`, and leaves the file reading exactly `{"key": "val"}` and `.purlin/` holding only `config.json`
- PROOF-15 (RULE-13): With `PURLIN_PROJECT_ROOT` unset and a marker at `<tmp>/project/.purlin/`, starting from `<tmp>/project/src` gives `<tmp>/project`, found by `climb`; the root asked for alone is the same `<tmp>/project`
- PROOF-28 (RULE-13): With a marker at `<tmp>/project/.purlin/` and `PURLIN_PROJECT_ROOT` naming `<tmp>/elsewhere`, an existing folder with no marker, starting from `<tmp>/project/src` gives `<tmp>/elsewhere`, found by `env`; the root asked for alone is the same
- PROOF-29 (RULE-13): With a marker at `<tmp>/project/.purlin/` and `PURLIN_PROJECT_ROOT` naming `<tmp>/gone`, which does not exist, starting from `<tmp>/project/src` gives `<tmp>/project`, found by `climb`; the root asked for alone is the same
- PROOF-30 (RULE-13): With `PURLIN_PROJECT_ROOT` unset, the working directory `<tmp>/work` and no marker in or above it or `<tmp>/bare`, starting from `<tmp>/bare` gives `<tmp>/work`, found by `cwd`; the root asked for alone is the same
- PROOF-31 (RULE-13): The ways a project root is found are exactly three, and their sentences read `the PURLIN_PROJECT_ROOT environment variable` for `env`, `climbing from the working directory to a .purlin/ marker` for `climb`, and `the working directory, with no .purlin/ marker in it or above it` for `cwd`
- PROOF-32 (RULE-14): With the settings file holding `{` on one line and `  "gate": "passed",}` on the next, the settings are named as `.purlin/config.json cannot be read: <the JSON reader's message> at line 2. Fix the file by hand; nothing ran and nothing was saved.`
- PROOF-33 (RULE-14): With the settings file holding `{"gate": "` then the byte 0xFF then `"}`, which is not UTF-8, the settings are named as `.purlin/config.json cannot be read: it is not UTF-8 text. Fix the file by hand; nothing ran and nothing was saved.`
- PROOF-34 (RULE-14): With the settings file holding `["gate", "passed"]`, a list, the settings are named as `.purlin/config.json cannot be read: it holds a list where an object belongs. Fix the file by hand; nothing ran and nothing was saved.`
- PROOF-35 (RULE-15): With the settings file holding `{` on one line and `  "gate": "passed",}` on the next, a write of `gate` as `strong` stops with the sentence naming that file as unreadable at line 2, the file is byte for byte as it was, and `.purlin/` holds only `config.json`
