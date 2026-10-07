# Feature: config_engine

> Description: One settings file, `.purlin/config.json`, committed with the
>   project. The resolver reads it whole and the settings tool writes one key
>   into it, atomically. The same module decides where the project root is
>   and names how it found it. The file holds `version`, `tests` and `runs`; the
>   project's name is read from the project's own files each time and never
>   written.
> Scope: scripts/mcp/config_engine.py, scripts/mcp/purlin/project.py
> Stack: python/stdlib, json
> Highest-Rule: 22
> Highest-Proof: 54

## Rules

- RULE-4: The config is `.purlin/config.json` read whole, the one settings file a project has, and with no such file the config is empty
- RULE-8: A write sets one top-level key in `.purlin/config.json`, creating the file when it is absent, and keeps every other key it held
- RULE-10: A write is atomic: the whole file is written beside the target and then moved onto it, so a write that fails at any point leaves the previous contents whole, removes the file it wrote beside the target, and says so
- RULE-14: A `.purlin/config.json` that cannot be read is named by the sentence `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`, and a write while it cannot be read is refused with that sentence, the file left byte for byte as it was
- RULE-19: The project's name is read from the project's own files each time and never written, the first found of: `name` under `[project]`, then under `[tool.poetry]`, in `pyproject.toml`; `name` in `package.json`; the name of the first `*.csproj` file at the root; the last segment of the `origin` remote's URL; the folder's name
- RULE-20: Each key `.purlin/config.json` holds other than `version`, `tests` and `runs` is named in one warning, with `Run purlin:init --update.` where the upgrade has a step for it and `Remove it from the file.` otherwise
- RULE-22: `runs` is a whole number from 1 up, how many times an AI proof's test runs on each model; with no `runs` the settings name no number, and any other value is read as not set and named in one warning
- RULE-21: The project root is `PURLIN_PROJECT_ROOT` when it names a folder that exists, else the nearest ancestor of the start folder holding `.purlin/`, else the working directory, and it comes with the name of how it was found, `env`, `climb` or `cwd`, so a guessed root is never handed back as found

## Proof

- PROOF-4 (RULE-4): With the settings file holding `{"team": "default", "shared": {"paths": ["a", "b"]}}`, the config reads as exactly that, the nested value included
- PROOF-7 (RULE-4): With `.purlin/` holding no settings file, the config reads as exactly `{}`
- PROOF-8 (RULE-8): With the settings file holding `{"team": "v1"}`, setting `user_pref` to `dark` leaves it holding exactly `{"team": "v1", "user_pref": "dark"}`, and `.purlin/` holds no other file
- PROOF-24 (RULE-8): With `.purlin/` holding no settings file, setting `new` to true creates `.purlin/config.json` holding exactly `{"new": true}`
- PROOF-38 (RULE-8): On Windows, with the settings file holding `{"team": "v1"}`, setting `user_pref` to `dark` leaves it holding exactly `{"team": "v1", "user_pref": "dark"}`, its lines ending with no carriage return, and `.purlin/` holds no other file @env(windows)
- PROOF-26 (RULE-10): With the settings file holding `{"key": "val"}`, a write of `key` as `other` whose move onto the settings file fails stops with that failure's error, and leaves the file reading exactly `{"key": "val"}` and `.purlin/` holding only `config.json`
- PROOF-27 (RULE-10): With the settings file holding `{"key": "val"}`, a write of `key` as `other` that fails partway through writing the new contents, because the disk is full, stops with the error `No space left on device`, and leaves the file reading exactly `{"key": "val"}` and `.purlin/` holding only `config.json`
- PROOF-39 (RULE-10): On Windows, with the settings file holding `{"key": "val"}` and held open by another program, a write of `key` as `other` stops with the system's error and leaves the file reading exactly `{"key": "val"}`, and `.purlin/` holding only `config.json` @env(windows)
- PROOF-32 (RULE-14): With the settings file holding `{` on one line and `  "tests": [],}` on the next, the settings are named as `.purlin/config.json cannot be read: <the JSON reader's message> at line 2. Fix the file by hand; nothing ran and nothing was saved.`
- PROOF-33 (RULE-14): With the settings file holding `{"version": "` then the byte 0xFF then `"}`, which is not UTF-8, the settings are named as `.purlin/config.json cannot be read: it is not UTF-8 text. Fix the file by hand; nothing ran and nothing was saved.`
- PROOF-35 (RULE-14): With the settings file holding `{` on one line and `  "tests": [],}` on the next, a write of `tests` as an empty list stops with the sentence naming that file as unreadable at line 2, the file is byte for byte as it was, and `.purlin/` holds only `config.json`
- PROOF-45 (RULE-19): A project whose `pyproject.toml` reads `[project]` and `name = "labconnect"`, beside a `package.json` naming `intake-web`, opens its status `Purlin status: labconnect,`, and its `.purlin/config.json` holds no name
- PROOF-48 (RULE-19): A project in the folder `work`, holding no `pyproject.toml`, `package.json` or `*.csproj`, whose `origin` remote is `/srv/git/labconnect.git`, opens its status `Purlin status: labconnect,`
- PROOF-49 (RULE-19): A project in the folder `labconnect`, holding no `pyproject.toml`, `package.json` or `*.csproj` and no git remote, opens its status `Purlin status: labconnect,`
- PROOF-50 (RULE-20): A settings file holding `version`, `tests`, `pre_push` and `digest`, in that order, is read with exactly the one warning `.purlin/config.json: setting not read. This version does not read pre_push, digest. Run purlin:init --update.`
- PROOF-51 (RULE-20): A settings file holding `version`, `tests` and `colour`, a key the upgrade has no step for, is read with exactly the one warning `.purlin/config.json: setting not read. This version does not read colour. Remove it from the file.`
- PROOF-52 (RULE-22): A settings file holding `version`, `tests` and `"runs": 5` is read with the number of runs `5` and no warning; one holding `version` and `tests` alone is read with no number of runs and no warning
- PROOF-53 (RULE-22): A settings file holding `version`, `tests` and `"runs": 0` is read with no number of runs and exactly the one warning `.purlin/config.json: setting not read. runs is not a whole number from 1 up. Correct it in the file.`
- PROOF-54 (RULE-22): A `runs` of `true`, of `"3"`, of `2.5` and of `-1` is each read as no number of runs, each with that one warning
- PROOF-28 (RULE-21): With a marker at `<tmp>/project/.purlin/` and `PURLIN_PROJECT_ROOT` naming `<tmp>/elsewhere`, an existing folder with no marker, starting from `<tmp>/project/src` gives `<tmp>/elsewhere`, found by `env`; the root asked for alone is the same
- PROOF-18 (RULE-21): With `PURLIN_PROJECT_ROOT` unset and `.purlin/` markers in both `<tmp>/outer` and `<tmp>/outer/inner`, starting from `<tmp>/outer/inner/src` gives the nearest, `<tmp>/outer/inner`, and not `<tmp>/outer`
- PROOF-30 (RULE-21): With `PURLIN_PROJECT_ROOT` unset, the working directory `<tmp>/work` and no marker in or above it or `<tmp>/bare`, starting from `<tmp>/bare` gives `<tmp>/work`, found by `cwd`; the root asked for alone is the same
