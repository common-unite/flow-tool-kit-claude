# Icon

Any of the 1,764 Salesforce Lightning Design System icons (SLDS 2.30.7), by the same name a FlowToolKit section, divider or field stores.

**Maps to:** `lightning-icon`. Icons are the SLDS artwork from `@salesforce-ux/design-system@2.30.7`, artwork unchanged, licensed CC BY-ND 4.0 (see `assets/Icons/License-for-icons.txt`). They load from `components/lib/slds-icons-2.30.7.js` as `window.SLDSIcons`.

## Props
- `name`: `category:name`, for example `utility:location`, `standard:account`, `action:approval`, `custom:custom14`, `doctype:pdf`. The Icon card in this system is a searchable browser of every icon: filter by category, search by word, and click an icon to copy its name. <!-- partner-clean: allow R4 -->
- `size`: `xx-small` (14px), `x-small` (16px), `small` (24px, default), `medium` (32px), `large` (48px), or a number of px.
- `variant`: defaults to how `lightning-icon` draws the category. `utility` icons are bare `glyph`s in `color`; `standard`, `action` and `custom` icons sit on their own colored `tile` with a white glyph; `doctype` icons keep their own colors. Pass `glyph` or `tile` to override.
- `color`: glyph color. Defaults to the surrounding text color.
- `title`: makes the icon announce itself; without one it is decorative.

## Notes
Use `utility:` icons for section headers and dividers: they fill the box edge to edge, which is how FlowToolKit's headers look. `standard:`, `action:` and `custom:` icons are drawn for SLDS's colored tile and carry built-in padding, so as glyphs they look about 40% smaller; they draw on their tile by default. The section header draws its icon as a glyph in `headingIconColor__c`, or `brand` with no theme.

## White-filled sprite glyphs
Thirty utility glyphs in the SLDS 2.30.7 sprite (`utility:alt_lock`, `alt_unlock`, `alt_agent_astro`, `recent`, `recenter`, `two_way`, `data_governance`, the `slack_*` and `table_*` sets, and a few others) give every shape `fill="#fff"`, so drawn straight from the sprite they are white on white. `lightning-icon`'s own templates carry no fill for them and draw them in the current color, so this system does the same.
