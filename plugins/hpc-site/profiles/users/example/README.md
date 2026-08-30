# User profile template

Copy this directory, fill it in, and select it:

```bash
cp -r users/example users/$USER
export USER_PROFILE=$USER     # or omit — $USER is used automatically
```

A user profile holds **person facts** — things that follow you across
institutions. Cluster facts (genome paths, partitions) belong in a site profile.

| File | Holds |
|---|---|
| `setup_preferences.yaml` | Sample-sheet and sample-YAML conventions |
| `DO_NOT.md` | Prohibited actions — read before anything destructive |
| `matplotlib_defaults` | Python plot defaults (font, sizes, palette) |
| `.Rprofile` | R plot defaults and theme |
| `env/` | Claude Code environment variable template |

`users/sahuno/` is a filled-in example. Note that its `.Rprofile` already does
macOS/Linux/Windows font detection — user profiles are written to travel, which
is exactly why they are separated from the site axis.
