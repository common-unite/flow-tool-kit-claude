# Tabs

A set of tabs in a column, each holding its own components: blocks, rich text, a Form Slot.

**Maps to:** Tabs (`forceCommunity:tabset`). Drawn with the markup and theme styles an Aura site renders (captured from the Testing CS site), not the SLDS Tabs blueprint, because that is what Aura draws.

| Prop | Builder setting | Notes |
| --- | --- | --- |
| `tabs` | Tabs | `[{ tabName, tabKey }]`, stored in `tabsetConfig.tabs`. `tabKey` is `tab1`, `tab2` and so on. |
| `activeTab` | (the tab that opens first) | A `tabKey`. Default the first tab. |
| `useOverflowMenu` | Show overflow menu | Tabs past the width go into a More menu. |
| children | (each tab's region) | One child per tab, in order. Wrap a tab with several components in a `React.Fragment`. |

## Notes
- On the site each tab is a region; the active tab underline and label colors come from the theme.
- In a narrow column (the 4 of an 8/4) the labels run out of room fast; keep them to one or two words.
- Clicking a tab in the preview switches it, as on the site.

## On LWR

Tabs on LWR is `dxp_layout:tabs`, drawn as Testing LWR renders it at Builder's default settings: bold active label over a brand underline, a thin line under the bar.

- `tabsetConfig` is stored as a JSON string, and each tab's region is named by its `tabKey`.
- Every tab is drawn on the page; the inactive ones are hidden until chosen.
- `useOverflowMenu` is Aura's name; LWR's setting is Enable Overflow Menu (`enableOverflowMenu`), off by default.
- Components inside a tab are not spaced by the column's component spacer.
