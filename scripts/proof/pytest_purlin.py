"""Purlin proof plugin for pytest.

The plugin reads `@pytest.mark.proof` markers during a run and writes what it
observed to `.purlin/runtime/proofs/<feature>.<tier>.json`. Proof files are
runtime: they are gitignored, so two runs on two branches never conflict and
nothing about a run is committed. The record `purlin:verify` writes is what
says where a run happened, and it says it once per run.

Usage in tests:

    @pytest.mark.proof("my_feature", "PROOF-1", "RULE-1")
    def test_something():
        assert login("alice", "secret") == 200

    @pytest.mark.proof("my_feature", "PROOF-2", "RULE-2", tier="integration")
    def test_integration_thing():
        assert ...

The operating system a proof must be proved on is a property of the spec, not
of the test: write `@env(windows)`, `@env(macos)` or `@env(linux)` on the
proof line. The retired `platforms=` keyword is refused rather than ignored,
so a test carrying one fails the run with a line saying what to write instead.

The project root is the nearest ancestor of the working directory holding
`specs/` or `.purlin/`, and every recorded `test_file` is relative to it with
`/` separators on every operating system, so a run started from a
subdirectory writes into the project's own tree rather than a second one
beside it.

A run that saw markers and wrote no entry at all fails: it exits non-zero
with one line naming the features whose evidence went missing. Silence there
would leave a reader with a stale proof file and no way to tell.
"""

import json
import os

import pytest


# The three tiers a proof marker can name. Each is registered as a pytest
# marker of its own so that `-m` can select on it: a caller asking for
# `-m "not integration and not e2e"` gets the unit-tier proofs and nothing
# else, without every test file having to carry a second hand-written marker.
_TIERS = ("unit", "integration", "e2e")

PROOF_DIR = os.path.join(".purlin", "runtime", "proofs")

# The retired keyword and what replaced it. A marker that still carries it is
# an error rather than a silent no-op: the test would otherwise look proved
# on a host that cannot prove it.
_RETIRED_KWARG = "platforms"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        'proof(feature, proof_id, rule_id, *, tier="unit"): mark test as proof '
        "for a spec rule",
    )
    for tier in _TIERS:
        config.addinivalue_line(
            "markers",
            "%s: proof tier, added to every test whose proof marker names it"
            % tier,
        )
    collector = ProofCollector()
    config.pluginmanager.register(collector, "purlin_proof")


# ── The project root ────────────────────────────────────────────────────────
# Everything the plugin addresses by a project-relative path is rooted here and
# not at the working directory, so a run started from a subdirectory writes
# into the project's own tree instead of making a second one beside itself.


def _find_root(start):
    """The nearest ancestor of `start`, `start` itself included, that holds a
    `specs/` or a `.purlin/` directory; None when none does."""
    d = os.path.realpath(start)
    while True:
        if (os.path.isdir(os.path.join(d, "specs"))
                or os.path.isdir(os.path.join(d, ".purlin"))):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def _project_root(start=None):
    """The project root of `start` (the working directory by default): the
    nearest ancestor holding `specs/` or `.purlin/`, and `start` itself when
    no ancestor holds either."""
    start = os.path.realpath(start or os.getcwd())
    return _find_root(start) or start


def _relativize(root, path):
    """`path` recorded relative to `root` with `/` separators.

    Whatever shape the framework handed over is resolved against the working
    directory first, so an absolute path and a relative one naming the same
    file record the same value: under the merge key a difference does not
    collapse, it accumulates as a second entry for one proof. A file outside
    `root` is made relative to the nearest project root above the file itself,
    and left absolute when there is none, rather than rewritten with `../`
    segments.
    """
    if not path:
        return path
    abs_path = os.path.realpath(path)
    for base in (root, _find_root(os.path.dirname(abs_path))):
        if not base:
            continue
        try:
            rel = os.path.relpath(abs_path, base)
        except ValueError:
            continue
        if rel != os.pardir and not rel.startswith(os.pardir + os.sep):
            return rel.replace(os.sep, "/").replace("\\", "/")
    return abs_path.replace(os.sep, "/").replace("\\", "/")


def _entry_order(entry):
    """The sort key of a proof file's entries.

    `(id, test_file, test_name)` under plain ordinal string comparison,
    applied after the merge and right before serialization, so two runs of the
    same tests in any collection order write byte-identical files.
    """
    return (entry.get("id") or "", entry.get("test_file") or "",
            entry.get("test_name") or "")


