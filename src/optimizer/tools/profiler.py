import json
import pstats
import subprocess
import sys
import tempfile
from pathlib import Path

from optimizer.config import Config
from optimizer.state import ProfileRow

WORKER = Path(__file__).with_name("profile_worker.py")


def _read_rows(prof_path: Path, package_dir: Path) -> list[ProfileRow]:
    """Convert one .prof file into ProfileRow items (project functions only)."""
    print(f"reading {prof_path}")
    try:
        stats = pstats.Stats(str(prof_path))
    except Exception as exc:
        print("mistake", exc)
        exit(1)
    rows: list[ProfileRow] = []
    # stats.stats maps (filename, lineno, funcname) -> (cc, nc, tottime, cumtime, callers)
    for (filename, lineno, funcname), (_cc, nc, tt, ct, _callers) in stats.stats.items():
        if funcname == "<module>":
            continue
        try:
            rel = Path(filename).resolve().relative_to(package_dir)
        except (ValueError, OSError):
            continue  # not inside the target package (stdlib, site-packages, <string>, ...)
        rows.append(
            ProfileRow(
                file=rel.as_posix(),
                name=funcname,
                lineno=lineno,
                calls=nc,
                tottime=tt,
                cumtime=ct,
            )
        )
    return rows


def profile_workload(config: Config, timeout_s: int = 30) -> tuple[list[ProfileRow], dict[str, str]]:
    """Profile every function marked 'ok' in cases.json, each in its own process.

    Returns (rows, failures). failures maps qualified_name -> error text (traceback or timeout).
    timeout_s applies to each function separately.
    """
    package_dir = config.package_dir.resolve()
    run_dir = Path(config.workload_script).resolve().parent  # folder with workload.py and cases.json

    cases = json.loads((run_dir / "cases.json").read_text(encoding="utf-8"))
    names = [name for name, case in cases.items() if case["status"] == "ok"]

    rows: list[ProfileRow] = []
    failures: dict[str, str] = {}

    with tempfile.TemporaryDirectory() as tmp:
        for i, name in enumerate(names):
            prof_path = Path(tmp) / f"{i}.prof"
            cmd = [sys.executable, str(WORKER), str(run_dir / "workload.py"), name, str(prof_path)]
            try:
                result = subprocess.run(
                    cmd,
                    cwd=config.target_dir,   # the worker imports the target project from here
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=timeout_s,
                )
            except subprocess.TimeoutExpired:
                failures[name] = f"timeout after {timeout_s}s"
                continue

            if result.returncode != 0:
                print("failed to profile ", name)
                failures[name] = result.stderr[-1500:]  # tail of the traceback
                continue

            rows.extend(_read_rows(prof_path, package_dir))

    rows.sort(key=lambda r: r["tottime"], reverse=True)
    return rows, failures