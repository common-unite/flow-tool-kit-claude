# Carousel

A form shown one section at a time, with a progress indicator under the section and Back / Continue buttons, Finish on the last section. Use it for short, focused steps inside a single form.

**Maps to:** a Flow Form whose `FlowToolKit__type__c` is `carousel` (flowForm `displayAsCarousel`). Each slide is one form section; the base progress indicator lists the section titles.

| Part | Renders |
| --- | --- |
| Slide | The section's fields on the 12-column grid |
| Progress | A base progress indicator under the slide, one step per section; earlier steps show complete |
| Buttons | Back (neutral, `utility:back`) and Continue (brand, `utility:forward`); Finish on the last section. Continue is disabled while the section has errors |

## Props
- Children: one `Tab` per section (`label`, `invalid`, and the section content), or `tabs: [{ label, value, invalid, content }]`.
- `value` / `defaultValue` (the section showing), `onChange(value)`.
- `backLabel`, `nextLabel`, `finishLabel`, `onFinish`. Defaults Back, Continue, Finish.

## Notes
A carousel is not a tab style, even though the package builds it from the same form sections as a tabset. For a multi-page experience with page navigation, use a Form Template instead.
