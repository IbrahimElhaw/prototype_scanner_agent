from .analytics import (
    count_vip_orders,
    customer_totals,
    daily_totals,
    find_duplicate_orders,
    revenue_by_customer_and_category,
    select_vip_customers,
)
from .generator import CATEGORIES
from .loader import load_orders
from .models import Order


def validate_catalog(categories: list[str]) -> bool:
    """Decoy: nested loops (AST will flag it) but only 6x6 items -> negligible runtime."""
    for i, a in enumerate(categories):
        for j, b in enumerate(categories):
            if i != j and a == b:
                return False
    return True


def build_report(orders: list[Order]) -> str:
    if not validate_catalog(CATEGORIES):
        raise ValueError("Duplicate category in catalog")
    customers = customer_totals(orders)
    top5 = sorted(customers.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    daily = daily_totals(orders)
    busiest_day = max(sorted(daily.items()), key=lambda kv: kv[1])
    duplicates = find_duplicate_orders(orders)
    matrix = revenue_by_customer_and_category(orders)
    vips = select_vip_customers(orders, min_total_cents=30000)
    vip_orders = count_vip_orders(orders, vips)

    lines = [
        f"orders: {len(orders)}",
        f"busiest day: {busiest_day[0]} ({busiest_day[1]} cents)",
        f"duplicate pairs: {len(duplicates)}",
        f"non-empty customer/category cells: {sum(1 for v in matrix.values() if v > 0)}",
        f"vip customers: {len(vips)}, vip orders: {vip_orders}",
        "top customers:",
    ]
    lines += [f"  {name}: {total}" for name, total in top5]
    return "\n".join(lines)


def run_pipeline(csv_lines: list[str]) -> str:
    """Entry point: raw CSV lines in, text report out."""
    return build_report(load_orders(csv_lines))