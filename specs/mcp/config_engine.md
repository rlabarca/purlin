# Feature: config_engine

> Description: Two-file configuration that separates shared team defaults
>   (`config.json`, committed) from per-user overrides (`config.local.json`,
>   gitignored). Resolution merges both files so a plugin update stays visible
>   while a local preference still wins. The same module decides where the
>   project root is and names how it found it.
> Scope: scripts/mcp/config_engine.py
> Stack: python/stdlib, json

## Rules

- RULE-1: The project root is the `PURLIN_PROJECT_ROOT` environment variable when it names a directory that exists [risk: high] [origin: eng]
- RULE-2: Failing that, the root is found by climbing from the start directory to the nearest ancestor holding a `.purlin/` marker directory [risk: high] [origin: eng]
- RULE-3: Failing both, the root is the working directory [risk: medium] [origin: eng]
- RULE-4: The merged config is `config.json` with `config.local.json` laid over it: a local key wins where both name it, a base key survives where the local file does not, and a key only the local file names is included [risk: high] [origin: eng]
- RULE-5: With no `config.local.json` on disk the merged config is `config.json` alone, and nothing creates the local file [risk: medium] [origin: eng]
- RULE-6: A `config.local.json` holding invalid JSON is ignored with a warning on stderr, and `config.json` alone is returned [risk: high] [origin: eng]
- RULE-7: With neither file on disk the merged config is empty [risk: medium] [origin: eng]
- RULE-8: A write reaches `config.local.json` and never `config.json`, which belongs to `purlin:init` and to version control [risk: high] [origin: eng]
- RULE-9: A write preserves every key `config.local.json` already held [risk: medium] [origin: eng]
- RULE-10: A write is atomic: the whole file is written beside the target and then moved onto it, so an interrupted write leaves the previous contents and no temporary file behind [risk: high] [origin: eng]
- RULE-11: The overlay is per top-level key. A nested object in `config.local.json` replaces the base object of the same name rather than merging into it, because a write sets a whole top-level value and a second merge rule would make what the user wrote and what the server read differ [risk: high] [origin: eng]
- RULE-13: `resolve_project_root` returns the root together with the name of how it was found, and is the one implementation of the precedence RULE-1 to RULE-3 describe: the three names are `env`, `climb` and `cwd`, each mapped to the sentence a report prints for it, so the last case is named as the guess it is rather than handed back as a path indistinguishable from a marker that was found. `find_project_root` is the same answer with the name dropped, and nothing recomputes the precedence for itself [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Set `PURLIN_PROJECT_ROOT` to a temporary directory holding `.purlin/` and call for the project root; verify it returns exactly that directory without climbing. Then set the variable to a path that was never created, put a real `.purlin/` marker at `<tmp>/real_project`, and call with the start directory `<tmp>/real_project/src`; verify the answer is `<tmp>/real_project` and never the path that does not exist
- PROOF-2 (RULE-2): Create `<tmp>/a/b/c` with a `.purlin/` marker in `<tmp>/a`; call for the project root with the start directory `<tmp>/a/b/c` and verify it returns `<tmp>/a`
- PROOF-3 (RULE-3): Call for the project root from a directory with no `.purlin/` marker in it or in any ancestor; verify it returns the working directory
- PROOF-4 (RULE-4): Write `config.json` holding `{"team": "default", "shared": "base"}` and `config.local.json` holding `{"shared": "override", "local_only": true}`; resolve the config and verify the result is exactly `{"team": "default", "shared": "override", "local_only": true}`
- PROOF-5 (RULE-5): Write `config.json` holding `{"key": "val"}` and no local file; resolve the config and verify it returns `{"key": "val"}` and that `config.local.json` was not created
- PROOF-6 (RULE-6): Write a `config.local.json` holding invalid JSON beside a `config.json` holding `{"key": "fallback"}`; resolve the config and verify it returns `{"key": "fallback"}` and that stderr carries a warning naming the malformed file
- PROOF-7 (RULE-7): Call the config resolver in a directory holding neither file; verify the result is exactly `{}`
- PROOF-8 (RULE-8): Write `config.json` holding `{"team": "v1"}`, then set the key `user_pref` to `dark`; verify `config.json` still holds `{"team": "v1"}` unchanged and that `config.local.json` holds `{"user_pref": "dark"}`
- PROOF-9 (RULE-9): Write `config.local.json` holding `{"existing": "keep"}`, then set the key `added` to `new`; verify the local file holds both `{"existing": "keep", "added": "new"}`
- PROOF-10 (RULE-10): Wrap the atomic move in a recording spy and set the key `key` to `val`; verify the spy recorded at least 1 call, that the last call's source ends in `.tmp` and its destination is `config.local.json`, that the file on disk parses to `{"key": "val"}` and that no temporary file remains. Then, with the local file already holding `{"key": "val"}`, patch the move to raise `OSError` and set the same key to `other`; verify the file still parses to exactly `{"key": "val"}` and no temporary file is left
- PROOF-11 (RULE-4): Write `config.json` holding `{"digest": "auto", "version": "0.9.0"}` and `config.local.json` holding `{"pre_push": "strict"}`; resolve the config and verify all 3 keys are present, so a new framework default stays visible through an existing local override
- PROOF-12 (RULE-8): Set the key `digest` to `off`; verify `config.json` is untouched, that `config.local.json` now holds `"digest": "off"`, and that the merged config reads `off`
- PROOF-13 (RULE-11): Write `config.json` whose `runners` object holds the two entries `win-2022` and `mac-14`, and `config.local.json` whose `runners` object holds only `ubuntu-24`; resolve the config and verify `runners` is exactly the one `ubuntu-24` entry with neither base entry present, so a deep merge that kept either one fails
- PROOF-15 (RULE-13): In a temporary tree holding `<tmp>/project/.purlin/` and `<tmp>/project/src/`, with `PURLIN_PROJECT_ROOT` unset, resolve the root from `<tmp>/project/src` and verify the pair is exactly `<tmp>/project` with the name `climb`. Set the variable to `<tmp>/elsewhere`, created and holding no marker, and verify the same call returns `<tmp>/elsewhere` named `env`. Point the variable at a path that is never created and verify the answer is the climb answer again. Unset it and resolve from a created directory with no marker in it or above it; verify the name is `cwd`, the root is the absolute working directory, that the sentence for `cwd` carries the words `working directory` and `marker`, and that the three names are exactly `climb`, `cwd` and `env` with every sentence a non-empty string. For each of those four cases verify the root-only entry point returns the same root
