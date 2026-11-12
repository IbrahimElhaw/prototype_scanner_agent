import pstats
import subprocess
import sys
import tempfile
from pathlib import Path

from optimizer.config import Config
from optimizer.state import ProfileRow


def profile_workload(config: Config, timeout_s: int = 300) -> list[ProfileRow]:
    """Run the workload under cProfile and return rows for project functions only."""
    package_dir = config.package_dir.resolve()

    with tempfile.TemporaryDirectory() as tmp:
        prof_path = Path(tmp) / "workload.prof"
        cmd = [sys.executable, "-m", "cProfile", "-o", str(prof_path), config.workload_script]

        try:
            result = subprocess.run(
                cmd,
                cwd=config.target_dir,   # run like a normal script from the target root
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Workload timed out after {timeout_s}s") from exc

        if result.returncode != 0:
            raise RuntimeError(f"Workload failed (exit {result.returncode}):\n{result.stderr[-1000:]}")

        stats = pstats.Stats(str(prof_path))

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

    rows.sort(key=lambda r: r["tottime"], reverse=True)
    return rows