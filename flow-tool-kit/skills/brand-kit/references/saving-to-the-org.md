# Saving the kit to the org

One step, right after the person confirms the kit: images, style values and the brand file. `orgsave.py` plans it from the org's current state, so a second run changes nothing that is already right.

## What the save needs

- A user who can create files and Asset Files, and edit the Form Style Defaults setting: a System Administrator, or a user with Customize Application and access to the Asset Library.
- Flow Tool Kit installed. The Default Logo fields came with a recent release; on an older org the plan lists them under `notInThisVersion` and the logo stays on each template until Flow Tool Kit is upgraded.
- The Asset Library (the Files library `sfdc_asset_company_assets`). Salesforce creates it; the plan stops if it is missing.

## The reads

`orgsave.py collect` (Claude Code) or the queries from `orgsave.py queries` (a connector) read:

| Read | Why |
|---|---|
| `SELECT Id FROM Organization` | The org row of the Form Style Defaults setting is keyed by the org Id |
| The Asset Library (`ContentWorkspace`) | Where every image and the brand file go |
| Every `ContentAsset`, and the `Checksum` of each one's latest `ContentVersion` | `Checksum` is the file's MD5, so an image already in the org is found without downloading anything |
| `ContentWorkspaceDoc` for the library | Which of those files are already in the library |
| The fields of `FlowToolKit__Form_Style_Defaults__c` and its org row (`SetupOwnerId` = the org Id) | Add-only needs the current values. It is a protected setting; when the read is refused, the save falls back to the import file |
| Brand files: `ContentVersion` titled `brand-kit...` with the `json` extension, and their text | A second save adds a version to the same file; a default brand file of another brand is a question, not an overwrite |

In chat, put the results in `org-state.json` in the shape `orgsave.py queries` prints (`stateShape`), then run `orgsave.py plan _brand/<slug> --state org-state.json --inline`.

## The writes, in order

### 1. Images: public Asset Files in the Asset Library

For an image the org already has (same checksum), nothing is uploaded: the kit takes that Asset File's name. If it is not public, `IsVisibleByExternalUsers` is set to true; if it is outside the Asset Library, a `ContentWorkspaceDoc` files it there. A packaged asset keeps its namespace in the name (`FlowToolKit__Background_Forest_Sunbeams`).

A new image:

1. `POST /sobjects/ContentVersion` with `Title` (the asset name), `PathOnClient`, `VersionData` (base64), `FirstPublishLocationId` (the Asset Library's Id) and `IsAssetEnabled: true`. This creates the file in the library and turns it into an Asset File in one call.
2. Read the new version's `ContentDocumentId`, then the document's `ContentAssetId`.
3. `PATCH /sobjects/ContentAsset/<Id>` with `DeveloperName` (the asset name), `MasterLabel` (a label a person recognizes, "Riverside Community Garden logo") and `IsVisibleByExternalUsers: true`, so guests on a site can see it.

An Asset File's `ContentDocumentId` cannot be set on insert, so creating a `ContentAsset` record directly fails; the flag on the version is the way. Asset names are letters, digits and single underscores, starting with a letter; a name the org already uses for another file gets `_2`.

Only PNG, JPG and SVG files appear in the Flow Tool Kit image picker. `brand_assets.py` converts anything else first.

**Why the Asset Library:** the image picker lists only files in it. A file outside the library, or an image deployed as a static resource, never shows up there, and a static resource is not public to guests.

**Folders.** The image picker groups images by their folder in the Asset Library. When the library already has folders (its `RootContentFolderId` is set), the save puts the brand's images in a folder named for the brand: it creates the folder under the library's root (or reuses one of that name), then moves each file by updating its `ContentFolderMember.ParentContentFolderId`. A library with no folders yet has no root to create one under through the API, so the images stay unfoldered and the plan says so; creating any folder once in Files, Libraries, Asset Library switches folders on. A folder failure is reported and stops nothing: the picker lists every image either way. Labels carry the brand's name, so brands stay easy to tell apart without folders too.

### 2. Style values: the org's Form Style defaults, add-only

Only for the org's default brand (`orgDefault: true`). Each value maps to one field of the setting, named after its Global Styles token (`--ftk-color-primary` is `FlowToolKit__Color_Primary__c`):

| Kit value | Token | Field |
|---|---|---|
| `colors.primary` | `--ftk-color-primary` | Color Primary |
| white text on it | `--ftk-color-on-primary` | Color On Primary |
| `fonts.bodyStack` | `--ftk-font-family` | Font Family |
| `fonts.headingStack` | `--ftk-font-family-heading` | Font Family Heading |
| `style.headingWeight` | `--ftk-font-weight-heading` | Font Weight Heading |
| `style.cornerRadius` | `--ftk-radius-medium` | Radius Medium |
| `style.buttonRadius` (when it differs) | `--ftk-button-radius` | Button Radius |
| `assets.logo`, `assets.logoAlt` | (not tokens) | Default Logo, Default Logo Alt Text |

The hover and pressed shades follow the brand color by themselves. Layout values (text size, spacing, border thickness) are not brand values; build-template sets those on each template.

For each field: blank takes the kit's value; the same value does nothing; a different value stays, and the plan reports it under `keptOrgValue`. The write is one `POST /sobjects/FlowToolKit__Form_Style_Defaults__c` (with `SetupOwnerId` = the org Id) when the org has no row yet, or one `PATCH` of the row.

**When the org refuses** the read or the write, the save writes `global-styles-import.json` and carries on. In Form Builder, open **Global Styles**, select **Import**, paste the file, **Preview import**, then **Save org defaults**. Import replaces every saved org style, so the file holds the org's current values plus the brand. When even the current values could not be read, the file holds only the brand: export the Global Styles first, then `python3 scripts/brandkit.py global-styles brand-kit.json --export exported.json --out global-styles-import.json` merges them. Set Default Logo in the same tab with **Select Image**.

### 3. The brand file

`brand-kit.json`, with the real asset names, as a private file (not an Asset File: it holds words, not images) in the Asset Library:

- Title `brand-kit` for the org's default brand, `brand-kit-<slug>` for another brand; `PathOnClient` `brand-kit.json`.
- First save: `POST /sobjects/ContentVersion` with `FirstPublishLocationId` = the Asset Library.
- Later saves: `POST /sobjects/ContentVersion` with the file's `ContentDocumentId`: a new version of the same file, so org-catalog always finds one.

org-catalog finds a saved kit from the setting's Color Primary or Default Logo, and from this file.

## What was proven in an org

In a scratch org (API version 62.0, a System Administrator): a version inserted with `IsAssetEnabled` and the Asset Library as its first location became an Asset File filed in the library; the rename, label and public flag took; the image picker's query listed it; a second save found both images by checksum, uploaded nothing and added version 2 to the brand file; the brand file's text read back through `/sobjects/ContentVersion/<Id>/VersionData`. The org reads (`collect`) ran against an org with Flow Tool Kit installed: the protected setting's fields and org row were readable through the API. Writing the setting through the API was proven by build-template in a subscriber org (insert, update, read). Not yet run in an org: the full save into a Flow Tool Kit org's setting, the brand folder step (no library in the test orgs had folders switched on; creating a folder with the library as its parent is refused), and a connector-driven save in chat.

## After the save

- `org-save.json` lists what was uploaded, reused, added, kept and any fallback.
- Check the images with the image picker's own query (SKILL.md) and in Form Builder's image picker.
- Open a site page or a guest form that shows the logo, to confirm guests can load it.
- Record the choice in `flow-tool-kit.json`: `brand_kit.choice` (`new` or `update`) and `found` (what was saved).
