# Room Upgrade Agent

A Claude Code sub-agent + skill for hotel operators. It scans upcoming reservations for upgrade opportunities (e.g. standard → premium), drafts personalised offer messages in the guest's language, and, once a guest accepts and you approve, executes the upgrade in your PMS as a 3-step change (room change + charge + rate adjustment) with verification.

This repo is a template: two markdown files that tell Claude Code how to do the job. You supply the command-line tools that talk to your PMS and your mailbox.

---

## What it does

- **Scans** upcoming reservations and filters to guests in standard rooms whose dates overlap with a free premium room
- **De-dupes** offers: checks an Upgrades tracker (sheet), or your email history, so the same guest is not offered the same upgrade twice
- **Calculates pricing** from a simple table that you set, and makes no offer when the premium room is selling well at full rate
- **Detects guest language** from the guest's earlier emails, phone country code or country field, and drafts the offer in that language
- **Creates drafts only.** It never sends a message to a guest
- **Executes accepted upgrades**, after your approval, in a fixed order:
  1. Record the original nightly rate (the room change overwrites it)
  2. Change the room type, which sets the nightly rate to the premium rate (expected)
  3. Add the upgrade-charge line item, then post a rate adjustment that keeps the original rate
- **Verifies the final balance**: `original_total + upgrade_charge` must reconcile against the detailed balance and the transactions
- **Stops on failure** instead of retrying, so a charge is not posted twice
- **Flags the freed room** in its report, so you can re-price it with the dynamic-pricing agent

---

## What you need

