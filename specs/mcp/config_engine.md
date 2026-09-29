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
- RULE-5: The command line prints the whole config as JSON with `--dump`, and with `--key <name>` one key's value, or an empty line when the config holds no such key; any other use prints nothing to standard output, prints its usage or the argument it does not know to standard error, and exits 1
- RULE-7: With no `config.json` on disk the config is empty
- RULE-8: A write sets one top-level key in `.purlin/config.json`, the committed file, creating it when it is absent
- RULE-9: A write preserves every other key `config.json` already held
- RULE-10: A write is atomic: the whole file is written beside the target and then moved onto it, so a write that fails at any point leaves the previous contents whole and removes the file it wrote beside the target
- RULE-13: The project root comes with the name of how it was found, `env`, `climb` or `cwd`, by the precedence RULE-1 to RULE-3 describe, each name with the sentence a report prints for it, so a root that is only the working directory is named as that guess and not handed back as if a marker were found. Asked for alone, without the name, the root is the same answer

## Proof

- PROOF-1 (RULE-1): With `PURLIN_PROJECT_ROOT` naming `<tmp>/chosen`, an existing folder with no `.purlin/` marker, starting from `<tmp>/other/src` under a marker at `<tmp>/other` gives the project root `<tmp>/chosen`
- PROOF-16 (RULE-1): With `PURLIN_PROJECT_ROOT` naming `<tmp>/gone`, which does not exist, and a `.purlin/` marker at `<tmp>/real_project`, starting from `<tmp>/real_project/src` gives the project root `<tmp>/real_project`
- PROOF-17 (RULE-1): With `PURLIN_PROJECT_ROOT` naming `<tmp>/settings.txt`, a file and not a folder, and a `.purlin/` marker at `<tmp>/real_project`, starting from `<tmp>/real_project/src` gives the project root `<tmp>/real_project`
- PROOF-2 (RULE-2): With `PURLIN_PROJECT_ROOT` unset and a `.purlin/` marker in `<tmp>/a` and none below it, starting from `<tmp>/a/b/c` gives the project root `<tmp>/a`
- PROOF-18 (RULE-2): With `PURLIN_PROJECT_ROOT` unset and `.purlin/` markers in both `<tmp>/outer` and `<tmp>/outer/inner`, starting from `<tmp>/outer/inner/src` gives the nearest, `<tmp>/outer/inner`, and not `<tmp>/outer`
- PROOF-3 (RULE-3): With `PURLIN_PROJECT_ROOT` unset, the working directory `<tmp>/work`, and no `.purlin/` marker in or above it or the start folder `<tmp>/bare`, starting from `<tmp>/bare` gives the project root `<tmp>/work`, not the start folder
- PROOF-4 (RULE-4): With the settings file holding `{"team": "default", "shared": {"paths": ["a", "b"]}}`, the config reads as exactly that, the nested value included
- PROOF-5 (RULE-5): With the settings file holding `{"version": "0.9.0"}`, the command line run with `--key version` exits 0 and prints exactly `0.9.0`
- PROOF-19 (RULE-5): With the settings file holding `{"team": "default", "shared": "base"}`, the command line run with `--dump` exits 0 and prints JSON reading exactly `{"team": "default", "shared": "base"}`
- PROOF-20 (RULE-5): With the settings file holding `{"version": "0.9.0"}`, the command line run with `--key missing` exits 0 and prints one empty line
- PROOF-21 (RULE-5): The command line run with no argument exits 1, prints nothing to standard output, and prints `Usage: config_engine.py [--dump | --key <name>]` to standard error
- PROOF-22 (RULE-5): The command line run with `--key` and no name exits 1, prints nothing to standard output, and prints `Usage: config_engine.py --key <name>` to standard error
- PROOF-23 (RULE-5): The command line run with `--show` exits 1, prints nothing to standard output, and prints `Unknown argument: --show` to standard error
- PROOF-7 (RULE-7): With `.purlin/` holding no settings file, the config reads as exactly `{}`
- PROOF-8 (RULE-8): With the settings file holding `{"team": "v1"}`, setting `user_pref` to `dark` leaves it holding exactly `{"team": "v1", "user_pref": "dark"}`, and `.purlin/` holds no other file
- PROOF-24 (RULE-8): With `.purlin/` holding no settings file, setting `new` to true creates `.purlin/config.json` holding exactly `{"new": true}`
- PROOF-12 (RULE-8): With the settings file holding `{"gate": "passed", "version": "0.9.0"}`, setting `gate` to `strong` makes the config read as exactly `{"gate": "strong", "version": "0.9.0"}`
- PROOF-9 (RULE-9): With the settings file holding `{"existing": "keep", "nested": {"list": [1, 2]}}`, setting `added` to `new` leaves it holding exactly `{"existing": "keep", "nested": {"list": [1, 2]}, "added": "new"}`
- PROOF-25 (RULE-9): With the settings file holding `{"existing": "keep", "shade": "old"}`, setting `shade` to `new` leaves it holding exactly `{"existing": "keep", "shade": "new"}`
- PROOF-10 (RULE-10): With the settings file holding `{"key": "old"}`, setting `key` to `val` writes the whole new file, `{"key": "val"}`, as `.purlin/config.json.tmp` and moves it once onto `.purlin/config.json`; afterwards `.purlin/` holds only `config.json`, reading exactly `{"key": "val"}`
- PROOF-26 (RULE-10): With the settings file holding `{"key": "val"}`, a write of `key` as `other` whose move onto the settings file fails leaves it reading exactly `{"key": "val"}`, and `.purlin/` holding only `config.json`
- PROOF-27 (RULE-10): With the settings file holding `{"key": "val"}`, a write of `key` as `other` that fails partway through writing the new contents, because the disk is full, leaves it reading exactly `{"key": "val"}`, and `.purlin/` holding only `config.json`
- PROOF-15 (RULE-13): With `PURLIN_PROJECT_ROOT` unset and a marker at `<tmp>/project/.purlin/`, starting from `<tmp>/project/src` gives `<tmp>/project`, found by `climb`; the root asked for alone is the same `<tmp>/project`
- PROOF-28 (RULE-13): With a marker at `<tmp>/project/.purlin/` and `PURLIN_PROJECT_ROOT` naming `<tmp>/elsewhere`, an existing folder with no marker, starting from `<tmp>/project/src` gives `<tmp>/elsewhere`, found by `env`; the root asked for alone is the same
- PROOF-29 (RULE-13): With a marker at `<tmp>/project/.purlin/` and `PURLIN_PROJECT_ROOT` naming `<tmp>/gone`, which does not exist, starting from `<tmp>/project/src` gives `<tmp>/project`, found by `climb`; the root asked for alone is the same
- PROOF-30 (RULE-13): With `PURLIN_PROJECT_ROOT` unset, the working directory `<tmp>/work` and no marker in or above it or `<tmp>/bare`, starting from `<tmp>/bare` gives `<tmp>/work`, found by `cwd`; the root asked for alone is the same
- PROOF-31 (RULE-13): The ways a project root is found are exactly three, and their sentences read `the PURLIN_PROJECT_ROOT environment variable` for `env`, `climbing from the working directory to a .purlin/ marker` for `climb`, and `the working directory, with no .purlin/ marker in it or above it` for `cwd`
