#!/usr/bin/env python3
"""PreToolUse guard for the room-upgrade agent.

Blocks a Bash command that looks like an email send unless AUTONOMY.md has
exactly one line "Level: <value>", the value is 3, and the daily send cap is
not reached. The value is 0, 1, 2, 3 or PAUSED. A missing file, a missing
line, more than one line or any other value counts as PAUSED.

Claude Code passes the tool call as JSON on stdin. Exit 0 = no decision (the
normal permission rules apply). Exit 2 = block; stderr goes back to Claude.
Any error inside this script blocks the command (fail closed).
"""
import datetime
import json
import os
import re
import sys

# Edit this so it matches the send command of YOUR email tool, and does not
# match its search and draft commands. Test both after you change it.
SEND_PATTERN = r"(?<![A-Za-z0-9_])(send|sendmail|msmtp)(?![A-Za-z0-9_])"


def block(reason):
    sys.stderr.write("autonomy-guard: blocked. " + reason + "\n")
    sys.exit(2)


def main():
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        sys.exit(0)
    command = (data.get("tool_input") or {}).get("command") or ""
    if not re.search(SEND_PATTERN, command, re.IGNORECASE):
        sys.exit(0)

    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    try:
        text = open(os.path.join(root, "AUTONOMY.md"), encoding="utf-8").read()
    except OSError:
        block("AUTONOMY.md is missing or unreadable, so the agent is PAUSED. Keep the draft.")

    levels = re.findall(r"(?m)^Level:[ \t]*(.*?)[ \t]*$", text)
    if len(levels) != 1:
        block("AUTONOMY.md must have exactly one 'Level: <value>' line (found %d), so the agent is PAUSED. Keep the draft." % len(levels))
    level = levels[0]
    if level not in ("0", "1", "2", "3"):
        block("AUTONOMY.md says 'Level: %s', so the agent is PAUSED. Keep the draft." % level[:20])
    if level != "3":
        block("Sending needs Level 3; AUTONOMY.md says Level %s. Keep the draft." % level)

    caps = re.findall(r"(?m)^Max sends per day:[ \t]*(\d+)[ \t]*$", text)
    if len(caps) != 1:
        block("AUTONOMY.md must have exactly one 'Max sends per day: N' line.")
    cap = int(caps[0])

    runs = os.path.join(root, "runs")
    os.makedirs(runs, exist_ok=True)
    counter = os.path.join(runs, ".sends-" + datetime.date.today().isoformat())
    sent = 0
    if os.path.exists(counter):
        with open(counter, encoding="utf-8") as fh:
            sent = sum(1 for line in fh if line.strip())
    if sent >= cap:
        block("Daily send cap reached (%d of %d). Keep the draft." % (sent, cap))
    with open(counter, "a", encoding="utf-8") as fh:
        fh.write(datetime.datetime.now().isoformat(timespec="seconds") + "\n")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:  # fail closed
        block("guard error: %s" % exc)
