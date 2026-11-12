# runs/

The room-upgrade agent keeps its record here. Everything in this folder except this file is ignored by git, because it refers to real reservations.

| File | Written by | Purpose |
|---|---|---|
| `LOG.md` | the agent | One entry per run, newest last. The agent reads the last entries before it acts, so it does not repeat work |
| `handoff/room-upgrade-agent.md` | the agent | One line per standard room that an executed upgrade freed. Input for the [dynamic-pricing agent](https://github.com/th1-ai/dynamic-pricing-agent) |
| `.sends-YYYY-MM-DD` | the hook `.claude/hooks/autonomy-guard.py` | One line per send that the hook let through that day. The hook uses it for the daily cap |
| `cron.log` | your scheduler | The printed report of each scheduled run, if you redirect output as the README shows |

## Format of a `LOG.md` entry

```
## <YYYY-MM-DDTHH:MM> | scheduled or on request | Level <n>
Needs you: <one line per item, or "Nothing needs you">
Checked: <n> reservations, <from> to <to>; <n> replies read
Done: <action, with the reservation ID and the draft, row or transaction ID>
Shadow: <"would send" lines at Level 3, with a count, e.g. 2 of 5>
Proposed: <what a higher level, or your approval, would allow>
Errors: <tool, error text, what was left undone, or "none">
```

Rules for the agent:

- Reservation IDs only. No guest names, email addresses or phone numbers.
- Append; do not rewrite or delete earlier entries.
- A skipped run (`Level: 0`, `Level: PAUSED`, or a missing or unknown level) is one line: the heading plus the reason.

## Format of a `handoff/room-upgrade-agent.md` line

```
- [ ] <date written> | <room type> | <first free night> to <last free night> | reservation <id> | freed by upgrade
```

Whoever re-prices the room (the dynamic-pricing agent or you) changes `[ ]` to `[x]`.

The [morning-routine agent](https://github.com/th1-ai/morning-routine-agent) can read the last entry of `LOG.md` (the latest run summary) and the `Level:` line of `AUTONOMY.md` to show this agent's state in the daily briefing.
