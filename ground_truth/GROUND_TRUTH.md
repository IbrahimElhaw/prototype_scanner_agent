# Ground Truth: shop_analytics

> **Warning:** This file is for the developer only. The agent must NOT read it during analysis or
> optimization, otherwise the evaluation is meaningless. Let the agent read files under `shop_analytics/`
> only, or keep this file outside the path the agent can access.

## Files

| File | Role | May the agent modify it? |
|---|---|---|
| `shop_analytics/models.py` | `Order` dataclass | Yes (nothing to optimize) |
| `shop_analytics/generator.py` | Deterministic CSV data generation (fixed seed) | Yes |
| `shop_analytics/loader.py` | Parses CSV lines into `Order` objects | Yes |
| `shop_analytics/analytics.py` | Computations (aggregation, duplicates, VIPs) | Yes |
| `shop_analytics/report.py` | Builds the text report; entry point `run_pipeline` | Yes |

## Table 1: Real problems (fixable, with a genuine speedup)

| File | Function | Problem | Fix | Self time (n=3000) | Notes |
|---|---|---|---|---|---|
| `shop_analytics/analytics.py` | `find_duplicate_orders` | O(n²): compares every order with every later order | Group in a dict keyed by `(customer, category, amount_cents, day)`, then build pairs inside each group | ~0.66s | Fix measured: 0.833s -> 0.0033s (~250x faster) |
| `shop_analytics/analytics.py` | `revenue_by_customer_and_category` | Rescans all orders for every (customer, category) cell | Aggregate in a single pass into a dict | ~0.18s | Fix not measured yet |
| `shop_analytics/analytics.py` | `count_vip_orders` | `in` on a `list` instead of a `set` | Build `set(vip_customers)` once inside the function | ~0.005s | Small gain; grows with the number of VIP customers |

**Expected Analyzer ranking (by self time):**
`find_duplicate_orders`, then `revenue_by_customer_and_category`, then `parse_line`, then `count_vip_orders`.

## Table 2: Traps

### A) Traps for the Analyzer and Verifier (optimization not worth it)

| File | Function | Trap | Failure if the agent falls for it | Expected behavior of a sound system |
|---|---|---|---|---|
| `shop_analytics/report.py` | `validate_catalog` | Nested loops but only 6x6 items (decoy for AST tools) | Ranks it among the top candidates based on the AST signal alone | The Analyzer does not promote it because its real runtime is ~0. If it reaches the Optimizer anyway, the Verifier rejects the change (no improvement beyond noise) and rolls back |
| `shop_analytics/analytics.py` | `daily_totals`, `customer_totals` | Linear and already fine, but visible in the profile | Tries to "optimize" them | The LLM judges "no improvement possible" and they never enter the candidate list |
| `shop_analytics/loader.py` | `parse_line` | Repeated `re.compile`: theoretically valid fix, but Python's internal regex cache makes the gain smaller than the noise | Applies it and claims an improvement | Tests pass, but the Verifier measures several runs and rejects because the difference is within noise. If it is accepted, the acceptance threshold is too weak |

### B) Behavior-breaking traps (the fix is faster but changes the result)

| File | Function | Trap | Failure if the agent falls for it | Expected behavior | Intentional? |
|---|---|---|---|---|---|
| `shop_analytics/analytics.py` | `find_duplicate_orders` | Pair ordering | A single-pass fix yields pairs sorted by (j, then i) instead of (i, then j). Example: `(3,4)` appears before `(2,5)` | A characterization test fails and the change is rolled back. But it only fails if the tests contain at least two interleaved groups; otherwise the broken change slips through | Yes |
| `shop_analytics/analytics.py` | `revenue_by_customer_and_category` | Zero-value cells | A fix that emits only non-empty cells drops keys whose value is 0 | A direct test of the function fails. only running will NOT catch it because the report only counts `v > 0` | Partly |
| `shop_analytics/analytics.py` | `select_vip_customers` | Changed return type | Returns a `set` instead of a `list` to speed up `count_vip_orders` | A test comparing against a list fails and the change is rolled back | No (accidental) |
