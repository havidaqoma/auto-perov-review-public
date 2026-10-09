"""Writer lock: which processes may still be writing this issue's drafts.

WHY THIS EXISTS
The build refuses to read drafts that a writer may still be changing (handbook
7.4: an orphaned agy kept writing a section after its parent stage died, and
the build read a half-written file). The first guard refused whenever ANY agy
process was running on the machine. That is safe, but it made every build and
the fault-injection study hostage to unrelated work: a review of another paper,
run by agy from a different project, stopped this pipeline's negative control
and scored a clean build as broken.

The drafting stage now records the PID of itself and of every agy child it
starts in <draft dir>/.writers.json. The build refuses while any recorded PID
is alive under an expected image name. An orphan is still caught, because the
child's PID is recorded before it writes anything. PID reuse can only cause a
false refusal (the safe side) and is narrowed by the image-name check.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess

LOCK_NAME = ".writers.json"
WRITER_IMAGES = ("agy", "python", "pythonw")


def lock_path(draft_dir: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(draft_dir) / LOCK_NAME


def register(path: pathlib.Path | None, pid: int, role: str) -> None:
    """Record a writer PID. Written before the writer can touch a draft."""
    if path is None:
        return
    path = pathlib.Path(path)
    rec = {"writers": []}
    if path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
    rec["writers"].append({"pid": int(pid), "role": role})
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def start(path: pathlib.Path) -> None:
    """A new drafting run: forget writers of earlier runs, record this one."""
    path = pathlib.Path(path)
    path.unlink(missing_ok=True)
    register(path, os.getpid(), "drafting-stage")


def live_writers(path: pathlib.Path, timeout: int = 60) -> list[int] | None:
    """PIDs from the lock that are alive as a writer image.

    Returns None when no lock exists (drafts written before the lock existed),
    and raises RuntimeError when liveness cannot be measured: the caller must
    not treat an unmeasured state as clear.
    """
    path = pathlib.Path(path)
    if not path.exists():
        return None
    pids = sorted({int(w["pid"]) for w in
                   json.loads(path.read_text(encoding="utf-8")).get("writers", [])})
    if not pids:
        return []
    ids = ",".join(str(p) for p in pids)
    try:
        ps = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-Process -Id {ids} -ErrorAction SilentlyContinue | "
             "ForEach-Object { \"$($_.Id) $($_.ProcessName)\" }"],
            capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"writer liveness not measurable: {e}") from e
    live = []
    for line in (ps.stdout or "").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lower() in WRITER_IMAGES:
            live.append(int(parts[0]))
    return live
