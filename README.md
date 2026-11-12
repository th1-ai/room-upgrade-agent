# Room Upgrade Agent

A Claude Code sub-agent + skill for hotel operators. It scans upcoming reservations for upgrade opportunities (e.g. standard → premium), drafts personalised offer messages in the guest's language, and, once a guest accepts and you approve, executes the upgrade in your PMS as a 3-step change (room change + charge + rate adjustment) with verification. It can run on a schedule, and [`AUTONOMY.md`](AUTONOMY.md) sets how much it does without you.

This repo is a template: markdown files that tell Claude Code how to do the job, plus one small guard script. You supply the command-line tools that talk to your PMS and your mailbox.

---

## What it does

- **Scans** upcoming reservations and filters to guests in standard rooms whose dates overlap with a free premium room
- **De-dupes** offers: checks an Upgrades tracker (sheet), or your email history, so the same guest is not offered the same upgrade twice
- **Calculates pricing** from a simple table that you set, and makes no offer when the premium room is selling well at full rate
- **Detects guest language** from the guest's earlier emails, phone country code or country field, and drafts the offer in that language
- **Creates drafts only, by default.** It sends an offer itself only if you set Level 3 in `AUTONOMY.md`, and then only inside the limits written there
- **Runs on a schedule** if you want: it reads the replies to earlier offers, keeps a run log so it does not repeat work, and starts its report with "Needs you"
- **Executes accepted upgrades**, after your approval, in a fixed order:
  1. Record the original nightly rate (the room change overwrites it)
  2. Change the room type, which sets the nightly rate to the premium rate (expected)
  3. Add the upgrade-charge line item, then post a rate adjustment that keeps the original rate
- **Verifies the final balance**: `original_total + upgrade_charge` must reconcile against the detailed balance and the transactions
- **Stops on failure** instead of retrying, so a charge is not posted twice
- **Flags the freed room** in its report and in `runs/handoff/room-upgrade-agent.md`, so you can re-price it with the dynamic-pricing agent

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
- Optional, for the send guard in scheduled runs: `python3`

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

   > Read the README and set this agent up with me. Read my `.env`, ask me for anything that is missing (room names, room IDs, premium room selling points, pricing thresholds, currency), then replace the placeholders in `.claude/agents/room-upgrade.md` and `.claude/skills/room-upgrade/SKILL.md`. Copy `.claude/settings.example.json` to `.claude/settings.scheduled.json` and replace the placeholders in the copy. Show me the changes before you save them.

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

1. Run `grep -rnE "\{\{[A-Z0-9_]+\}\}" .claude/ --exclude=settings.example.json` in a terminal. No output means that all placeholders are filled.
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
| A scheduled run does nothing | Read the last entry of `runs/LOG.md`. `Level: 0` or `Level: PAUSED` in `AUTONOMY.md` skips the run, and so does a missing or unknown `Level:` line. "Permission denied" lines mean a command does not match an allow rule in `.claude/settings.scheduled.json` |
| A send is blocked at Level 3 | The message from `autonomy-guard` gives the reason: the level or the daily cap |

---

## File structure

```
room-upgrade-agent/
├── README.md
├── AUTONOMY.md                                      # You edit: level, limits, kill switch
├── .env.example
├── .gitignore
├── LICENSE
├── runs/
│   ├── README.md                                    # Format of the run log and the handoff file
│   └── .gitkeep                                     # LOG.md and handoff/ appear here; git ignores them
└── .claude/
    ├── settings.example.json                        # Example permissions + hook for scheduled runs
    ├── agents/
    │   └── room-upgrade.md                          # Sub-agent: modes, autonomy, report format
    ├── hooks/
    │   └── autonomy-guard.py                        # Blocks a send unless AUTONOMY.md allows it
    ├── skills/
    │   └── room-upgrade/
    │       └── SKILL.md                             # Skill: the full process, preloaded into the agent
    └── agent-memory/
        └── room-upgrade/
            └── example-feedback-pattern.md          # Example memory note
```

---

## Customising

Each `{{PLACEHOLDER}}` has the same name as a line in `.env.example`. Four of them (`EMAIL_CLI` and the three PMS tools) also appear in `.claude/settings.example.json`.

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
- The **send command** in Part 3, only if you plan to use Level 3

