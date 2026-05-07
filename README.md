# Room Upgrade Agent

A Claude Code sub-agent + skill for hotel operators. It scans upcoming reservations for upgrade opportunities (e.g. standard → premium), drafts personalised offer messages in the guest's language, and — once a guest accepts — executes the upgrade in your PMS as an atomic 3-step transaction (room change + charge + rate adjustment) with verification.

Built on the **WAT framework** (Workflows, Agents, Tools): probabilistic AI handles reasoning, deterministic scripts handle execution.

---

## What it does

- **Scans** upcoming reservations and filters to guests in standard rooms whose dates overlap with available premium rooms
- **De-dupes** offers — checks an Upgrades tracker (sheet) and the email history so the same guest is never offered the same upgrade twice
- **Calculates pricing** per a simple table — never offers below your minimum margin
- **Detects guest language** from phone country code (with country-field fallback) and drafts the offer in that language
- **Executes accepted upgrades** as a verified 3-step transaction:
  1. Capture original nightly rate (you cannot recover it after the room change)
  2. Change the room type — this resets the nightly rate to the premium rack rate (expected)
  3. Add the upgrade-charge line item, then post a rate adjustment to keep the original rate intact
- **Verifies the final balance** — `original_total + upgrade_charge` must reconcile, with a transaction matching "Room upgrade"
- **Triggers re-pricing** of the freed room via the dynamic-pricing agent so the now-empty standard room doesn't sit at rack rate

---

## What you need

- [Claude Code](https://claude.ai/code) installed
- A PMS that supports: room-type changes on a reservation, per-reservation line items, and rate adjustments. The reference setup uses Cloudbeds (`putReservation`, `postItem`, `postAdjustment`), but any PMS with these endpoints works.
- An email account you can draft to programmatically (Gmail via the Google Workspace CLI is the reference setup)

---

## Quick start

1. **Clone the repo** into a Claude Code project:

   ```bash
   git clone https://github.com/th1-ai/room-upgrade-agent.git
   cd room-upgrade-agent
   ```

2. **Copy the env template** and fill it in:

   ```bash
   cp .env.example .env
   ```

3. **Edit [`.claude/agents/room-upgrade.md`](.claude/agents/room-upgrade.md)** and [`.claude/skills/room-upgrade/SKILL.md`](.claude/skills/room-upgrade/SKILL.md) — replace the placeholders described in [Customising](#customising) with the wrappers your setup uses.

4. **Open in Claude Code** from the project root:

   ```bash
   claude
   ```

5. **Invoke the agent**:

   > "Scan for upgrade opportunities."
   >
   > or, after a guest replies yes:
   >
   > "<Guest> accepted the upgrade — execute it."

   Claude Code will pick up the `room-upgrade` sub-agent automatically because of the front-matter `description` line.

---

## File structure

```
room-upgrade-agent/
├── README.md
├── .env.example
├── .gitignore
├── LICENSE
└── .claude/
    ├── agents/
    │   └── room-upgrade.md                          # Sub-agent definition
    ├── skills/
    │   └── room-upgrade/
    │       └── SKILL.md                             # Skill (full process)
    └── agent-memory/
        └── room-upgrade/
            └── example-feedback-pattern.md          # Example "memory note"
```

---

## Customising

The agent and skill files use placeholders so they can be adapted to any PMS + email stack. Replace the following before first run:

| Placeholder | What to put | Example |
|---|---|---|
| `{{HOTEL_NAME}}` / `{{OPERATOR_NAME}}` | Display name + sender | `The Garden Inn` / `Alex Morgan` |
| `{{INBOX_BOOKINGS}}` | Account drafts are written to | `bookings@yourhotel.com` |
| `{{EMAIL_CLI}}` | Wrapper that creates Gmail drafts | `gws gmail` |
| `{{PMS_PROPERTY_ID}}` | PMS property ID | `123456789` |
| `{{PMS_LOOKUP_TOOL}}` | Script that fetches reservations + assignments | `tools/pms_lookup.py` |
| `{{PMS_RATES_TOOL}}` | Script that fetches rate plans / availability | `tools/pms_rates.py` |
| `{{PMS_RESERVATION_TOOL}}` | Script that wraps room-change + post-item + post-adjustment | `tools/pms_reservation.py` |
| `<PremiumRoom>` / `<StandardRoom>` | Your own room-type names | e.g. `Premium Suite` / `Standard Double` |
| `<UPGRADE_ITEM_ID>` | The PMS item ID for the upgrade charge | e.g. PMS item ID `1234567890` |

You can do this with any text editor or with a single `sed` pass.

---

## How memory works

The agent uses Claude Code's per-agent memory at `.claude/agent-memory/room-upgrade/`. After each run, it can save:

- **Feedback** — patterns that improve the offer hit-rate (e.g. "guests on stays of 4+ nights accept upgrades far more often — prioritise them")
- **Project notes** — context that affects pricing or messaging (e.g. "during local festival week, premium rooms sell at rack — skip discounted upgrades that week")
- **References** — pointers to other systems (e.g. "freed-room re-pricing handled by the dynamic-pricing agent")

[`example-feedback-pattern.md`](.claude/agent-memory/room-upgrade/example-feedback-pattern.md) shows the recommended format. Delete it once you have your own.

---

## Related agents

This agent works well alongside:

- [`dynamic-pricing-agent`](https://github.com/th1-ai/dynamic-pricing-agent) — automatically called after an upgrade is executed so the freed standard room is re-priced for the last-minute window
- [`pre-arrival-outreach-agent`](https://github.com/th1-ai/pre-arrival-outreach-agent) — you can chain these: pre-arrival outreach mentions the available premium room as a soft offer
- [`booking-inquiry-agent`](https://github.com/th1-ai/booking-inquiry-agent) — keeps the upgrade language consistent with how the same room was originally pitched at booking time

---

## License

MIT — see [LICENSE](LICENSE).
