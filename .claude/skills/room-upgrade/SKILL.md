---
name: room-upgrade
---

# Skill: Room Upgrade

## Trigger

Use proactively when:
- The operator asks to check for upgrade opportunities
- During the morning routine, to flag possible upsells
- The operator says "upgrade", "upsell", "room upgrade", "upgrade opportunities"
- A guest replies accepting an upgrade offer

> **Template note:** Replace `{{HOTEL_NAME}}`, `{{OPERATOR_NAME}}`, `{{INBOX_*}}`, `{{EMAIL_CLI}}`, `{{PMS_*}}` placeholders, `<PremiumRoom>` / `<StandardRoom>` and `<UPGRADE_ITEM_ID>` before first run. See [README.md](../../../README.md#customising) for guidance.

## Purpose

Four functions:
1. **Scan** upcoming reservations for upgrade opportunities and draft offer messages
2. **Execute** upgrades when guests accept — change room, add charge, adjust rate
3. **Log** every offer to an Upgrades tracker so we never re-offer the same guest
4. **Re-price** the freed room — after every executed upgrade, run the Dynamic Pricing skill on the original room/dates so a newly-available room within the 0–6 day window is dropped to its floor instead of sitting at rack rate

---

## Room Mapping (template — fill in with your own rooms)

| Internal label | Display name | Room type | Room ID | Room Type ID |
|---|---|---|---|---|
| Premium A | `<PremiumRoom>` | premium room types | `<PREMIUM_ROOM_INSTANCE_ID_1>` | `<PREMIUM_ROOM_TYPE_ID>` |
| Premium B | `<PremiumRoom>` | premium room types | `<PREMIUM_ROOM_INSTANCE_ID_2>` | `<PREMIUM_ROOM_TYPE_ID>` |
| Standard A | `<StandardRoom>` | standard rooms | `<STANDARD_ROOM_INSTANCE_ID_1>` | `<STANDARD_ROOM_TYPE_ID_1>` |
| Standard B | `<StandardRoom>` | standard rooms | `<STANDARD_ROOM_INSTANCE_ID_2>` | `<STANDARD_ROOM_TYPE_ID_2>` |
| Suite | `<DeluxeRoom>` | deluxe room types | `<SUITE_ROOM_INSTANCE_ID>` | `<SUITE_ROOM_TYPE_ID>` |

**Upgrade path:** `<StandardRoom>` → `<PremiumRoom>`

**Upgrade catalogue:**
- "Room upgrade" PMS item ID: `<UPGRADE_ITEM_ID>` — pre-configured at your chosen per-night price (configured in `.env` as `UPGRADE_PRICE_PER_NIGHT_TIER1` and `UPGRADE_PRICE_PER_NIGHT_TIER2`)

---

## Part 1: Scanning for Opportunities

### Pricing Logic

Calculate the rate gap between the guest's current rate and the discounted premium rate, then pick an upgrade price that captures part of the gap (so both you and the guest win):

| Rate gap (discounted premium – current) | Suggested upgrade offer |
|---|---|
| Up to €30 / night | €<TIER1> / night extra |
| €31 – €50 / night | €<TIER2> / night extra |
| Over €50 / night | Usually not worth offering as an upsell — premium is selling at rack |

**Formula:**
1. Get the guest's current nightly rate from their reservation
2. Get the `<PremiumRoom>` standard rate for those dates from `{{PMS_RATES_TOOL}}`
3. Apply your usual discount (e.g. 10% direct discount): `discounted_rate = standard_rate * 0.9`
4. Gap = `discounted_rate - current_rate`
5. Apply the table above

### Scan Workflow

1. Fetch confirmed + checked_in reservations for the next 30 days via `{{PMS_LOOKUP_TOOL}}`.
2. Filter to guests assigned to `<StandardRoom>`.
3. Sort by length of stay descending (longer stays = more revenue, prioritised first).
4. No minimum-night requirement — even 1-night guests qualify.

### Check Availability

Call `{{PMS_RATES_TOOL}}` for each candidate's check-in / check-out dates. Filter to `<PremiumRoom>` rate plans where `roomsAvailable > 0`. Most PMS APIs return `totalRate` for the **whole stay** — divide by nights to get the per-night rate.

### Check If Already Offered

**Primary check — Upgrades tracker (fast):**

If you log offers to a sheet (recommended), query it by reservation ID before drafting. Match by reservation ID; fall back to `Guest Name + Check-in Date` if the res ID is unknown. Skip if any matching row exists with Status ≠ `Declined`.

**Fallback check — email search** (only if a tracker miss seems suspicious):

```bash
{{EMAIL_CLI}} search \
  --account {{INBOX_BOOKINGS}} \
  --query "subject:upgrade to:{guest_email_or_relay}" \
  --max 3
```

Skip if an offer has already been sent.

### Detect Guest Language

**Before drafting, always determine the guest's likely native language and write the message in that language.** Guests respond far better to outreach in their own language.

**Detection priority (use the first signal that resolves):**

1. **Phone country code** (most reliable). Map the international dialling code to language.
2. **Nationality / country field** in the reservation (`guestCountry`, `country`).
3. **Inbound email language** if the guest has already written to you — match what they used.
4. **Fallback:** English.

**Country code → language map (common cases):**

| Code | Country | Language |
|------|---------|----------|
| +33 | France | French |
| +32 | Belgium | French (assume FR; switch if Flemish signals) |
| +41 | Switzerland | French (assume FR; check name for DE/IT cues) |
| +39 | Italy | Italian |
| +34 | Spain | Spanish |
| +351 | Portugal | Portuguese |
| +49 | Germany | German |
| +43 | Austria | German |
| +31 | Netherlands | Dutch (or English — Dutch guests often comfortable in EN) |
| +44 | UK | English |
| +1 | US/Canada | English |
| +61 | Australia | English |
| +47 | Norway | English |
| +46 | Sweden | English |
| +45 | Denmark | English |
| +358 | Finland | English |
| anything else | — | English |

If the country code is ambiguous (e.g. +41 Switzerland) and you cannot resolve from name or email, default to English and flag for human override.

**Always log the language used** in the Upgrades tracker (Notes column), e.g. `Sent in FR`.

### Draft Upgrade Messages

Use the templates below. Translate them naturally into the detected language — do not machine-translate word-for-word. Use the formal address (`vous`, `Sie`, `Lei`, `usted`). **Always present to the operator for approval before sending.**

### Log the Offer

After the operator approves and the draft is created (or sent), append a row to the Upgrades tracker. See **Logging — Upgrades Tracker** below for the schema.

---

## Logging — Upgrades Tracker

Spreadsheet: `{{SHEET_ID_UPGRADES}}` (optional, recommended). Tab: `Upgrades`. Columns:

| Col | Field | Notes |
|-----|-------|-------|
| A | Date Sent | YYYY-MM-DD when draft was created |
| B | Guest Name | as in PMS |
| C | Reservation ID | primary key for dedupe |
| D | Source | Direct / Booking.com / Expedia / Airbnb / etc |
| E | Check-in Date | YYYY-MM-DD |
| F | Check-out Date | YYYY-MM-DD |
| G | Current Room Type | e.g. `<StandardRoom>` |
| H | Offered Room Type | e.g. `<PremiumRoom>` |
| I | Upgrade Price (€) | total €, not per-night |
| J | Status | Sent / Accepted / Declined / Silent / Executed |
| K | Date Resolved | when Status moved off Sent (blank otherwise) |
| L | Notes | relay address, anomalies, language, anything useful |

**Status lifecycle:** `Sent` → `Accepted` (then `Executed` after PMS change) / `Declined` / `Silent` (no reply 7+ days post-checkout).

### Scan Flow Integration

1. **BEFORE proposing offers:** read the Upgrades tab, exclude any guest with a row where Status ≠ `Declined` (already offered or in flight).
2. **AFTER drafting an offer:** append a row with Status = `Sent`.
3. **AFTER detecting a guest reply:** update Status (`Accepted` / `Declined`) and Date Resolved.
4. **AFTER executing the room change in the PMS:** update Status to `Executed` and add a note with the new sub-reservation ID.

---

## Part 2: Executing an Accepted Upgrade

When a guest accepts an upgrade offer, execute these steps **in order**. Always do Steps 0–4. Step 5 (payment) only if the operator explicitly says to record a payment.

### Step 0: Record original rate

Before changing anything, capture the original nightly rate — you need it for the rate adjustment.

```
detail = {{PMS_LOOKUP_TOOL}} get-reservation --reservation-id <RES_ID>
original_nightly_rate = detail.assigned[0].dailyRates[0].rate
sub_reservation_id   = detail.assigned[0].subReservationID
```

### Step 1: Change the room type

Move the booking from `<StandardRoom>` to `<PremiumRoom>`. **This automatically changes the nightly rate to the premium rack rate** — that's expected; we fix it in Step 3.

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

**Important notes:**
- The PMS may assign a different room instance than requested (e.g. the second of two `<PremiumRoom>` units). This is fine — both are the same room type.
- The nightly rate WILL change to the premium rack rate. This is expected.
- After this call, get the new `subReservationID` from the response — the room change may create a new one.

### Step 2: Add the upgrade charge (allocated to the room)

Add the "Room upgrade" item to the reservation. **Always pass `sub_reservation_id`** so the charge is allocated to the correct room on the folio.

```bash
{{PMS_RESERVATION_TOOL}} post-item \
  --reservation-id <RES_ID> \
  --property-id {{PMS_PROPERTY_ID}} \
  --item-id <UPGRADE_ITEM_ID> \
  --quantity <nights> \
  --sub-reservation-id <NEW_SUB_RES_ID>
```

### Step 3: Adjust the rate back to the original

The room type change reset the rate to rack rate. Apply a rate adjustment to bring the total back to the original room rate.

```
rate_difference = (new_rack_rate - original_nightly_rate) * nights
```

```bash
{{PMS_RESERVATION_TOOL}} post-adjustment \
  --reservation-id <RES_ID> \
  --property-id {{PMS_PROPERTY_ID}} \
  --amount <rate_difference> \
  --type rate \
  --notes "Rate correction: keep original rate ({original_nightly_rate}/night) for room upgrade"
```

**Critical: amount sign convention** depends on your PMS:
- In some PMS systems: positive = discount (reduces balance), negative = surcharge (increases balance)
- In others it's reversed. **Test with one reservation before bulk use.**
- The PMS typically auto-splits the adjustment between base rate and VAT.

### Step 4: Verify final state

**CRITICAL — do NOT trust top-level `total` and `dailyRates` alone.** After a rate adjustment, the daily room rate (e.g. premium rack) and the reservation `total` will not reconcile, and you will wrongly conclude the upgrade was not executed. The truth is in the detailed balance and the transactions log.

```
detail = {{PMS_LOOKUP_TOOL}} get-reservation --reservation-id <RES_ID>
print: roomTypeName, balanceDetailed (subTotal, additionalItems, taxesFees, grandTotal, paid)
print transactions (separate endpoint): date, category, description, amount, notes
```

**Pass criteria (ALL must be true):**
- `assigned[0].roomTypeName` == upgraded type
- `balanceDetailed.additionalItems` ≥ upgrade charge total (e.g. `<TIER>` × nights)
- A transaction with `description == "Room upgrade"` exists for the right amount
- A transaction with `notes` containing `"Rate correction"` or `"rate adjustment"` exists if the rate was kept at the original

**This same diagnostic applies to the SCAN flow too:** when checking whether a guest who accepted an upgrade still needs PMS work, run this verification block before flagging "needs execution". A booking can look unchanged at the top level but be fully reconciled in the detailed balance.

### Step 5: Record payment (ONLY if explicitly requested)

Only add a payment if the operator says the guest has already paid the upgrade charge. Do NOT add automatically.

### Step 6: Draft confirmation reply

Draft a reply confirming the upgrade. Use `{{EMAIL_CLI}}` and the original message ID for in-thread replies (so OTA-relay routing works). **Present the draft for approval before sending.**

### Step 7: Re-run dynamic pricing on the freed room

The upgrade just returned the original room (e.g. `<StandardRoom>`) to availability. Within the 0–6 day window, that room almost always now meets the rate-drop conditions because at least one other room is still booked.

**Always run the Dynamic Pricing skill** for the freed room's date range immediately after Step 6.

- If the proposal includes the freed room/date(s), present the diff and push on approval, then refresh the availability mirror.
- If no change is proposed (out of the 0–6 day window, or no overlapping booking), report "no rate change needed" and stop.

This step is **not optional** — leaving the freed room at rack rate wastes the last-minute pricing window.

---

## Room Move Within Same Type

To move a guest between rooms of the **same type** (e.g. between two `<PremiumRoom>` units), use a same-type room-assign endpoint instead of the cross-type room-change endpoint. This does NOT work for cross-type moves — use the change-room-type call for that.

---

## Message Templates

### Upgrade Offer — Checking In Today or Tomorrow

```
Subject: A little upgrade offer for your stay

Hi {first_name},

Welcome to {{HOTEL_NAME}}! We're looking forward to having you with us.

I wanted to reach out because we have one of our <PremiumRoom> rooms available for your dates. It's a beautiful room, and I think you'd really enjoy the difference for the rest of your stay.

If you'd like to upgrade, it would be just €{upgrade_per_night} extra per night (€{upgrade_total} total for your {nights}-night stay). It really does make a difference to the experience.

Just let me know and I'll take care of it.

Best,
{{OPERATOR_NAME}}
```

### Upgrade Offer — Future Check-In

```
Subject: Room upgrade available for your stay

Hi {first_name},

We're looking forward to welcoming you on the {check_in_day}!

One of our <PremiumRoom> rooms has just become available for your dates, and I thought I'd offer it to you before it goes.

It's a real upgrade from the <StandardRoom>, and for a {nights}-night stay I'd always recommend it.

The upgrade would be just €{upgrade_per_night} extra per night (€{upgrade_total} total). Let me know if you'd like to switch and I'll take care of everything.

Best,
{{OPERATOR_NAME}}
```

## HTML Formatting

Wrap each paragraph in `<p>` tags. Use `<br>` for line breaks within the sign-off.

## Sending Rules

| Booking source | Send from | Send to |
|----------------|-----------|---------|
| Direct (Website, Walk-In, Phone, Email) | `{{INBOX_BOOKINGS}}` | Guest's personal email |
| Booking.com | `{{INBOX_BOOKINGS}}` | Booking.com relay email (`xxx@guest.booking.com`) |
| Hotels.com / Expedia | `{{INBOX_BOOKINGS}}` | OTA relay email |

**Important:** OTA guest names in emails often differ from the reservation name in the PMS. Cross-reference by booking number or check-in date.

## Guardrails

- **NEVER send without approval** — always present drafts first
- **NEVER execute an upgrade without approval** — flag acceptance, show plan, get go-ahead
- **Record the original nightly rate BEFORE changing room type** — you need it for the adjustment
- **Always pass `sub_reservation_id` to the post-item call** — charges must be allocated to the room, not left unassigned on the folio
- **Always verify the final balance** after all steps
- **NEVER record a payment unless explicitly told to** — the charge is always added, but payment is only recorded when confirmed
- **Confirm rate-adjustment sign convention** for your PMS with one test before relying on it
