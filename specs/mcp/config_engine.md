# Feature: config_engine

> Description: One settings file, `.purlin/config.json`, committed with the
>   project. The resolver reads it whole and the settings tool writes one key
>   into it. The same module decides where the project root is and names how
>   it found it.
> Scope: scripts/mcp/config_engine.py
> Stack: python/stdlib, json

## Rules

- RULE-1: The project root is the `PURLIN_PROJECT_ROOT` environment variable when it names a directory that exists [bar: strong]
- RULE-2: Failing that, the root is found by climbing from the start directory to the nearest ancestor holding a `.purlin/` marker directory [bar: strong]
- RULE-3: Failing both, the root is the working directory [bar: strong]
- RULE-4: The config is `.purlin/config.json` read whole, the one settings file a project has [bar: strong]
- RULE-5: The command line prints the whole config as JSON with `--dump` and one key's value with `--key <name>` [bar: strong]
- RULE-7: With no `config.json` on disk the config is empty [bar: strong]
- RULE-8: A write sets one top-level key in `.purlin/config.json`, the committed file, creating it when it is absent [bar: strong]
- RULE-9: A write preserves every other key `config.json` already held [bar: strong]
- RULE-10: A write is atomic: the whole file is written beside the target and then moved onto it, so an interrupted write leaves the previous contents and no temporary file behind [bar: strong]
- RULE-13: `resolve_project_root` returns the root together with the name of how it was found, and is the one implementation of the precedence RULE-1 to RULE-3 describe: the three names are `env`, `climb` and `cwd`, each mapped to the sentence a report prints for it, so the last case is named as the guess it is rather than handed back as a path indistinguishable from a marker that was found. `find_project_root` is the same answer with the name dropped, and nothing recomputes the precedence for itself [bar: strong]

## Proof

- PROOF-1 (RULE-1): With `PURLIN_PROJECT_ROOT` naming a folder that holds `.purlin/`, the project root is that folder. With it naming a path that does not exist, and a `.purlin/` marker at `<tmp>/real_project`, starting from `<tmp>/real_project/src` gives `<tmp>/real_project`, never the missing path
- PROOF-2 (RULE-2): With a `.purlin/` marker in `<tmp>/a`, starting from `<tmp>/a/b/c` gives the project root `<tmp>/a`
- PROOF-3 (RULE-3): Starting from a folder with no `.purlin/` marker in it or above it gives the working directory as the project root
- PROOF-4 (RULE-4): A settings file holding `{"team": "default", "shared": "base"}` reads back as exactly that, and `--dump` prints exactly that
- PROOF-5 (RULE-5): With the settings file holding `{"version": "0.9.0"}`, `--key version` exits 0 and prints exactly `0.9.0`, whether run as its own process or in the caller's
- PROOF-7 (RULE-7): With no settings file on disk, the settings read back as exactly `{}`
- PROOF-8 (RULE-8): With the settings file holding `{"team": "v1"}`, setting `user_pref` to `dark` leaves it holding exactly `{"team": "v1", "user_pref": "dark"}`, and `.purlin/` holds no other file. With no settings file, setting `new` to true creates one holding exactly `{"new": true}`
- PROOF-9 (RULE-9): With the settings file holding `{"existing": "keep", "shade": "old"}`, setting `added` to `new` and then `shade` to `new` leaves it holding exactly `{"existing": "keep", "shade": "new", "added": "new"}`
- PROOF-10 (RULE-10): Setting `key` to `val` leaves the settings file with `key` reading `val` and no temporary file beside it. With the file holding `{"key": "val"}`, a write of `other` interrupted at the moment it replaces the file leaves the file reading exactly `{"key": "val"}`, and no temporary file
- PROOF-12 (RULE-8): With the settings file holding `{"digest": "auto", "version": "0.9.0"}`, setting `digest` to `off` reads back as exactly `{"digest": "off", "version": "0.9.0"}`
- PROOF-15 (RULE-13): With a marker at `<tmp>/project/.purlin/` and `PURLIN_PROJECT_ROOT` unset, starting from `<tmp>/project/src` gives `<tmp>/project`, found by `climb`. With the variable naming `<tmp>/elsewhere`, a folder that exists and holds no marker, the answer is `<tmp>/elsewhere`, found by `env`. With it naming a path that does not exist, the answer is the climb's again. With it unset and no marker in or above the start, the answer is the working directory, found by `cwd`, and the sentence for `cwd` names the `working directory` and the `marker`. The ways a root is found are exactly `climb`, `cwd` and `env`, each with a sentence of its own, and the root alone, asked for without the way, is the same in all four cases
