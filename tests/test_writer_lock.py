"""The build waits only for this issue's own writers (stages/writer_lock.py).

The earlier guard refused whenever any agy process ran on the machine, so an
unrelated agy job stopped the build and made the fault-injection negative
control read as broken. These tests pin the narrower rule without weakening it:
a recorded live writer still blocks, an unrecorded one does not, and an
unmeasurable state never counts as clear.
"""
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stages import writer_lock  # noqa: E402


def test_no_lock_means_unknown_not_clear(tmp_path):
    assert writer_lock.live_writers(tmp_path / ".writers.json") is None


def test_recorded_live_writer_blocks(tmp_path):
    lock = writer_lock.lock_path(tmp_path)
    writer_lock.start(lock)               # records this python process
    assert writer_lock.live_writers(lock) == [os.getpid()]


def test_dead_writer_does_not_block(tmp_path):
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    lock = writer_lock.lock_path(tmp_path)
    writer_lock.register(lock, p.pid, "agy")
    assert writer_lock.live_writers(lock) == []


def test_start_forgets_earlier_runs(tmp_path):
    lock = writer_lock.lock_path(tmp_path)
    writer_lock.register(lock, 999999, "agy")
    writer_lock.start(lock)
    import json
    pids = [w["pid"] for w in json.loads(lock.read_text())["writers"]]
    assert pids == [os.getpid()]


def test_unmeasurable_raises(tmp_path, monkeypatch):
    lock = writer_lock.lock_path(tmp_path)
    writer_lock.start(lock)

    def boom(*a, **k):
        raise FileNotFoundError("powershell")
    monkeypatch.setattr(writer_lock.subprocess, "run", boom)
    with pytest.raises(RuntimeError):
        writer_lock.live_writers(lock)


@pytest.mark.parametrize("rel", ["scripts/stages", "yearly/scripts/stages"])
def test_builders_no_longer_match_any_agy(rel):
    for f in (ROOT / rel).glob("s18*.py"):
        assert "Get-Process agy" not in f.read_text(encoding="utf-8"), f.name
