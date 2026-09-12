"""Purlin proof plugin for pytest.

Collects @pytest.mark.proof markers and emits write-scoped proof JSON files
next to the corresponding spec files.

Usage in tests:
    @pytest.mark.proof("my_feature", "PROOF-1", "RULE-1")
    def test_something():
        assert ...

    @pytest.mark.proof("my_feature", "PROOF-2", "RULE-2", tier="integration")
    def test_integration_thing():
        assert ...

    @pytest.mark.proof("my_feature", "PROOF-3", "RULE-3", platforms=("windows-2022",))
    def test_platform_specific_thing():
        assert ...

A marker that declares `platforms=` (a tuple of platform ids, or one id as a
bare string) writes its entry to `<feature>.proofs-<tier>@<host>.json`, where
`<host>` is `PURLIN_PLATFORM` when set and otherwise the detected OS family
(`windows`, `macos`, `linux`). Every entry in that file carries an eighth
field, `platform`, equal to `<host>`. A marker with no `platforms=` writes the
agnostic `<feature>.proofs-<tier>.json` with the seven standard fields,
whatever `PURLIN_PLATFORM` says. The plugin never evaluates version
constraints: the ids a marker declares are recorded by the spec, not here.
"""

import glob
import json
import os
import platform

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        'proof(feature, proof_id, rule_id, *, tier="unit", platforms=()): mark test as proof for a spec rule',
    )
    collector = ProofCollector()
    config.pluginmanager.register(collector, "purlin_proof")


_FAMILIES = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}


def _host_platform():
    """The platform id this run's scoped files are named after.

    `PURLIN_PLATFORM` names a registry id (a runner sets it); with no env the
    OS family stands in. This is the only place a proof plugin looks at the
    host: nothing else in the plugin branches on the operating system.
    """
    env = os.environ.get("PURLIN_PLATFORM", "").strip()
    if env:
        return env
    system = platform.system()
    return _FAMILIES.get(system, system.lower())


def _declared_platforms(marker):
    raw = marker.kwargs.get("platforms")
    if not raw:
        return ()
    if isinstance(raw, str):
        raw = (raw,)
    return tuple(p.strip() for p in raw if p and p.strip())


class ProofCollector:
    def __init__(self):
        self.proofs = {}  # keyed by (feature, tier, platform); platform is None when agnostic
        # (feature, id, test_file) for every marked test this run skipped, so an
        # existing entry for it survives the write-scoped overwrite instead of
        # being reaped by a sibling test in the same file (proof_common RULE-18).
        self.skipped = set()

    def pytest_runtest_makereport(self, item, call):
        # A skip surfaces as a Skipped exception: raised during setup by a
        # `skip`/`skipif` marker or a fixture, and during the call phase by a
        # `pytest.skip()` inside the test body. Both are the skip signal
        # proof_common RULE-18 asks a capable plugin to observe.
        if call.when not in ("setup", "call"):
            return
        was_skipped = call.excinfo is not None and call.excinfo.errisinstance(
            pytest.skip.Exception
        )
        if call.when == "setup" and not was_skipped:
            return
        for marker in item.iter_markers("proof"):
            if len(marker.args) < 3:
                continue
            feature = marker.args[0]
            proof_id = marker.args[1]
            rule_id = marker.args[2]
            tier = marker.kwargs.get("tier", "unit")
            # Project-relative with `/` separators on every OS (proof_common
            # RULE-15): a backslash is never written into a proof file.
            test_file = str(item.fspath.relto(item.config.rootdir)).replace(os.sep, "/").replace("\\", "/")
            if was_skipped:
                # proof_common RULE-13: a skipped test emits no entry at all.
                # RULE-18: and the entry it would have written is kept.
                self.skipped.add((feature, proof_id, test_file))
                continue
            plat = _host_platform() if _declared_platforms(marker) else None
            key = (feature, tier, plat)
            entry = {
                "feature": feature,
                "id": proof_id,
                "rule": rule_id,
                "test_file": test_file,
                "test_name": item.name,
                "status": "pass" if call.excinfo is None else "fail",
                "tier": tier,
            }
            if plat is not None:
                entry["platform"] = plat
            self.proofs.setdefault(key, []).append(entry)

    def pytest_sessionfinish(self, session):
        if not self.proofs:
            return

        # Build feature -> spec directory mapping
        spec_dirs = {}
        for spec in glob.glob("specs/**/*.md", recursive=True):
            stem = os.path.splitext(os.path.basename(spec))[0]
            spec_dirs[stem] = os.path.dirname(spec)

        for (feature, tier, plat), new_entries in self.proofs.items():
            suffix = f"{tier}@{plat}" if plat is not None else tier
            spec_dir = spec_dirs.get(feature)
            if spec_dir is None:
                import sys
                print(f'WARNING: No spec found for feature "{feature}" — writing proofs to specs/{feature}.proofs-{suffix}.json. Create a spec with: purlin:spec {feature}', file=sys.stderr)
                spec_dir = "specs"
            path = os.path.join(spec_dir, f"{feature}.proofs-{suffix}.json")

            # Load existing file for this feature+tier(+platform)
            existing = []
            if os.path.exists(path):
                with open(path) as f:
                    existing = json.load(f).get("proofs", [])

            # Write-scoped overwrite keyed by (feature, tier, platform, test_file), per
            # proof_common RULE-4. The tier and platform are carried by the file being
            # written, so within it the key is (feature, test_file). Keep other features
            # untouched; keep this feature's entries from test files this run did not
            # execute, so two files covering one (feature, tier, platform) can run in
            # any order; reap entries whose test file is gone (RULE-11). The existence
            # check is relative to cwd, which the spec glob above already assumes is
            # the repo root. If it is not, every path misses and the merge degrades to
            # the older feature-wide purge, never to something wider.
            run_files = {e["test_file"] for e in new_entries}
            # What this run wrote, so a skipped test's protection never keeps an
            # entry the run has just replaced (proof_common RULE-18: only an
            # executed test replaces its entry).
            run_wrote = {(e["id"], e["test_file"], e["test_name"]) for e in new_entries}

            def _keep(e):
                if e.get("feature") != feature:
                    return True
                test_file = e.get("test_file") or ""
                if not os.path.exists(test_file):
                    return False
                if test_file not in run_files:
                    return True
                # The file ran. RULE-18: an entry whose test the run skipped is
                # kept with its old status, unless this run wrote it afresh.
                return (
                    (feature, e.get("id"), test_file) in self.skipped
                    and (e.get("id"), test_file, e.get("test_name")) not in run_wrote
                )

            kept = [e for e in existing if _keep(e)]

            payload = {"tier": tier}
            if plat is not None:
                payload["platform"] = plat
            payload["proofs"] = kept + new_entries

            # Write fresh entries (atomic: tmp + rename)
            tmp_path = path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(payload, f, indent=2)
                f.write("\n")
            os.replace(tmp_path, path)
