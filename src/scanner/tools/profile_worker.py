"""Profile ONE target function from a generated workload.

Usage: python profile_worker.py <workload_path> <qualified_name> <prof_path>
The cwd must be the target project root.
"""
import cProfile
import importlib
import importlib.util
import os
import sys

# "python path/to/script.py" puts the script's folder on sys.path, not the cwd.
# We add the cwd so the target project's packages can be imported.
sys.path.insert(0, os.getcwd())


def load_workload(path: str):
    spec = importlib.util.spec_from_file_location("workload", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve(qualified_name: str):
    """'pkg.mod:func' -> the function object."""
    module_name, qualname = qualified_name.split(":")
    obj = importlib.import_module(module_name)
    for part in qualname.split("."):
        obj = getattr(obj, part)
    return obj


def main() -> None:
    workload_path, qualified_name, prof_path = sys.argv[1:4]
    workload = load_workload(workload_path)

    func = resolve(qualified_name)
    builder = workload.BUILDERS[qualified_name]
    n = max(workload.SIZES)  # profile the largest size only

    # Building the inputs happens BEFORE the profiler starts, so it is not measured
    args, kwargs = builder(n)

    profiler = cProfile.Profile()
    profiler.enable()
    func(*args, **kwargs)
    profiler.disable()
    profiler.dump_stats(prof_path)


if __name__ == "__main__":
    main()