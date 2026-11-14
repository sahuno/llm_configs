# independent-study

Written for anyone who installs this plugin from the `sahuno` marketplace. It
assumes you use Claude Code but no software-engineering background.

A plugin is a folder that bundles skills (instructions Claude loads when your
request matches them) so you install them in one step. This one is for
studying a topic on your own.

## Skills

| Skill | What it does | Loads when you say |
|---|---|---|
| `startup-climb` | Turns a company's funding history into an interactive mountain. Height is valuation on a log scale (each gridline is ten times the one below), each funding round is a flag, strategic investments are parachutes, and the IPO or acquisition is the summit. Tap a flag to see the round's numbers and what that stage means in general. | "show me Stripe's funding journey", "path to IPO for Figma", "how did Databricks get here" |

`startup-climb` searches the web for every round before drawing, because
funding figures go stale. It never makes up a valuation; undisclosed ones show
as "Not disclosed". Its bundled example (Anthropic, as of 13 Nov 2026) is there
to show the data format, not to be reused as current figures.

The plugin also holds a personal learning skill and its commands on the
author's own machine. They are kept out of this repository on purpose
(see `.gitignore`), so a fresh install from GitHub contains only
`startup-climb`.

## Install

```
/plugin install independent-study@sahuno
```

## Where the skill came from

It was first written as a claude.ai skill and downloaded as a `.skill` file on
2026-11-14. The only changes for Claude Code: it no longer uses the claude.ai
file paths (`/home/claude`, `/mnt/user-data/outputs`), and it has two extra
rules learned from a test run on Stripe (keep unpriced early steps off the
map; merge rounds when there are more than about a dozen flags).
