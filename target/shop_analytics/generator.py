import random

CATEGORIES = ["books", "games", "music", "toys", "garden", "kitchen"]
HEADER = "order_id,customer,category,amount_cents,day"


def generate_csv_lines(n_orders: int, seed: int = 42) -> list[str]:
    """Deterministic fake order log. ~2% of rows repeat the previous order
    (same customer/category/amount/day, new order_id) to create duplicates."""
    rng = random.Random(seed)
    lines = [HEADER]
    prev = None
    for order_id in range(1, n_orders + 1):
        if prev is not None and rng.random() < 0.02:
            customer, category, amount, day = prev
        else:
            customer = f"cust_{rng.randrange(500):04d}"
            category = rng.choice(CATEGORIES)
            amount = rng.randrange(500, 10000)
            day = rng.randrange(1, 366)
        prev = (customer, category, amount, day)
        lines.append(f"{order_id},{customer},{category},{amount},{day}")
    return lines