Limits for unattended runs (caps, quiet hours, offer ceiling) are plain numbers in [`AUTONOMY.md`](AUTONOMY.md). Edit them there.

Other values in `<ANGLE_BRACKETS>` or `{curly}` braces (`<RES_ID>`, `<nights>`, `{first_name}`) are per-reservation. Leave them; the agent fills them in on each run.

---

## How approval works

- **Emails:** below Level 3 the agent is instructed to create drafts only. You read and send them. For a hard guarantee, give your email tool draft-only access. At Level 3 it sends offer emails only, inside the limits in `AUTONOMY.md`; replies and confirmations stay drafts.
- **PMS changes:** the agent returns a plan first and changes the PMS only when your request says that you approve that reservation. Claude Code also asks for permission before it runs a command, unless you have allowed that command. A scheduled run never changes the PMS at any level, because the change posts a charge to a guest folio.
- **Payments:** not recorded unless you say the guest has paid.
- **Rates:** the agent never changes a room rate.

---

## Autonomy levels

[`AUTONOMY.md`](AUTONOMY.md) holds one line, `Level: 1`, that you change. The file also lists every action, its limit, and what the agent never does alone.

| Level | A scheduled run does this |
|---|---|
| PAUSED | Nothing, and the agent also does nothing when you ask |
| 0 | Nothing. The agent works only when you ask |
| 1 (default) | Reads everything and reports the offers it would make and the replies it found |
| 2 | Also creates the drafts and tracker rows, and prepares the plan for each accepted upgrade |
| 3 | Also sends offer emails that pass every limit: direct bookings, check-in 2 to 30 days away, table price, 3 per day, not in quiet hours. The first 5 are logged, not sent |

Never without you, at any level: the PMS change, payments, refunds, rate changes, replies to guest questions, deleting anything.

To stop everything, change the line to `Level: PAUSED`. The file must have exactly one `Level:` line. If the file or the line is missing, or the value is not `0`, `1`, `2`, `3` or `PAUSED`, the agent treats it as `PAUSED`: it does nothing and writes the reason to the run log.

---

## Run it on its own

The commands below follow the Claude Code docs for [non-interactive mode](https://code.claude.com/docs/en/headless), [permissions](https://code.claude.com/docs/en/permissions) and [hooks](https://code.claude.com/docs/en/hooks). They are examples. This template was not run against a real PMS or mailbox, so test each step with your own tools.

### 1. Make the settings file for scheduled runs

```bash
cp .claude/settings.example.json .claude/settings.scheduled.json
```

Replace the four placeholders in the copy (the setup prompt does this too). The file is only used when you pass it with `--settings`, so your normal sessions do not change. It contains:

- **allow**: your PMS lookup tool, your rates tool, your email tool, and file edits in `runs/` and the agent's memory folder. If you use a tracker sheet, add a rule for your spreadsheet tool, for example `"Bash(your-sheet-cli *)"`.
- **deny**: your PMS reservation tool (so a scheduled run cannot write to the PMS), `rm`, `curl`, `wget`, `git push`, edits to `AUTONOMY.md`, the settings files and the hook, and reads of `.env`.
- **hooks**: a `PreToolUse` hook that runs `.claude/hooks/autonomy-guard.py` before every Bash command.

An allow rule matches the command as the agent types it. If your tool is started as `python3 tools/pms_lookup.py`, write the rule that way. Claude Code's docs say that Bash rules are not a security boundary around a program; the strong guarantee is still an email tool with draft-only access and a PMS key without write access.

### 2. The send guard

`autonomy-guard.py` blocks a Bash command that contains the word `send` (or `sendmail`, `msmtp`) unless `AUTONOMY.md` has exactly one `Level:` line, that line says `Level: 3`, and fewer sends than "Max sends per day" passed today. It counts in `runs/.sends-<date>`. If the script itself fails, it blocks.

Change `SEND_PATTERN` at the top of the script to match your email tool, then test both cases:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"your-email-cli drafts create --to guest@example.com"}}' \
  | CLAUDE_PROJECT_DIR="$PWD" python3 .claude/hooks/autonomy-guard.py; echo "exit $?"   # expect: exit 0
