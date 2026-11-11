"""Workload entry point: `python benchmark.py [n_orders]`."""
import sys
import time

from shop_analytics.generator import generate_csv_lines
from shop_analytics.report import run_pipeline


def main(n_orders: int = 3000) -> None:
    lines = generate_csv_lines(n_orders)
    start = time.perf_counter()
    report = run_pipeline(lines)
    elapsed = time.perf_counter() - start
    print(report)
    print(f"\nelapsed: {elapsed:.2f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3000)