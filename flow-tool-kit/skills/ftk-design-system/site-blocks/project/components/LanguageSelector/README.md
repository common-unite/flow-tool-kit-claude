# LanguageSelector

The site language picker: the current language with a menu of the others.

**Maps to:** Language Selector (`forceCommunity:languagePicker`). It has no settings of its own; the languages come from the site's language settings. `languages` lists them for the design (the first is current, or set `current`).

It renders nothing when the site has one language, as the site does. Usually it sits in a narrow column or the header.

## On LWR

Language Selector on LWR is `dxp_base:languageSelector` (confirmed by deploying it), drawn as a neutral button menu naming the current language. As on Aura it shows only when the site has a second language; Testing LWR has Spanish for that.
