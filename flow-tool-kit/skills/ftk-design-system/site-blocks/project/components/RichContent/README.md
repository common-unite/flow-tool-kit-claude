# RichContent

Formatted text, links and images, styled by the site theme.

**Maps to:** Rich Content Editor (`forceCommunity:richTextInline`). The one prop is `richTextValue`, the HTML Builder stores. Headings, paragraphs and links take the theme's fonts and link color.

## Notes
- Use it for copy that is a page's own: an intro, a policy, contact details. For a styled band with a heading and a button, use a block instead.
- Rich text keeps inline styles but not scripts or embeds; use the HTML Editor for markup.

## On LWR

Rich Content Editor on LWR is `community_builder:richTextEditor`, with the same `richTextValue`. Headings in it render at body size and weight, as Testing LWR shows them, because LWR does not style them. On an LWR page, set a heading with a block's header or a Section Header rather than an `h1` in rich text.
