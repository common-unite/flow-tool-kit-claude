# Search

The site search box with its brand button, placed in a column. The theme header carries its own.

**Maps to:** Search (`forceCommunity:searchBox`). Props are its Builder attributes; the design uses `placeholder` (Placeholder Text). Autocomplete and result settings (`enableAutocomplete`, `maxNumberOfResults`, `crossObjectTypeaheadApiNames`) change what it finds, not how it looks.

On a phone the field collapses to a search icon, as the site draws it.

## On LWR

Search on LWR is the Search Bar, `dxp_search:searchInput` (the name was confirmed by deploying it to a test org). Testing LWR keeps Builder's defaults: a search icon, no placeholder, no button. `placeholder` and `buttonLabel` are Aura settings; the LWR attribute names for them are not confirmed, so an LWR design shows the default. The site also needs a Search Results page for the bar to go anywhere.
