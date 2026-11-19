# Form-type rules: header, buttons, indicator, page headings, first page

The one table every Flow Tool Kit form follows: form-design, build-template, build-form-component, form-migrate and ftk-start's brief mode all read it. Variety between forms comes from sections, images, field shapes and capabilities, never from breaking a row.

Pick the row from the form's kind, page count and length. **Long** means an application or grant with three or more pages, or any other form with three or more pages and about 10 minutes or more, counted as the pages' Estimated Time added up. "Banner" always means the Banner section in the template header, never a page header repeating the title.

| # | Form | Header | Buttons | Indicator and stages mode | Page headings | First page |
|---|---|---|---|---|---|---|
| 1 | Survey, one page | Banner Compact, Small, placement `singleCardHeader` | Footer bar, `spread`. Submit label Submit Survey | Hidden (`Hide_Stage_Indicator__c`). Stages off. Each question section is a Survey Section | None | A meaningful label. No intro page |
| 2 | Survey, two or more pages | Banner Overlay, Small; `singleCardHeader` without the vertical indicator, `header` with it | Two pages: Footer bar, `spread`. Three or more: Docked. Continue on every page, Submit Survey on the last | Two pages: hidden. Three or more and long: row 6. Three or more and shorter: plain pages, `base` indicator, review screen off | None; a page header only for a page that needs its own title | A meaningful label, never Welcome |
| 3 | Simple single-page form (contact, sign-up, request) | Banner Compact, Small, `singleCardHeader` | Footer bar, `spread` | Hidden. Stages off | None | A meaningful label; no cover page |
| 4 | Two pages (details, then a release or a second task) | Banner Overlay, Small, `singleCardHeader` | Footer bar, `spread`. The forward button reads Continue | Hidden. Stages off | None | A meaningful label |
| 5 | Three or more pages, not an application or grant, not long (registration, intake, onboarding) | Banner Overlay, Small, `singleCardHeader`: the indicator sits above the page, so the banner stays flush with square bottom corners | Docked, `spread`. Continue on every page | `Stage_Indicator_Type__c` `base` (it shows on phones, where path hides). Stages off | None: the indicator already shows position | A meaningful label. As a rule no intro page |
| 6 | Long: an application or grant with three or more pages, or any form with three or more pages and about 10 minutes or more, long surveys included | Banner Overlay, Small, placement `header`, and `Stage_Mode_Layout__c` Display Template Header so the banner sits above the stage list | Docked, `center`, with Save Progress. Inside a step the package shows Return, Save Progress, Mark Complete; the overview shows Save Progress | Stages mode, Save Progress, `vertical` indicator, review screen | Stage rows show each page's label, description and minutes; every section titled with a one-line subtitle | The one valid place for an intro page, and only when it helps: an About the Program or Learn More page before the application, button Learn More or Get Started. Question stages are named for what they ask, button Start Step |

On every row:

- every page has a description of at least two sentences, and every section a title and a one-line description (headerless only for a follow-up or a note);
- a page break needs a stated reason;
- a form of consents and terms closes with the electronic signature;
- payment stays its own step when that is the workflow;
- no path indicator on a Form Template page, and no `footer base` or `footer path`;
- no "Page N of M" heading anywhere: the indicator or the stage list already shows position, and one- and two-page forms need none;
- the forward button reads Continue, never Next;
- most forms need no intro page; never leave a page labelled Welcome.

## Why each choice

- **Footer bar on one or two pages, Docked on three or more:** a short form ends where the card ends; on long pages the docked bar stays in reach.
- **Base indicator on short multi-page forms:** it shows on phones, where the path indicator hides. The vertical indicator belongs to stages mode.
- **Stages mode for long forms:** people finish long applications over several sittings, so they need Save Progress, a start screen with each step's minutes, and a review before submitting.
- **Square bottom corners without the vertical indicator:** the banner is the top of the form card; only beside the vertical indicator does it stand alone with rounded corners.
- **Templates keep the default theme:** a brand goes in Form Style values, which an admin can still change in the Style Editor. A template never gets its own new Form Theme record.
