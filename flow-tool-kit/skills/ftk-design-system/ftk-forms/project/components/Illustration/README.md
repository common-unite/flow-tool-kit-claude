# Illustration

An empty-state or confirmation picture with a heading and a short message, using the SLDS illustrations the package ships.

**Maps to:** the `displayIllustration` component (`displayIllustrationArt`). Hand-written from `displayIllustration`; the art in `components/lib/ftk-illustrations.js` is copied unchanged from the package.

## Props
- `type`: one of the package's 23 scenes: `Base`, `Camping`, `Maintenance`, `Desert`, `Road`, `No Access`, `Balloon`, `Lightning`, `Axe`, `Not Available`, `Fishing`, `Mountain`, `No Events`, `No Tasks`, `Setup`, `Gone Fishing`, `No Access #2`, `No Content`, `No Preview`, `Preview`, `Research`, `Approval`, `Spinner`. The list is exported as `FTK.ILLUSTRATION_TYPES`. <!-- partner-clean: allow R4 -->
- `size`: `small` (default; art at most 300 by 200) or `large` (600 by 400).
- `title` (a 20px heading) and `subtitle` (rich text, 13px).
- `topMargin` / `bottomMargin`: SLDS margin classes, as on `DisplayImage`.

## Notes
The art uses SLDS's own light blues (`#90d0fe`, `#cfe9fe`) and does not follow the brand; `Approval` is a teal check. `Spinner` is a brand loading spinner that covers the whole screen in the package (it pairs with auto-navigate); the preview keeps it in its box. `Spinner` exists only on the Display Illustration screen component (`displayIllustration`); an illustration section (`Illustration_Type__c`) offers the other 22 scenes, so never put `Spinner` in a form section. Use `Approval` or `Balloon` for a thank-you page and `No Access` or `Not Available` for a closed form. <!-- partner-clean: allow R4 -->
