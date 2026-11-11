from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    order_id: int
    customer: str
    category: str
    amount_cents: int
    day: int  # day of year, 1..365