# Project config: flow-tool-kit.json

One JSON file at the project root that every Flow Tool Kit skill reads. ftk-start writes it (its `scripts/ftk_config.py` reads and writes it the same way in chat and Claude Code); the other skills read it and never ask its questions again. Unknown keys are ignored, so add rather than rename.

A skill that needs an answer the file lacks asks the same single question ftk-start would, and saves the answer here.

```json
{
  "config_version": 1,
  "design_systems": {
    "forms": {"title": "FlowToolKit Forms", "url": "<this account's design system link>", "kit_version": "<shipped kit version>", "installed_on": "2026-01-15"},
    "site_blocks": {"title": "FlowToolKit Site Blocks", "url": "<link>", "kit_version": "<version>", "installed_on": "2026-01-15"}
  },
  "orgs": {
    "00D000000000001EAA": {
      "name": "Riverside Community Garden (sandbox)",
      "alias": "<org-alias>",
      "edition": "paid",
      "edition_source": "asked",
      "audiences": ["guest", "internal"],
      "brand_kit": {"choice": "use", "found": "style defaults and brand file"},
      "platforms": {"outbound_funds": true, "nonprofit_cloud": false},
      "catalog": "<path of org-catalog's file>",
      "answered_on": "2026-01-15"
    }
  }
}
```

| Key | Rule |
|---|---|
| `design_systems` | Per claude.ai account, not per org. Only the systems installed so far; Site Blocks only when a site was needed |
| `orgs` | Keyed by the 18-character org Id, because an alias differs between computers |
| `edition` | `paid` or `free`. `edition_source`: `asked` (the person said) or `assumed` (they did not know; paid was used) |
| `audiences` | Any of `guest`, `portal`, `internal` |
| `brand_kit.choice` | `use`, `update`, `new` or `none` |
| `platforms` | As org-catalog found them |

In chat, write the file to the outputs folder and suggest the person add it to their claude.ai Project's files, so the next chat in that Project reads it. In Claude Code it lives in the project folder.
