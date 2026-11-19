# Address

A compound address: an address search box over Street, City, State/Province, Zip/Postal Code and Country.

**Maps to:** an Address compound field (or its parts by `addressFieldType__c`), drawn by `flowFormFieldAddress` as `lightning-input-address` with `show-address-lookup`. Hand-written from `flowFormFieldAddress`.

## Layout
It follows `lightning-input-address` (en-US order; `fieldsLayout.js` widths), which `flowFormFieldAddress` renders with `show-address-lookup`:

| Org setting | Rows |
| --- | --- |
| State and Country picklists **off** | Address search (no label, placeholder only) · Street, a two-line text area (12) · City (8) beside State/Province (4) · Zip/Postal Code (8) beside Country (4). State and Country are text inputs |
| State and Country picklists **on** | Address search · **Country** picklist (12, moved to the top) · Street (12) · City (8) beside State/Province picklist (4) · Zip/Postal Code (12) |

With picklists on, the State/Province picklist lists the chosen country's states and stays hidden until a country with states is picked (`hide-province`); City then runs full width. When the org has only one country, the package passes no country options, so Country is a text input holding that country while State/Province is still a picklist. The order changes for other locales (the package sets `locale` from the chosen country). The parts stay side by side down to about 320px.

## Props
- `label` (default `Address`), `value` / `defaultValue` (`{street, city, province, postalCode, country}`), `onChange(address)`.
- `showLookup` (default true) and `lookupPlaceholder` (default "Search For Address"); `suggestions` (`{label, sublabel, address}`) fill the parts when picked. `open` and `searchValue` show the suggestions for mockups.
- `countries` (options): pass two or more to show State and Country picklists turned on in the org; Country becomes a dropdown at the top and `provinces` (an array, or `{countryValue: options}`) fills State/Province for the chosen country. One country: a Country text input holding it. None: picklists off.
- `hideProvince`: drop State/Province.
- `labels` and `placeholders` (`{street, city, province, postalCode, country}`): the per-part `customLabel__c` and `placeholder__c`.
- `required`: true for every part, or `{street, city, province, postalCode, country}` (each part's own field requiredness).
- `readOnly`: the formatted address with a static map (`lightning-formatted-address show-static-map`). `showStaticMap` false hides the map.
- `disabled`, `error`, `helpText`, `helpTextDisplay`, `labelSize`, `labelHidden`.

## Notes
The search is Salesforce's address lookup, so suggestions come from the platform, not from a list you configure. In review mode the parts show as five separate review lines.

## Prototypes
Always draw an address with this component. The package can also show one part of an address as its own field (`addressFieldType__c` = `Street`, `City`, `State`, `PostalCode`, `Country`), but a prototype should not split an address that way: use the full Address section and note any part the client wants hidden in the handoff.
