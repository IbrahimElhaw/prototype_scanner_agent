import re
from dotenv import load_dotenv
load_dotenv(dotenv_path="../../.env")
import ast
import json
import os

from context import helper_catalog
from validate import normalize, validate_builder

MODEL = "deepseek-v4.1-flash"
RUN_DIR = os.path.join("..", "run")
SIZES = [1000, 2000, 4000]

import os
from ollama import Client

from context import referenced_classes
from extractor import ClassInfo, FunctionInfo
from prompts import SYSTEM_PROMPT, build_user_prompt


def builder_name(qualified_name: str) -> str:
    """qualified_name = "my.module:MyClass.build -> build__my_module__MyClass_build"""
    module, qualname = qualified_name.split(":")
    return "build__" + module.replace(".", "_") + "__" + qualname.replace(".", "_")


def _strip_fences(text: str) -> str:
    """Remove ```python fences if the model added them despite the instructions.
        ```python print("Hello World") ``` -> print("Hello World")"
    """
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()



def write_run(builders: list[dict], skipped: list[tuple], run_dir: str) -> None:
    """Write run_dir/workload.py (valid builders + registry) and run_dir/cases.json."""
    os.makedirs(run_dir, exist_ok=True)
    valid = [b for b in builders if not b["error"]]

    imports = set()
    for builder in valid:
        for line in builder["imports"]:
            imports.add(line)
    imports = sorted(imports)
    header = ["import random", *imports]
    body = [b["code"] for b in valid]
    registry = ["SIZES = " + repr(SIZES), "", "BUILDERS = {"]
    registry += [f'    "{b["qualified_name"]}": {b["builder_name"]},' for b in valid]
    registry.append("}")

    with open(os.path.join(run_dir, "workload.py"), "w", encoding="utf-8") as f:
        f.write("\n".join(header) + "\n\n\n" + "\n\n\n".join(body) + "\n\n\n" + "\n".join(registry) + "\n")

    cases = {b["qualified_name"]: {"status": "ok"} for b in valid}
    for b in builders:
        if b["error"]:
            cases[b["qualified_name"]] = {"status": "skipped", "reason": f"invalid builder: {b['error']}"}
    for func, reason in skipped:
        cases[func.qualified_name] = {"status": "skipped", "reason": reason}

    with open(os.path.join(run_dir, "cases.json"), "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)

def _ask(llm: Client, system_prompt: str, user_prompt: str) -> str:
    """The only place that talks to the LLM. """
    # response = llm.chat(
    #     model=MODEL,
    #     messages=[{"role": "system", "content": system_prompt},
    #               {"role": "user", "content": user_prompt}],
    #     options={"temperature": 0},
    # )

    print(user_prompt)
    exit()
    response = {"message": {"content": ""}}
    return response["message"]["content"]


def _remove_pkg_name(func: FunctionInfo) -> str:
    """'shop_analytics.generator:generate_csv_lines' -> 'generate_csv_lines'"""
    return func.qualified_name.split(":")[1]


def _used_names(code: str) -> set[str]:
    return {n.id for n in ast.walk(ast.parse(code)) if isinstance(n, ast.Name)}

def counter():
    for i in range(1000):
        yield i
_counter = counter()

def generate_builder(llm: Client, func: FunctionInfo, classes: dict[str, ClassInfo],
                     runnable: list[FunctionInfo]) -> dict:
    """Ask the LLM for one builder, clean it, validate it. `error` is None if it is valid."""
    print(next(_counter))
    name = builder_name(func.qualified_name)
    class_infos = referenced_classes(func, classes)
    helper_infos = helper_catalog(func, runnable)
    result = {"qualified_name": func.qualified_name, "builder_name": name,
              "imports": [], "code": "", "error": None}

    user_prompt = build_user_prompt(func, class_infos, helper_infos, name)
    raw_code = _ask(llm, SYSTEM_PROMPT, user_prompt)
    try:
        code = normalize(_strip_fences(raw_code))
    except SyntaxError as e:
        result["error"] = f"syntax error: {e}"
        return result

    known = {c.name for c in class_infos} | {_remove_pkg_name(h) for h in helper_infos}
    result["error"] = validate_builder(code, name, _remove_pkg_name(func).split(".")[-1], known)

    # Import only what the builder actually uses; we write the imports, not the model
    used_names = _used_names(code)
    imports = [f"from {c.module} import {c.name}" for c in class_infos if c.name in used_names]
    imports += [f"from {h.qualified_name.split(':')[0]} import {_remove_pkg_name(h)}"
                for h in helper_infos if _remove_pkg_name(h) in used_names]
    result["imports"] = imports
    result["code"] = code
    return result


def main():
    import sys
    from extractor import extract_classes, extract_functions
    from filter import filter_functions

    root = sys.argv[1]
    print("root =", root)
    all_funcs = extract_functions(root)
    print("extracted:", len(all_funcs))
    funcs, skipped = filter_functions(all_funcs)
    print("runnable:", len(funcs), "| skipped:", len(skipped))

    classes = extract_classes(root)
    llm = Client(
        host='https://ollama.com',
        headers={'Authorization': 'Bearer ' + os.environ['OLLAMA_API_KEY']},
    )

    builders = [generate_builder(llm, f, classes, funcs) for f in funcs]
    exit(0)
    write_run(builders, skipped, RUN_DIR)
    print(f"Wrote {RUN_DIR}\\ with {sum(not b['error'] for b in builders)}/{len(builders)} builders")

    for b in builders:
        if b["error"]:
            print(f"  INVALID {b['builder_name']}: {b['error']}")

if __name__ == "__main__":
    main()