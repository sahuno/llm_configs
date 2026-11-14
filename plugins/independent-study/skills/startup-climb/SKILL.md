---
name: startup-climb
description: Builds "The climb", an interactive mountain visualization of a company's funding journey, where height is valuation on a log scale, each funding round is a flag on the ridge, strategic deals are parachute drops, and the IPO or acquisition is the summit. Tapping a flag opens a card with the round's numbers, story and the general startup-playbook meaning of that stage. Use this skill whenever someone wants to explore, visualize, map or explain a startup's funding rounds, valuation history, path to IPO, or "startup to IPO roadmap" for a specific company (e.g. "show me Stripe's funding journey", "visualize how Databricks got to where it is", "do the mountain thing for Figma"), or wants to compare where one startup is against another company's path, even if they don't say "mountain" or "climb".
---

# Startup climb

Turns a company's funding history into an interactive mountain the person can explore. The
visual design, interactivity, dark mode, mobile layout and accessibility are already built into
`assets/template.html`. Your job is the research and the data; don't rewrite the template unless
the person asks for a design change.

## Workflow

### 1. Pin down the company and the framing

Identify the company. If the person mentions a second company to compare against ("LangChain just
raised a Series C, show me how Anthropic did it"), the main company is the one being climbed and
the other becomes a `here` marker on the matching stage ("LangChain is here"). Only ask a question
if the company is genuinely ambiguous.

### 2. Research every round, with web search

Funding data goes stale fast, so search even for companies you know well:

- One search for the overall funding history, then **separate searches for each round** whose
  amount, date, lead investor or valuation you'd otherwise fill from memory.
- One search for the **current status**: still private, IPO filed or scheduled, public, acquired
  or shut down. This decides the summit.
- Prefer the company's own announcements, regulatory filings (S-1) and major outlets over
  aggregator sites. Where sources disagree, use the company or filing figure and note the
  disagreement.

Collect for each round: date, amount raised, post-money valuation (or that it wasn't disclosed),
lead investors, and one fact that makes it memorable. Also note strategic investments,
down rounds, large debt facilities and tender offers if they matter to the story.

Never invent a valuation. If none was disclosed and no credible press estimate exists, set
`valuation` to `null`: the template places that flag by interpolation and shows "Not disclosed".
If you use a press estimate, mark it "(est.)" in `val` and add a note in `notes`.

### 3. Write the data file

Write `<company>-climb.json` to a working folder (in Claude Code, the session's scratchpad directory unless the person names a project folder) using this shape (all money values are billions of USD):

```json
{
  "company": "Anthropic",
  "title": "The climb",
  "lede": "One or two sentences: whose route, from when to when, and how to read it (height is value, each gridline is ten times the one below, tap a flag).",
  "asOf": "Nov 13, 2026",
  "status": "private | ipo-scheduled | public | acquired | closed",
  "here": { "camp": "C", "label": "LangChain is here" },
  "aheadLabel": "Next?",
  "notes": ["Caveats: which valuations are estimates, what's still unconfirmed."],
  "camps": [
    {
      "id": "C",
      "label": "C",
      "date": "2023-05",
      "valuation": 4.1,
      "kind": "round | strategic | exit | milestone",
      "name": "Series C",
      "sub": "Short subtitle, a few words",
      "when": "May 2023",
      "raised": "$450M",
      "val": "≈$4.1B (est.)",
      "lead": "Spark Capital",
      "story": "One or two sentences specific to this company.",
      "play": "One or two sentences on what this stage means in general."
    }
  ]
}
```

Field notes:

- `id` must be unique; `label` is the text on the flag (defaults to `id`) and must stay under 15
  characters, so use "A", "Seed", "IPO", "Big tech".
- `date` is `YYYY`, `YYYY-MM` or `YYYY-MM-DD`; camps are sorted by date automatically.
- `kind: "strategic"` draws a parachute floating above the ridge instead of a flag. Use it for
  corporate or strategic investments that weren't priced rounds.
- `kind: "exit"` for the IPO, acquisition or listing. When `status` is `private`, the template
  instead draws a dotted rope from the latest camp to a cloud labelled `aheadLabel`.
- `here` is optional. Without it, the latest camp is selected on load.
- `play` text: start from `references/playbook.md` and adapt it in plain language. Choose the
  entry by what the round really was (a down round, a pre-IPO round), not just its letter.
- Write for a newcomer: no unexplained jargon, typographic apostrophes (’), no fabricated quotes.
- At least two non-strategic camps need numeric valuations to draw the mountain.
- A camp with `valuation: null` that comes before the first camp with a number is drawn at that
  first camp's height, which reads as a valuation it never had. Leave such early steps (accelerator,
  an unpriced seed) off the map and mention them in the first flagged camp's `story`.
- Phone width fits about a dozen flags. With more, merge extensions into their round ("$250M, then
  $600M") and drop marks the company never confirmed, moving the facts into a neighbouring
  `story` or `notes`.

### 4. Build

```bash
python3 <skill-dir>/scripts/build.py <folder>/<company>-climb.json <folder>/<company>-climb.html
```

`<skill-dir>` is this skill's base directory, which Claude Code prints when the skill loads.

The script validates the data and stops with a readable message if something is off; fix the
JSON and rerun.

### 5. Check it

If Playwright is available, screenshot it at about 1200px and 390px wide and look for flag labels
colliding, a `here` label overlapping something, or a parachute sitting on a flag. Nudge by
shortening labels or shifting a strategic camp's date by a month or two (and say so in `notes`
only if that changes meaning). Skip this step if there's no browser.

### 6. Deliver

- With the Artifact tool: publish the HTML file (icon `chart`). On later changes,
  update the same artifact rather than creating a new one.
- Elsewhere: present the HTML file.

Then reply in a few sentences: what the climb shows (the steepest stretch, where any `here`
marker sits), which numbers are estimates, and the "as of" date. Cite sources for the facts you
mention in the reply. If an IPO or deal is scheduled but not complete, say so plainly.

## Example

`assets/example-anthropic.json` is a complete, working data file (Anthropic from 2021 to its
scheduled November 2026 IPO, with LangChain marked at Series C). Read it before writing a new data
file to match its tone and level of detail. Its figures are as of Nov 13, 2026 and must not be
reused for a later request without checking them again.
