from dataclasses import dataclass
from pathlib import Path

# <project_root>/src/optimizer/config.py -> parents[2] == <project_root>
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class Config:
    # --- Target project (the code we want to speed up) ---
    target_dir: Path = _PROJECT_ROOT / "target"
    package_name: str = "shop_analytics"   # sub-folder that the scanner is allowed to analyze
    workload_script: str = "benchmark.py"  # run from target_dir under cProfile

    # --- Scanner behavior ---
    top_n: int = 5                         # how many functions the LLM gets to judge

    # --- LLM (swap the model here only) ---
    model_name: str = "qwen2.5-coder:3b"
    ollama_url: str = "http://localhost:11434"
    temperature: float = 0.0

    # --- Output ---
    output_path: Path = Path("scan_report.json")

    @property
    def package_dir(self) -> Path:
        return self.target_dir / self.package_name