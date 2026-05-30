#!/usr/bin/env python3
"""
Tally votes from sleep.yaml and output a markdown summary.
No dependencies beyond Python stdlib.
Usage: python3 tally-sleep.py [path-to-yaml] > tally-results.md
"""

import sys
import re
from collections import Counter
from datetime import datetime, timezone

path = sys.argv[1] if len(sys.argv) > 1 else "sleep/sleep.yaml"

with open(path) as f:
    content = f.read()

day_blocks = re.split(r'\n(?=\w)', content)

total_days = 0
decided = 0
pending = 0
no_votes = 0

rows = []

for block in day_blocks:
    key_match = re.match(r'^(\S+):', block)
    if not key_match:
        continue
    day_key = key_match.group(1)

    votes_match = re.search(r'votes:\n((?:[ \t]+\S.*\n?)*)', block)
    if not votes_match:
        continue

    total_days += 1
    votes_raw = votes_match.group(1)
    votes = {}
    for line in votes_raw.splitlines():
        m = re.match(r'\s+(\w+):\s*(.*)', line)
        if m:
            votes[m.group(1)] = m.group(2).strip() or None

    filled = {k: v for k, v in votes.items() if v}
    total_people = len(votes)
    voted = len(filled)
    label = day_key.replace('_', ' ').title()

    if filled:
        tally = Counter(filled.values())
        winner, count = tally.most_common(1)[0]
        majority = count > voted / 2
        if majority:
            status = "✅"
            decided += 1
        else:
            status = "🔸"
            pending += 1
        others = ", ".join(f"{k} ({v})" for k, v in tally.most_common()[1:])
        rows.append((status, label, winner, f"{voted}/{total_people}", others))
    else:
        no_votes += 1
        rows.append(("⬜", label, "—", f"0/{total_people}", ""))

# Output markdown
print(f"# Camino del Norte – Accommodation Vote Tally")
print(f"\n_Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")
print(f"**{decided}** decided &nbsp;|&nbsp; **{pending}** needs consensus &nbsp;|&nbsp; **{no_votes}** no votes yet &nbsp;|&nbsp; **{total_days}** total stages\n")
print("| | Stage | Leading choice | Votes | Other votes |")
print("|---|---|---|---|---|")
for status, label, winner, votes_str, others in rows:
    print(f"| {status} | {label} | {winner} | {votes_str} | {others} |")