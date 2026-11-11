import re

from .models import Order


def parse_line(line: str) -> Order:
    # Known pattern: regex compiled on every call instead of once at module level.
    pattern = re.compile(r"^(\d+),(cust_\d+),([a-z]+),(\d+),(\d+)$")
    match = pattern.match(line.strip())
    if match is None:
        raise ValueError(f"Malformed line: {line!r}")
    order_id, customer, category, amount, day = match.groups()
    return Order(int(order_id), customer, category, int(amount), int(day))


def load_orders(lines: list[str]) -> list[Order]:
    """Parse all data rows (the first line is the CSV header)."""
    return [parse_line(line) for line in lines[1:]]