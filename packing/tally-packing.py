#!/usr/bin/env python3
"""
Tally packing list from packing-list.yaml and output a markdown summary.
No dependencies beyond Python stdlib.
Usage: python3 tally-packing.py [path-to-yaml] > packing-tally.md
"""

import sys
import re
from datetime import datetime, timezone

path = sys.argv[1] if len(sys.argv) > 1 else "packing/packing-list.yaml"

with open(path) as f:
    content = f.read()

# Split into top-level category blocks
category_blocks = re.split(r'\n(?=\w)', content)

people = ['Dan', 'Matt', 'Joel', 'Pat', 'Jamie']

categories = []   # list of (category_name, [item_results])
total_items = 0
nobody_bringing = []
needs_coordination = []
all_confirmed = []

for block in category_blocks:
    key_match = re.match(r'^(\w+):', block)
    if not key_match:
        continue
    category = key_match.group(1)

    # Find all item blocks within this category
    # Items start at 2-space indent with a key, contain a 'packed:' subsection
    item_matches = re.finditer(
        r'  (\w+):\n(?:.*\n)*?    packed:\n((?:      \w+:.*\n)*)',
        block
    )

    items = []
    for m in item_matches:
        item_name = m.group(1)
        if item_name == 'note':
            continue
        packed_raw = m.group(2)

        # Check if shared: true appears before packed: for this item
        item_block_start = m.start()
        item_block_end = m.end()
        item_text = block[item_block_start:item_block_end]
        is_shared_item = bool(re.search(r'^\s+shared:\s*true', item_text, re.MULTILINE))

        # Parse each person's status
        statuses = {}
        for line in packed_raw.splitlines():
            pm = re.match(r'[ \t]+(\w+):[ \t]*(.*)', line)
            if pm:
                person = pm.group(1)
                val = pm.group(2).strip().lower()
                statuses[person] = val if val else None

        # Determine status
        confirmed = [p for p, v in statuses.items() if v == 'true']
        not_bringing = [p for p, v in statuses.items() if v == 'false']
        sharing = [p for p, v in statuses.items() if v == 'shared']
        undecided = [p for p, v in statuses.items() if not v]

        if is_shared_item:
            bringers = confirmed + sharing
            if not bringers:
                status = "🔴"  # nobody confirmed for shared item
                needs_coordination.append(f"{category} / {item_name}")
            elif len(bringers) == 1:
                status = "✅"  # exactly one person sorted
            else:
                status = "⚠️"  # multiple people bringing — could consolidate
        else:
            if not confirmed and not sharing:
                status = "⬜"
                if not undecided:  # everyone explicitly said false
                    nobody_bringing.append(f"{category} / {item_name}")
                    status = "❌"
            elif undecided:
                status = "🔸"  # some people haven't decided
            else:
                status = "✅"

        items.append((item_name, statuses, status, is_shared_item))
        total_items += 1

        if status == "✅" and not undecided:
            all_confirmed.append(item_name)

    if items:
        categories.append((category, items))

# ── Output markdown ──────────────────────────────────────────────

print("# Camino del Norte – Packing List Tally")
print(f"\n_Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")

# Summary line
filled = sum(
    1 for _, items in categories
    for _, statuses, status, _ in items
    if any(v for v in statuses.values())
)
print(f"**{filled}** items with at least one response &nbsp;|&nbsp; **{total_items}** total items\n")

# Attention flags
if needs_coordination:
    print("### ⚠️ Needs coordination — shared item, nobody confirmed yet")
    for item in needs_coordination:
        print(f"- {item.replace('_', ' ')}")
    print()

if nobody_bringing:
    print("### ❌ Nobody is bringing these")
    for item in nobody_bringing:
        print(f"- {item.replace('_', ' ')}")
    print()

# Per-category tables
person_cols = " | ".join(people)
separator = " | ".join(["---"] * len(people))

for category, items in categories:
    print(f"### {category.replace('_', ' ').title()}\n")
    print(f"| Item | {person_cols} | Status |")
    print(f"|---|{separator}|---|")

    for item_name, statuses, status, is_shared in items:
        def fmt(p):
            v = statuses.get(p)
            if v == 'true':    return "✅"
            if v == 'false':   return "❌"
            if v == 'shared':  return "🤝"
            return "—"

        cols = " | ".join(fmt(p) for p in people)
        label = item_name.replace('_', ' ')
        if is_shared:
            label += " *(shared)*"
        print(f"| {label} | {cols} | {status} |")

    print()

print("---")
print("*Key: ✅ bringing &nbsp; ❌ not bringing &nbsp; 🤝 shared/can share &nbsp; — undecided*")
print("*Shared items only need one person to bring them — coordinate with the group.*")
