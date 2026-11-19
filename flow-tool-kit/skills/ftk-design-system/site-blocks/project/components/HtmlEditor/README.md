# HtmlEditor

Authored HTML shown as written, for embeds and one-off markup.

**Maps to:** HTML Editor (`forceCommunity:htmlBlock`). The one prop is `richTextValue`, the markup as Builder stores it. `designTag` draws a small "HTML" tag in the corner, for designs only.

## Notes
- An Aura site strips `<script>` and blocks frames, objects and embeds it cannot vouch for. When the markup has one, the preview flags it and leaves it out, so the design does not show something the site will not.
- Use SLDS classes or tokens in the markup where you can; hand-styled markup is a design question to raise.

## On LWR

HTML Editor on LWR is `community_builder:htmlEditor`, with the same `richTextValue`, drawn as written. The script, frame and embed flag follows what an Aura site strips; how LWR treats them was not tested on Testing LWR, so check an embed on the site before relying on it.
