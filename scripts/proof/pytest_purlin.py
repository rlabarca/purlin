"""Purlin proof plugin for pytest.

Collects @pytest.mark.proof markers and emits feature-scoped proof JSON files
next to the corresponding spec files.

Usage in tests:
    @pytest.mark.proof("my_feature", "PROOF-1", "RULE-1")
    def test_something():
        assert ...

    @pytest.mark.proof("my_feature", "PROOF-2", "RULE-2", tier="slow")
    def test_slow_thing():
        assert ...
"""

import glob
import json
import os

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        'proof(feature, proof_id, rule_id, *, tier="default"): mark test as proof for a spec rule',
    )
    collector = ProofCollector()
    config.pluginmanager.register(collector, "purlin_proof")


class ProofCollector:
    def __init__(self):
        self.proofs = {}  # keyed by (feature, tier)

    def pytest_runtest_makereport(self, item, call):
        if call.when != "call":
            return
        for marker in item.iter_markers("proof"):
            if len(marker.args) < 3:
                continue
            feature = marker.args[0]
            proof_id = marker.args[1]
            rule_id = marker.args[2]
            tier = marker.kwargs.get("tier", "default")
            key = (feature, tier)
            self.proofs.setdefault(key, []).append(
                {
                    "feature": feature,
                    "id": proof_id,
                    "rule": rule_id,
                    "test_file": str(item.fspath.relto(item.config.rootdir)),
                    "test_name": item.name,
                    "status": "pass" if call.excinfo is None else "fail",
                    "tier": tier,
                }
            )

    def pytest_sessionfinish(self, session):
        if not self.proofs:
            return

        # Build feature -> spec directory mapping
        spec_dirs = {}
        for spec in glob.glob("specs/**/*.md", recursive=True):
            stem = os.path.splitext(os.path.basename(spec))[0]
            spec_dirs[stem] = os.path.dirname(spec)

        for (feature, tier), new_entries in self.proofs.items():
            spec_dir = spec_dirs.get(feature, "specs")
            path = os.path.join(spec_dir, f"{feature}.proofs-{tier}.json")

            # Load existing file for this feature+tier
            existing = []
            if os.path.exists(path):
                with open(path) as f:
                    existing = json.load(f).get("proofs", [])

            # Purge this feature's old entries (kills ghosts), keep others
            kept = [e for e in existing if e.get("feature") != feature]

            # Write fresh entries
            with open(path, "w") as f:
                json.dump({"tier": tier, "proofs": kept + new_entries}, f, indent=2)
                f.write("\n")
