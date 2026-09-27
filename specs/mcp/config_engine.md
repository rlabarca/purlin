# Feature: config_engine

> Description: One settings file, `.purlin/config.json`, committed with the
>   project. The resolver reads it whole and the settings tool writes one key
>   into it. The same module decides where the project root is and names how
>   it found it.
> Scope: scripts/mcp/config_engine.py
> Stack: python/stdlib, json

## Rules

- RULE-1: The project root is the `PURLIN_PROJECT_ROOT` environment variable when it names a directory that exists [bar: strong] [origin: eng]
- RULE-2: Failing that, the root is found by climbing from the start directory to the nearest ancestor holding a `.purlin/` marker directory [bar: strong] [origin: eng]
- RULE-3: Failing both, the root is the working directory [bar: strong] [origin: eng]
- RULE-4: The config is `.purlin/config.json` read whole, the one settings file a project has [bar: strong] [origin: eng]
- RULE-5: The command line prints the whole config as JSON with `--dump` and one key's value with `--key <name>` [bar: strong] [origin: eng]
- RULE-7: With no `config.json` on disk the config is empty [bar: strong] [origin: eng]
- RULE-8: A write sets one top-level key in `.purlin/config.json`, the committed file, creating it when it is absent [bar: strong] [origin: eng]
- RULE-9: A write preserves every other key `config.json` already held [bar: strong] [origin: eng]
- RULE-10: A write is atomic: the whole file is written beside the target and then moved onto it, so an interrupted write leaves the previous contents and no temporary file behind [bar: strong] [origin: eng]
- RULE-13: `resolve_project_root` returns the root together with the name of how it was found, and is the one implementation of the precedence RULE-1 to RULE-3 describe: the three names are `env`, `climb` and `cwd`, each mapped to the sentence a report prints for it, so the last case is named as the guess it is rather than handed back as a path indistinguishable from a marker that was found. `find_project_root` is the same answer with the name dropped, and nothing recomputes the precedence for itself [bar: strong] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Set `PURLIN_PROJECT_ROOT` to a temporary directory holding `.purlin/` and call for the project root; verify it returns exactly that directory without climbing. Then set the variable to a path that was never created, put a real `.purlin/` marker at `<tmp>/real_project`, and call with the start directory `<tmp>/real_project/src`; verify the answer is `<tmp>/real_project` and never the path that does not exist
- PROOF-2 (RULE-2): Create `<tmp>/a/b/c` with a `.purlin/` marker in `<tmp>/a`; call for the project root with the start directory `<tmp>/a/b/c` and verify it returns `<tmp>/a`
- PROOF-3 (RULE-3): Call for the project root from a directory with no `.purlin/` marker in it or in any ancestor; verify it returns the working directory
- PROOF-4 (RULE-4): Write `config.json` holding `{"team": "default", "shared": "base"}`; resolve the config and verify the result is exactly that dict, and that `--dump` run in the process prints the same dict
- PROOF-5 (RULE-5): Write `config.json` holding `{"version": "0.9.0"}`; run the command line with `--key version` both as a child process and in the process, and verify each exits 0 and prints exactly `0.9.0`
- PROOF-7 (RULE-7): Call the config resolver in a directory holding no `config.json`; verify the result is exactly `{}`
- PROOF-8 (RULE-8): Write `config.json` holding `{"team": "v1"}`, then set the key `user_pref` to `dark`; verify `config.json` holds exactly `{"team": "v1", "user_pref": "dark"}` and that `.purlin/` holds no other file. With no `config.json`, set the key `new` to true and verify the file is created holding exactly `{"new": true}`
- PROOF-9 (RULE-9): Write `config.json` holding `{"existing": "keep", "shade": "old"}`, then set the key `added` to `new` and the key `shade` to `new`; verify the file holds exactly `{"existing": "keep", "shade": "new", "added": "new"}`
- PROOF-10 (RULE-10): Wrap the atomic move in a recording spy and set the key `key` to `val`; verify the spy saw at least 1 call, that the last call's source ends in `.tmp` and its destination is `config.json`, that the file on disk parses to `{"key": "val"}` and that no temporary file remains. Then, with the file already holding `{"key": "val"}`, patch the move to raise `OSError` and set the same key to `other`; verify the file still parses to exactly `{"key": "val"}` and no temporary file is left
- PROOF-12 (RULE-8): Write `config.json` holding `{"digest": "auto", "version": "0.9.0"}` and set the key `digest` to `off`; verify the resolved config is exactly `{"digest": "off", "version": "0.9.0"}`
- PROOF-15 (RULE-13): In a temporary tree holding `<tmp>/project/.purlin/` and `<tmp>/project/src/`, with `PURLIN_PROJECT_ROOT` unset, resolve the root from `<tmp>/project/src` and verify the pair is exactly `<tmp>/project` with the name `climb`. Set the variable to `<tmp>/elsewhere`, created and holding no marker, and verify the same call returns `<tmp>/elsewhere` named `env`. Point the variable at a path that is never created and verify the answer is the climb answer again. Unset it and resolve from a created directory with no marker in it or above it; verify the name is `cwd`, the root is the absolute working directory, that the sentence for `cwd` carries the words `working directory` and `marker`, and that the three names are exactly `climb`, `cwd` and `env` with every sentence a non-empty string. For each of those four cases verify the root-only entry point returns the same root
