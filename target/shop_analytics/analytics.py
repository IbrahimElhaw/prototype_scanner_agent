from .models import Order


def daily_totals(orders: list[Order]) -> dict[int, int]:
    """Linear single pass: already fine, nothing to optimize here."""
    totals: dict[int, int] = {}
    for order in orders:
        totals[order.day] = totals.get(order.day, 0) + order.amount_cents
    return totals


def customer_totals(orders: list[Order]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for order in orders:
        totals[order.customer] = totals.get(order.customer, 0) + order.amount_cents
    return totals


def find_duplicate_orders(orders: list[Order]) -> list[tuple[int, int]]:
    """Return (order_id_a, order_id_b) for every pair of orders that share
    customer, category, amount and day. Pairs are ordered by position (i < j).
    Known issue: O(n^2) pairwise comparison."""
    duplicates = []
    for i in range(len(orders)):
        for j in range(i + 1, len(orders)):
            a, b = orders[i], orders[j]
            if (a.customer, a.category, a.amount_cents, a.day) == (
                b.customer,
                b.category,
                b.amount_cents,
                b.day,
            ):
                duplicates.append((a.order_id, b.order_id))
    return duplicates


def revenue_by_customer_and_category(orders: list[Order]) -> dict[tuple[str, str], int]:
    """Revenue per (customer, category).
    Known issue: rescans all orders for every (customer, category) combination."""
    customers = sorted({o.customer for o in orders})
    categories = sorted({o.category for o in orders})
    result = {}
    for customer in customers:
        for category in categories:
            result[(customer, category)] = sum(
                o.amount_cents
                for o in orders
                if o.customer == customer and o.category == category
            )
    return result


def select_vip_customers(orders: list[Order], min_total_cents: int) -> list[str]:
    totals = customer_totals(orders)
    return sorted(c for c, t in totals.items() if t >= min_total_cents)


def count_vip_orders(orders: list[Order], vip_customers: list[str]) -> int:
    """Known issue: membership test on a list instead of a set."""
    count = 0
    for order in orders:
        if order.customer in vip_customers:
            count += 1
    return count