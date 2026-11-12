---
name: room-upgrade
description: Room upgrade process for a hotel. Scans upcoming reservations for guests in a standard room who can move to a free premium room, prices the offer, drafts the offer email in the guest's language (draft only), logs it to a tracker, and executes an accepted upgrade in the PMS (room change, upgrade charge, rate adjustment, verification). Use when the operator says "upgrade", "upsell", "room upgrade" or "upgrade opportunities", during the morning routine, or when a guest accepts an upgrade offer.
---

# Skill: Room Upgrade

> **Template note:** Replace every placeholder in double curly braces and fill in the Room Mapping table before first run. See [README.md](../../../README.md#customising). Values in `<ANGLE_BRACKETS>` inside commands (`<RES_ID>`, `<nights>`) are per-reservation and are filled in at run time.

## Purpose

1. **Scan** upcoming reservations for upgrade opportunities and draft offer messages
2. **Log** every offer to the Upgrades tracker so a guest is not offered the same upgrade twice
3. **Execute** an accepted upgrade after the operator approves: change room, add charge, adjust rate, verify
4. **Hand off** the freed room for re-pricing

---

## Room Mapping (fill in with your own rooms)

| Internal label | Display name | Room ID | Room Type ID | Max guests |
|---|---|---|---|---|
| Premium A | `<PremiumRoom>` | `<PREMIUM_ROOM_INSTANCE_ID_1>` | `<PREMIUM_ROOM_TYPE_ID>` | |
| Premium B | `<PremiumRoom>` | `<PREMIUM_ROOM_INSTANCE_ID_2>` | `<PREMIUM_ROOM_TYPE_ID>` | |
| Standard A | `<StandardRoom>` | `<STANDARD_ROOM_INSTANCE_ID_1>` | `<STANDARD_ROOM_TYPE_ID>` | |
| Standard B | `<StandardRoom>` | `<STANDARD_ROOM_INSTANCE_ID_2>` | `<STANDARD_ROOM_TYPE_ID>` | |

Add or remove rows to match your property. Rooms that are not in this table are never offered and never moved.

**Upgrade path:** `<StandardRoom>` → `<PremiumRoom>`

**Premium room selling points** (fill in; messages use only what is written here):

- _e.g. size, view, terrace, bath_

**Upgrade charge:** PMS item "Room upgrade", item ID `{{UPGRADE_ITEM_ID}}`. The price of the PMS item must equal the tier price you offer. If you use two tiers, the item must accept a price per posting, or you need one item per tier.

---

## Part 1: Scanning for Opportunities

### Scan Workflow

1. Fetch confirmed and checked-in reservations for the next 30 days via `{{PMS_LOOKUP_TOOL}}`.
2. Keep guests assigned to `<StandardRoom>`. Skip a reservation with more than one room and list it under "needs operator decision".
3. For a guest who is already checked in, the upgrade covers the **remaining nights only**. Use the remaining nights for availability, price and the message.
4. No minimum-night requirement. Sort by nights descending, because a longer stay earns more from one room.

### Check Availability

Call `{{PMS_RATES_TOOL}}` for each candidate's dates. Keep `<PremiumRoom>` rate plans with availability for **every night** of the stay (or of the remaining nights). Check that the party fits the "Max guests" column.

Most PMS APIs return the rate for the **whole stay**. Divide by nights to get the per-night rate.

**One free room, one open offer.** If several guests qualify for the same free premium room on overlapping dates, draft an offer only for the top-ranked guest per free room. List the others as "waiting". Two guests who both accept the same room is a problem that the operator then has to solve by phone.

### Check If Already Offered

**Primary check: the Upgrades tracker.** Match by reservation ID; fall back to guest name + check-in date. Skip the guest if any matching row exists, whatever its status. A guest who declined is not offered again unless the operator asks for it.

**Fallback check: email search.** Use it when no tracker is configured, or when the tracker has no row but you have reason to doubt it:

```bash
{{EMAIL_CLI}} search \
  --account {{INBOX_BOOKINGS}} \
  --query "subject:upgrade to:<guest_email_or_relay>" \
  --max 3
```

Skip the guest if an offer was already sent.

### Pricing Logic

1. Current nightly rate: from the guest's reservation.
2. `<PremiumRoom>` rate for the same dates: from `{{PMS_RATES_TOOL}}`.
3. Apply your usual direct discount, if you have one (e.g. 10%: `discounted_rate = premium_rate * 0.9`).
4. `gap = discounted_rate - current_rate`
5. Apply the table:

| Rate gap per night | Upgrade offer |
|---|---|
| Zero or negative | Do not price. Ask the operator (the guest already pays the premium rate or more) |
| Up to €30 | €{{UPGRADE_PRICE_PER_NIGHT_TIER1}} per night extra |
| €31 to €50 | €{{UPGRADE_PRICE_PER_NIGHT_TIER2}} per night extra |
| Over €50 | No offer. The premium room is selling well at full rate, so a cheap upgrade gives away revenue |

The thresholds and the currency are examples. Set your own. Do not offer a price that is not in this table.

### Detect Guest Language

Write the message in the guest's likely language. Use the first signal that resolves:

1. **Language of an email the guest already wrote to you.** This is the strongest signal.
2. **Phone country code** (table below).
3. **Country field** on the reservation.
4. **Fallback:** English.

| Code | Country | Language |
|------|---------|----------|
| +33 | France | French |
| +32 | Belgium | French or Dutch: ambiguous |
| +41 | Switzerland | German, French or Italian: ambiguous |
| +39 | Italy | Italian |
| +34 | Spain | Spanish |
| +351 | Portugal | Portuguese |
| +49 | Germany | German |
| +43 | Austria | German |
| +31 | Netherlands | Dutch |
| +44 | UK | English |
| +1 | US / Canada | English |
| +61 | Australia | English |
| +45 / +46 / +47 / +358 | Nordic countries | English |
| anything else | | English |

If the code is ambiguous and nothing else resolves it, write in English and flag it for the operator. A phone code is a guess, not a fact, so always state the language you chose in the report.

### Draft Upgrade Messages

Use the templates below. Translate naturally, not word for word, and use the formal address (`vous`, `Sie`, `Lei`, `usted`). Describe the premium room only with the selling points listed in Room Mapping. Create a draft with `{{EMAIL_CLI}}`; never send.

| Booking source | Draft from | Draft to |
|----------------|-----------|---------|
| Direct (website, walk-in, phone, email) | `{{INBOX_BOOKINGS}}` | Guest's own email |
| OTA (online travel agency) | `{{INBOX_BOOKINGS}}` | The OTA's relay address for that booking, in the existing thread where there is one |

OTA guest names in emails often differ from the reservation name in the PMS. Cross-reference by booking number or check-in date. If the OTA booking is prepaid or paid by virtual card, ask the operator how the upgrade charge is collected before you draft.

Email format: HTML, one `<p>` per paragraph, `<br>` inside the sign-off.

### Log the Offer

After the draft is created, append a row to the Upgrades tracker with Status = `Drafted`.

---

## Logging: Upgrades Tracker

Spreadsheet: `{{SHEET_ID_UPGRADES}}` (optional, recommended). Tab: `Upgrades`. Read and write it with your own spreadsheet tool. If no tracker is configured, say so in the report and use the email search for de-duplication.

| Col | Field | Notes |
|-----|-------|-------|
| A | Date Drafted | YYYY-MM-DD |
| B | Guest Name | as in PMS |
| C | Reservation ID | primary key for de-duplication |
| D | Source | Direct / name of the OTA |
| E | Check-in Date | YYYY-MM-DD |
| F | Check-out Date | YYYY-MM-DD |
| G | Current Room Type | e.g. `<StandardRoom>` |
| H | Offered Room Type | e.g. `<PremiumRoom>` |
| I | Upgrade Price | total, not per night |
| J | Status | Drafted / Sent / Accepted / Executed / Declined / Silent |
| K | Date Resolved | when Status became Accepted, Declined or Silent |
| L | Notes | language used, relay address, new sub-reservation ID, anomalies |

**Status lifecycle:** `Drafted` → `Sent` (the operator sent the draft) → `Accepted` → `Executed`, or `Declined`, or `Silent` (no reply by check-out).

Update the row when the operator confirms the send, when a reply arrives, and after the PMS change (Status `Executed`, new sub-reservation ID in Notes).

---

## Part 2: Executing an Accepted Upgrade

**Preconditions.** The guest accepted, and the operator approved the change for this reservation. Without both, show the plan and stop.

**Before Step 0:**

- Run the Step 4 verification block. If the upgrade is already in place, do not execute again.
- Confirm that `<PremiumRoom>` is still available for the dates. The room can sell between the offer and the reply.

**If any call fails or returns something unexpected: stop.** Do not retry and do not continue to the next step. Report the steps that completed, the IDs returned and the current folio. A blind retry can post the charge or the adjustment twice.

### Step 0: Record the original rate

The room change overwrites the nightly rate, and you need the original for Step 3.

```
detail = {{PMS_LOOKUP_TOOL}} get-reservation --reservation-id <RES_ID>
original_nightly_rate = detail.assigned[0].dailyRates[0].rate
original_total        = the detailed balance grand total
sub_reservation_id    = detail.assigned[0].subReservationID
```

If the nightly rate differs from night to night, record every night's rate and use the sum in Step 3. Field names here follow one PMS as an example; use the names your PMS returns.

### Step 1: Change the room type

```bash
{{PMS_RESERVATION_TOOL}} change-room-type \
  --reservation-id <RES_ID> \
  --property-id {{PMS_PROPERTY_ID}} \
  --new-room-type-id <PREMIUM_ROOM_TYPE_ID> \
  --new-room-id <PREMIUM_ROOM_INSTANCE_ID> \
  --checkin-date <YYYY-MM-DD> \
  --checkout-date <YYYY-MM-DD> \
  --adults <N> --children <N>
```

- The nightly rate changes to the premium rate. This is expected; Step 3 corrects it.
- The PMS may assign a different unit of the same type than the one requested. That is fine.
- Take the `subReservationID` from the response. The room change may create a new one.
- Pass the real number of adults and children from the reservation.

### Step 2: Add the upgrade charge

Pass the **new** sub-reservation ID, so that the charge is allocated to the room and not left unassigned on the folio.

```bash
{{PMS_RESERVATION_TOOL}} post-item \
  --reservation-id <RES_ID> \
  --property-id {{PMS_PROPERTY_ID}} \
  --item-id {{UPGRADE_ITEM_ID}} \
  --quantity <nights> \
  --sub-reservation-id <NEW_SUB_RES_ID>
```

### Step 3: Adjust the rate back to the original

```
rate_difference = (new_nightly_rate - original_nightly_rate) * nights
```

```bash
{{PMS_RESERVATION_TOOL}} post-adjustment \
  --reservation-id <RES_ID> \
  --property-id {{PMS_PROPERTY_ID}} \
  --amount <rate_difference> \
  --type rate \
  --notes "Rate correction: keep original rate (<original_nightly_rate>/night) for room upgrade"
```

**Sign convention: {{PMS_ADJUSTMENT_SIGN}}.** In some PMSs a positive amount is a discount (reduces the balance); in others it is the reverse. If the line above is not filled in, stop and ask the operator. The PMS usually splits the adjustment between base rate and tax by itself.

### Step 4: Verify the final state

Do not trust the top-level `total` and `dailyRates` alone. After a rate adjustment they still show the premium rate, and the upgrade looks wrong when it is correct. The truth is in the detailed balance and the transactions log.

```
detail = {{PMS_LOOKUP_TOOL}} get-reservation --reservation-id <RES_ID>
read: roomTypeName, balanceDetailed (subTotal, additionalItems, taxesFees, grandTotal, paid)
read the transactions: date, category, description, amount, notes
```

**Pass criteria (all must be true):**

- The assigned room type is `<PremiumRoom>`
- Exactly one "Room upgrade" transaction exists, for tier price × nights
- Exactly one transaction with "Rate correction" in the notes exists, for the Step 3 amount
- The detailed grand total equals `original_total + upgrade charge` (within rounding, and allowing for tax on the upgrade charge if your PMS adds it)

If a criterion fails, report the values found and stop. Do not post a second adjustment to "fix" the balance without the operator.

Use the same block in a scan when a guest has accepted and you are not sure whether the PMS work is done.

### Step 5: Record payment (only on request)

Add a payment only when the operator says the guest has paid the upgrade charge.

### Step 6: Draft the confirmation reply

Draft a reply that confirms the new room and the charge. Reply in the guest's thread (use the original message ID) so that OTA relay routing works. Draft only. Then set the tracker row to `Executed`.

### Step 7: Hand off the freed room for re-pricing

The upgrade returns a `<StandardRoom>` to availability, often close to arrival. Report the freed room and its dates under "Re-price handoff" so that the operator or the main session can run the dynamic-pricing agent ([th1-ai/dynamic-pricing-agent](https://github.com/th1-ai/dynamic-pricing-agent)) if it is installed. Do not change a rate from this skill.

---

## Room Move Within the Same Type

A move between two units of the **same** type is a room assignment, not a room-type change. It has no charge and no rate adjustment, and it is outside this skill's three-step process. Ask the operator before you make such a move.

---

## Message Templates

Replace `€` with your currency. `{curly}` values are filled in for each guest.

### Upgrade Offer: Checking In Today or Tomorrow, or Already In House

```
Subject: An upgrade offer for your stay

Hi {first_name},

Welcome to {{HOTEL_NAME}}! We're looking forward to having you with us.

One of our <PremiumRoom> rooms is free for your dates. {one or two selling points}

If you'd like to upgrade, it is €{upgrade_per_night} extra per night (€{upgrade_total} in total for {nights} nights).

Just let me know and I'll take care of it.

Best,
{{OPERATOR_NAME}}
```

### Upgrade Offer: Future Check-In

```
Subject: Room upgrade available for your stay

Hi {first_name},

We're looking forward to welcoming you on {check_in_day}!

One of our <PremiumRoom> rooms is free for your dates, and I wanted to offer it to you first. {one or two selling points}

The upgrade is €{upgrade_per_night} extra per night (€{upgrade_total} in total for {nights} nights). Let me know if you'd like to switch and I'll take care of everything.

Best,
{{OPERATOR_NAME}}
```

### Upgrade Confirmation

```
Subject: Your upgrade is confirmed

Hi {first_name},

Your stay is now in our <PremiumRoom>, from {first_upgraded_night} to {check_out_day}. The upgrade is €{upgrade_total} in total, added to your booking.

See you soon,
{{OPERATOR_NAME}}
```

---

## Guardrails

- **Drafts only.** Never send a message; the operator approves and sends.
- **No PMS write without the operator's approval** for that reservation.
- **Record the original rate before the room change.**
- **Pass the new sub-reservation ID to the charge.**
- **Stop on failure; never retry a write blindly.**
- **Verify against the detailed balance and the transactions**, not the top-level total.
- **No payment recorded** unless the operator says the guest paid.
- **No invented facts**: rates and availability come from the PMS tools, room features from the selling points list.
- **Offer wording is honest**: no false urgency ("last room", "only today") unless the PMS shows it.
