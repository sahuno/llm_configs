#!/usr/bin/env python3
"""Fill the startup-climb template with a company's funding data.

Usage: python3 build.py data.json output.html
Exits non-zero with a readable message if the data is invalid.
"""
import json
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
STATUSES = {"private", "ipo-scheduled", "public", "acquired", "closed"}
KINDS = {"round", "strategic", "exit", "milestone"}
DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def fail(msg):
    sys.exit(f"Data error: {msg}")


def validate(d):
    for key in ("company", "title", "lede", "asOf", "status", "camps"):
        if key not in d:
            fail(f'missing top-level "{key}"')
    if d["status"] not in STATUSES:
        fail(f'status must be one of {sorted(STATUSES)}')
    camps = d["camps"]
    if len(camps) < 2:
        fail("need at least 2 camps")
    ids = set()
    valued = 0
    for i, c in enumerate(camps):
        where = f'camp #{i + 1} ({c.get("id", "?")})'
        for key in ("id", "date", "name", "when", "story", "play"):
            if not c.get(key):
                fail(f'{where} is missing "{key}"')
        if c["id"] in ids:
            fail(f'{where}: duplicate id')
        ids.add(c["id"])
        if not DATE_RE.match(str(c["date"])):
            fail(f'{where}: date must be YYYY, YYYY-MM or YYYY-MM-DD')
        kind = c.get("kind", "round")
        if kind not in KINDS:
            fail(f'{where}: kind must be one of {sorted(KINDS)}')
        v = c.get("valuation")
        if v is not None:
            if not isinstance(v, (int, float)) or v <= 0:
                fail(f'{where}: valuation must be a positive number in billions of USD, or null')
            if kind != "strategic":
                valued += 1
        if len(c.get("label", c["id"])) > 14:
            fail(f'{where}: flag label is too long for the map; keep "label" (or "id") under 15 characters')
    if valued < 2:
        fail("at least 2 non-strategic camps need a numeric valuation to draw the mountain")
    here = d.get("here")
    if here and here.get("camp") not in ids:
        fail('"here.camp" must match a camp id')


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    data = json.loads(Path(sys.argv[1]).read_text())
    validate(data)
    html = TEMPLATE.read_text()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = f'{data["title"]}: {data["company"]}'.replace("&", "&amp;").replace("<", "&lt;")
    html = html.replace("/*__DATA__*/", payload).replace("__PAGE_TITLE__", title)
    Path(sys.argv[2]).write_text(html)
    print(f"Wrote {sys.argv[2]} with {len(data['camps'])} camps")


if __name__ == "__main__":
    main()