- [Claude Code](https://code.claude.com/docs/en/quickstart) installed
- A PMS with an API that supports room-type changes on a reservation, per-reservation line items, and rate adjustments. The examples follow Cloudbeds field names (`putReservation`, `postItem`, `postAdjustment`), but any PMS with these operations works.
- Your own scripts or CLIs for the PMS. The skill expects these calls; rename them in the skill if yours differ:

  | Tool | Calls the skill makes |
  |---|---|
  | Lookup tool | list reservations for a date range; `get-reservation` (with detailed balance and transactions) |
  | Rates tool | rates and availability per room type for given dates |
  | Reservation tool | `change-room-type`, `post-item`, `post-adjustment` |

- An email tool that can search a mailbox and create drafts (for example a Google Workspace CLI for Gmail)
- A "Room upgrade" item in your PMS for the upgrade charge
- Optional: a spreadsheet for the Upgrades tracker, and a tool that reads and writes it

---

## Quick start

1. **Clone the repo**:

   ```bash
   git clone https://github.com/th1-ai/room-upgrade-agent.git
   cd room-upgrade-agent
   ```

2. **Copy the env template** and fill in the values you know:

   ```bash
   cp .env.example .env
   ```

3. **Open Claude Code** from the project root:

   ```bash
   claude
   ```

4. **Run the setup prompt**:

   > Read the README and set this agent up with me. Read my `.env`, ask me for anything that is missing (room names, room IDs, premium room selling points, pricing thresholds, currency), then replace the placeholders in `.claude/agents/room-upgrade.md` and `.claude/skills/room-upgrade/SKILL.md`. Show me the changes before you save them.

   You can also edit the two files by hand. The values are listed in [Customising](#customising).

5. **Use the agent**:

   > Scan for upgrade opportunities.

   or, after a guest replies yes:

   > Reservation 12345 accepted the upgrade. Show me the plan.
   >
   > Approved, execute it.

   Claude Code delegates to the `room-upgrade` sub-agent because of its `description`. To call it by name, say "use the room-upgrade subagent" or type `@agent-room-upgrade`.

---

## Verify it works

1. Run `grep -rnE "\{\{[A-Z0-9_]+\}\}" .claude/` in a terminal. No output means that all placeholders are filled.
2. Ask for a scan. The first run is read-only on the PMS: it reads reservations and rates and creates email drafts. Check one draft against the reservation in your PMS.
3. Before the first real upgrade, make a test reservation in your PMS and run the execute steps on it. This is how you learn the sign of a rate adjustment in your PMS (see `PMS_ADJUSTMENT_SIGN`). Cancel the test reservation afterwards.

### Troubleshooting

| Problem | What to check |
|---|---|
| Claude does not use the agent | Start `claude` in the repo root. If you cloned while a session was open, restart Claude Code. Then name the agent: `@agent-room-upgrade` |
| The agent stops with "setup incomplete" | A `{{PLACEHOLDER}}` or a room ID in the Room Mapping table is not filled in |
| "Command not found" for a PMS or email tool | The tool paths in the skill do not match your scripts. The template contains no scripts |
| The balance looks wrong after an upgrade | Read the detailed balance and the transactions, not the top-level total. If it is still wrong, the adjustment sign is probably reversed. Do not let the agent post a second adjustment before you look at the folio |
| The same guest is offered twice | No tracker is configured and the earlier offer is not in the mailbox that the agent searches |

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
    │   └── room-upgrade.md                          # Sub-agent: modes, limits, report format
    ├── skills/
    │   └── room-upgrade/
    │       └── SKILL.md                             # Skill: the full process, preloaded into the agent
    └── agent-memory/
        └── room-upgrade/
            └── example-feedback-pattern.md          # Example memory note
```

---

## Customising

Each `{{PLACEHOLDER}}` has the same name as a line in `.env.example`.

| Placeholder | What to put | Example |
|---|---|---|
| `{{HOTEL_NAME}}` | Name of the property | `The Garden Inn` |
| `{{OPERATOR_NAME}}` | Name that signs guest messages | `Alex Morgan` |
| `{{INBOX_BOOKINGS}}` | Mailbox where drafts are created | `bookings@yourhotel.example` |
| `{{EMAIL_CLI}}` | Command that searches mail and creates drafts | `gws gmail` |
| `{{PMS_PROPERTY_ID}}` | PMS property ID | `123456` |
| `{{PMS_LOOKUP_TOOL}}` | Script that fetches reservations | `tools/pms_lookup.py` |
| `{{PMS_RATES_TOOL}}` | Script that fetches rates and availability | `tools/pms_rates.py` |
| `{{PMS_RESERVATION_TOOL}}` | Script for room change, item and adjustment | `tools/pms_reservation.py` |
| `{{PMS_ADJUSTMENT_SIGN}}` | How your PMS reads an adjustment amount | `positive amount = discount` |
| `{{UPGRADE_ITEM_ID}}` | PMS item ID of the "Room upgrade" charge | `987654` |
| `{{UPGRADE_PRICE_PER_NIGHT_TIER1}}` | Offer price per night, small rate gap | `20` |
| `{{UPGRADE_PRICE_PER_NIGHT_TIER2}}` | Offer price per night, larger rate gap | `30` |
| `{{SHEET_ID_UPGRADES}}` | ID of the Upgrades tracker sheet. No tracker: write `not configured` | `not configured` |

Also fill in, in `SKILL.md`:

- `<StandardRoom>` and `<PremiumRoom>`: your room-type names, everywhere they appear (also in the agent file)
- The **Room Mapping** table: room IDs, room type IDs and maximum guests
- **Premium room selling points**: the only room features the agent may mention to a guest
- The **pricing table**: thresholds and currency (the template uses € and gaps of 30 and 50 as examples)

Other values in `<ANGLE_BRACKETS>` or `{curly}` braces (`<RES_ID>`, `<nights>`, `{first_name}`) are per-reservation. Leave them; the agent fills them in on each run.

---

## How approval works

- **Emails:** the agent is instructed to create drafts only. You read and send them. For a hard guarantee, give your email tool draft-only access.
- **PMS changes:** the agent returns a plan first and changes the PMS only when your request says that you approve that reservation. Claude Code also asks for permission before it runs a command, unless you have allowed that command.
- **Payments:** not recorded unless you say the guest has paid.
- **Rates:** the agent never changes a room rate.

---

## How memory works

The agent has `memory: project`, so Claude Code gives it the folder `.claude/agent-memory/room-upgrade/` and loads `MEMORY.md` from that folder at the start of each run. The agent creates and maintains `MEMORY.md` itself. Useful notes are:

- **PMS behaviour**: how your PMS handles sub-reservation IDs, tax on the upgrade item, the adjustment sign
- **Corrections**: changes you made to a price or to the wording of an offer
- **Patterns**: which stays accept offers (your own observations, not statistics from this template)

[`example-feedback-pattern.md`](.claude/agent-memory/room-upgrade/example-feedback-pattern.md) shows the format of one note. It is not loaded until `MEMORY.md` lists it. Delete it once you have your own notes. Agent memory has no effect if you turned off Claude Code's auto memory.

---

## Related agents

- [`dynamic-pricing-agent`](https://github.com/th1-ai/dynamic-pricing-agent): run it after an upgrade, on the freed standard room and dates that this agent reports
- [`morning-routine-agent`](https://github.com/th1-ai/morning-routine-agent): the daily briefing, which can include an upgrade scan
- [`pre-arrival-outreach-agent`](https://github.com/th1-ai/pre-arrival-outreach-agent): welcome emails before arrival. Check that a guest does not get a welcome email and an upgrade offer on the same day

All 21 agents: [th1.ai/agent-stack](https://th1.ai/agent-stack)

---

## License

MIT. See [LICENSE](LICENSE).
