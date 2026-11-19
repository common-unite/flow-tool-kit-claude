# Brand, letterhead and images

Every email of an organization shares one letterhead: the brand bar with the logo and the organization's name, an optional banner photo, a 16px body, one button, and a footer with the tagline and contact details. It is the same markup form-design draws on the review canvas, so what was reviewed is what is deployed.

## Where the look comes from (first match wins, key by key)

1. The plan's own `style`, `assets` and `emails.letterhead` (form-design wrote them from the brand kit the person chose).
2. The saved brand file, `brand-kit.json` in the Asset Library: `colors` (`primary`, `heading`, `accent`, `background`), `fonts` (`body`, `heading`), `assets` (`logo`, `logoAlt`, `banner`) and `brandName`. Pass it with `--brand`, or pass org-catalog's catalog with `--catalog` and the brand file it read is used.
3. The org's Form Style defaults (Brand color, Font, Heading font, Default Logo and its alt text), from the catalog.
4. Flow Tool Kit's neutral palette, the same one form-design falls back to. No brand kit is fine.

`style` keys: `brand` (the bar and button), `heading_color` (headings and footer), `background` (around the card), `font`, `heading_font` (or the full `font_css`, `heading_font_css`), `Corner radius` (the button). White text sits on `brand` and `heading_color`, so both need at least **4.5:1** contrast with white; the build warns below that and the fix is a darker shade in the plan's style.

## Images: Public Asset Files only

A mail client loads an image from the open internet, without signing in. The address that works is a **Public Asset File**'s:

```
<My Domain URL>/file-asset-public/<asset name>?oid=<org Id>
```

- `<My Domain URL>` is the org's address up to `.my.salesforce.com` (in a sandbox it includes the sandbox name). In Claude Code, `sf org display --target-org <org-alias>` shows it as the Instance Url. In chat, ask the person for it (Setup, My Domain).
- `<asset name>` is the Asset File's name. A packaged asset carries the namespace (`FlowToolKit__Background_Forest_Sunbeams`); the bare name redirects and draws nothing. The build adds it from the asset's NamespacePrefix.
- The asset must be visible to external users (`IsVisibleByExternalUsers`). The build refuses one that is not.
- The address contains the org's own domain and Id, so a template built for a sandbox shows the sandbox's images. **Build again for each org**, from that org's context, before deploying there.

Load new images into the Asset Library first (the brand-kit skill does this, as Public Asset Files). Then read them for the org context:

```sql
SELECT DeveloperName, NamespacePrefix, IsVisibleByExternalUsers FROM ContentAsset
```

`emailbuild.py check-images build.json` fetches each address and fails unless it answers with an image. It needs network access to the org's domain: run it in Claude Code; in chat, the test email is the check.

Never point an email image at a Lightning or site address (`/sfsites/c/file-asset/...`, `lightning.force.com`) or at a static resource: those need a signed-in session or a site, and the image is blank in the inbox. An image already on the organization's public website can be used as a full `https://` address in `assets`; the build accepts it with a warning.

## Letterhead keys (`emails.letterhead`)

| Key | What it is |
|---|---|
| `org` | The organization's name in the brand bar |
| `logo_alt`, `banner_alt` | Alt text for the logo and banner |
| `tagline` | One line in the footer |
| `address`, `email`, `site`, `site_label` | Footer contact details; `site_label` is the link text |

Keep the letterhead identical across an organization's forms. A shared Save Progress template is only shared when its letterhead matches in every plan; the build says so when it does not.