class ProofCollector:
    def __init__(self):
        # Resolved once, from the working directory pytest was started in, and
        # used for the existence check and every recorded `test_file`.
        self.root = _project_root()
        self.proofs = {}   # keyed by (feature, tier)
        # (feature, id, test_file) for every marked test this run skipped, so
        # an existing entry for it survives the write-scoped overwrite instead
        # of being reaped by a sibling test in the same file.
        self.skipped = set()
        # Every feature a marker named, whether or not it produced an entry.
        # A run that saw markers and wrote nothing is a failure, not silence.
        self.seen_features = set()
        # Markers carrying the retired `platforms=` keyword, named in the one
        # line the run fails with.
        self.retired = []

    def pytest_collection_modifyitems(self, config, items):
        """Give every marked test the pytest marker its proof tier names.

        The tier already decides which proof file the entry lands in; adding
        it as a marker as well makes it selectable with `-m`, so a fast arm
        can deselect the slow tiers. The marker is added, never substituted:
        whatever markers the test already carries stay, and a test whose proof
        markers name two tiers gets both. A tier outside `_TIERS` is added
        under its own name verbatim rather than dropped or rewritten, so the
        plugin never silently renames a caller's tier.
        """
        for item in items:
            for marker in item.iter_markers("proof"):
                if len(marker.args) < 3:
                    continue
                item.add_marker(marker.kwargs.get("tier", "unit"))

    def pytest_runtest_makereport(self, item, call):
        # A skip surfaces as a Skipped exception: raised during setup by a
        # `skip`/`skipif` marker or a fixture, and during the call phase by a
        # `pytest.skip()` inside the test body.
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
            test_file = _relativize(self.root, str(item.fspath))
            self.seen_features.add(feature)
            if _RETIRED_KWARG in marker.kwargs:
                self.retired.append((feature, proof_id, item.name))
                continue
            if was_skipped:
                # A skipped test emits no entry at all, and the entry it would
                # have written is kept.
                self.skipped.add((feature, proof_id, test_file))
                continue
            key = (feature, tier)
            self.proofs.setdefault(key, []).append({
                "feature": feature,
                "id": proof_id,
                "rule": rule_id,
                "test_file": test_file,
                "test_name": item.name,
                "status": "pass" if call.excinfo is None else "fail",
                "tier": tier,
            })

    def pytest_sessionfinish(self, session, exitstatus):
        if self.retired:
            names = ", ".join(sorted(
                "%s %s (%s)" % (f, p, t) for f, p, t in self.retired))
            _fail(session, 'purlin: "platforms=" is not read any more; write '
                           "@env(windows), @env(macos) or @env(linux) on the "
                           "proof line in the spec instead: %s" % names)
            return
        if self.proofs:
            self._write_proof_files()
            return
        if self.seen_features:
            _fail(session, "purlin: markers were seen and no proof entry was "
                           "written for %s; the proof files on disk describe "
                           "an earlier run."
                           % ", ".join(sorted(self.seen_features)))

    def _write_proof_files(self):
        root = self.root
        directory = os.path.join(root, PROOF_DIR)
        os.makedirs(directory, exist_ok=True)

        for (feature, tier), new_entries in self.proofs.items():
            path = os.path.join(directory, "%s.%s.json" % (feature, tier))

            existing = []
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as handle:
                        existing = json.load(handle).get("proofs", [])
                except (ValueError, OSError):
                    existing = []

            # Write-scoped overwrite keyed by (feature, tier, test_file). The
            # tier is carried by the file being written, so within it the key
            # is (feature, test_file). Keep other features untouched; keep this
            # feature's entries from test files this run did not execute, so
            # two files covering one (feature, tier) can run in any order; reap
            # entries whose test file is gone. The existence check resolves
            # each recorded path from the project root, the same root it was
            # relativized against, so a run started from a subdirectory reads
            # the paths it wrote rather than reaping all of them.
            run_files = {e["test_file"] for e in new_entries}
            # What this run wrote, so a skipped test's protection never keeps
            # an entry the run has just replaced: only an executed test
            # replaces its entry.
            run_wrote = {(e["id"], e["test_file"], e["test_name"])
                         for e in new_entries}

            def _keep(e, feature=feature, run_files=run_files,
                      run_wrote=run_wrote):
                if e.get("feature") != feature:
                    return True
                test_file = e.get("test_file") or ""
                if not test_file or not os.path.exists(
                        os.path.join(root, test_file)):
                    return False
                if test_file not in run_files:
                    return True
                return (
                    (feature, e.get("id"), test_file) in self.skipped
                    and (e.get("id"), test_file, e.get("test_name"))
                    not in run_wrote
                )

            kept = [e for e in existing if _keep(e)]
            payload = {
                "tier": tier,
                "proofs": sorted(kept + new_entries, key=_entry_order),
            }

            # Atomic write: tmp + rename. The temp name carries this process
            # id, so two plugins writing the same file concurrently never
            # share a temp path.
            tmp_path = "%s.%d.tmp" % (path, os.getpid())
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
            os.replace(tmp_path, path)


def _fail(session, message):
    """Print one line and make the run exit non-zero."""
    import sys

    print(message, file=sys.stderr)
    session.exitstatus = 1