echo '{"tool_name":"Bash","tool_input":{"command":"your-email-cli drafts send --id 1"}}' \
  | CLAUDE_PROJECT_DIR="$PWD" python3 .claude/hooks/autonomy-guard.py; echo "exit $?"   # expect: blocked, exit 2 (at Level 1)
```

The script was tested this way. It was not tested inside a live scheduled run. If `python3` is not installed, the hook fails without blocking, so check `python3 --version` first.

### 3. The command

Run it once by hand from the repo root:

```bash
claude -p "Use the room-upgrade subagent for a scheduled run. Read AUTONOMY.md first and obey it." \
  --settings .claude/settings.scheduled.json \
  --permission-mode dontAsk \
  --permission-prompts none \
  --max-turns 40
```

- `-p` runs without a session window and prints the report.
- `--permission-mode dontAsk` denies every command that is not in the allow list, instead of asking.
- `--permission-prompts none` tells Claude that nobody can approve a request. It needs Claude Code v2.1.259 or later; leave it out on an older version.
- `--max-turns` stops a run that does not finish.

### 4. A schedule (example: cron on macOS or Linux)

Every day at 07:30. Use full paths, because cron does not load your shell profile; `command -v claude` prints the path of `claude`.

```
30 7 * * * cd /path/to/room-upgrade-agent && /path/to/claude -p "Use the room-upgrade subagent for a scheduled run. Read AUTONOMY.md first and obey it." --settings .claude/settings.scheduled.json --permission-mode dontAsk --permission-prompts none --max-turns 40 >> runs/cron.log 2>&1
```

The computer must be on and you must be logged in to Claude Code on it. The Claude Code docs also describe [scheduled tasks in the Desktop app](https://code.claude.com/docs/en/desktop-scheduled-tasks); this template was not tested with them.

Scheduled use of a personal Pro or Max plan is subject to Anthropic's usage policy, and those plans assume ordinary individual use; for a heavy or business-critical schedule use an API key or a team plan.

### 5. Move up one level at a time

1. Run at Level 1 for 7 days. Each morning read the last entry of `runs/LOG.md`: are the proposed offers the ones you would make, at the right price?
2. Change the line to `Level: 2`. Run for 7 days. Check each draft before you send it. Count how many you changed.
3. Only if you changed none: fill in the send command in the skill, test the hook, and set `Level: 3`. The first 5 sends are logged as "would send". Read them, then let it run.
4. To go back, change the one line. `Level: PAUSED` stops everything.

---

## How memory works

The agent has `memory: project`, so Claude Code gives it the folder `.claude/agent-memory/room-upgrade/` and loads `MEMORY.md` from that folder at the start of each run. The agent creates and maintains `MEMORY.md` itself. Useful notes are:

- **PMS behaviour**: how your PMS handles sub-reservation IDs, tax on the upgrade item, the adjustment sign
- **Corrections**: changes you made to a price or to the wording of an offer
- **Patterns**: which stays accept offers (your own observations, not statistics from this template)

[`example-feedback-pattern.md`](.claude/agent-memory/room-upgrade/example-feedback-pattern.md) shows the format of one note. It is not loaded until `MEMORY.md` lists it. Delete it once you have your own notes. Agent memory has no effect if you turned off Claude Code's auto memory.

---

## Related agents

- [`dynamic-pricing-agent`](https://github.com/th1-ai/dynamic-pricing-agent): run it after an upgrade, on the freed standard room and dates. This agent writes them to `runs/handoff/room-upgrade-agent.md` (format in [`runs/README.md`](runs/README.md)); point the pricing agent at that file or copy the line
- [`morning-routine-agent`](https://github.com/th1-ai/morning-routine-agent): the daily briefing. It can read the last entry of this agent's `runs/LOG.md` (the latest run summary) and the `Level:` line of `AUTONOMY.md`, or start an upgrade scan
- [`pre-arrival-outreach-agent`](https://github.com/th1-ai/pre-arrival-outreach-agent): welcome emails before arrival. At Level 3 this agent does not send an offer to a guest who got another message from the hotel in the last 24 hours; below Level 3, check this yourself before you send a draft

All 21 agents: [th1.ai/agent-stack](https://th1.ai/agent-stack)

---

## License

MIT. See [LICENSE](LICENSE).
