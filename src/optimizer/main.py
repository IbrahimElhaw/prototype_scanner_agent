from optimizer.config import Config
from optimizer.graph import build_graph
from optimizer.llm import build_llm


def main() -> None:
    config = Config()
    graph = build_graph(build_llm(config))
    result = graph.invoke({"config": config})

    verdicts = {(j["file"], j["name"]): j for j in result.get("judgments", [])}
    print(f"{'function':<42}{'time(s)':>9}{'calls':>7}  improvable")
    for c in result["candidates"]:
        j = verdicts.get((c["file"], c["name"]))
        flag = "-" if j is None else f"{j['improvable']} ({j['confidence']})"
        print(f"{c['file'] + ':' + c['name']:<42}{c['tottime']:>9.4f}{c['calls']:>7}  {flag}")

    for err in result.get("errors", []):
        print("ERROR:", err)
    print("report:", result["report_path"])


if __name__ == "__main__":
    main()