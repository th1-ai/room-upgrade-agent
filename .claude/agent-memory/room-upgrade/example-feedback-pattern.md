---
name: Verify final balance against detailed balance, not top-level total
description: After a rate adjustment, the top-level reservation total and dailyRates won't reconcile — checking only those leads to the wrong conclusion
type: feedback
---

> **Example pattern.** This file shows the *shape* of a useful agent-memory note. Replace it with your own learnings as the agent runs.

When verifying that an upgrade was executed correctly, do not rely on the top-level `total` field on the reservation, or on the `dailyRates` array. After Step 3 (rate adjustment), the daily rate will show the premium rack rate (e.g. higher than what the guest is paying) and the reservation `total` will not equal `original_total + upgrade_charge`. This is correct PMS behaviour but it makes the upgrade look broken.

**The truth is in two other places:**

1. **`balanceDetailed`** (or your PMS equivalent) — has `subTotal`, `additionalItems`, `taxesFees`, `grandTotal`, `paid`. The grand total here is the actual amount the guest owes.
2. **The transactions log** (separate endpoint) — shows every line item posted to the reservation: the upgrade-charge line, the rate-adjustment line, taxes, etc.

**Pass criteria when verifying an upgrade:**

- `assigned[0].roomTypeName` is the new (premium) type
- A transaction matching `description == "Room upgrade"` exists with the expected amount
- A transaction with notes containing `"Rate correction"` exists with the expected amount
- `balanceDetailed.additionalItems` ≥ upgrade charge total
- `balanceDetailed.grandTotal` ≈ `original_total + upgrade_charge` (within rounding)

**Apply the same check in the SCAN flow** — when a guest accepts but you're not sure if PMS work has already been done, this verification block tells you whether to execute or skip.

**Anti-pattern:**

Concluding "the upgrade didn't happen" because `total` looks too low or `dailyRates[0].rate` is the rack rate. Always go to the detailed balance and the transactions log.
