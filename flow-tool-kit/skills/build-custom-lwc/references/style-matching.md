# Matching the form's look

A custom section component looks like the rest of the form through two mechanisms the package already has. Importing Flow Tool Kit's style sheets is not one of them: its style modules are internal to the package, so a component in your org cannot import them.

## 1. Wrap the inputs in the package's own form

Render the admin's form inside the component with `<FlowToolKit-flow-form is-extension ...>` ([house-pattern.md](house-pattern.md)). On connect, that form asks the nearest Flow Tool Kit style owner for its styles with a composed event that crosses shadow boundaries, and the Form Template answers (on a Form Component section, the surrounding form does). Every input, label, section and button inside then follows the template's Form Style settings and theme. Nothing to write.

## 2. Use the style variables for anything else you draw

The Form Template sets its resolved Form Style settings, its theme's Brand color and its border color as CSS custom properties on its container. Custom properties inherit through shadow DOM, so your CSS reads them directly:

```css
.fee-card {
    padding: var(--ftk-section-padding, calc(0.75rem * var(--ftk-layout-spacing-scale, 1)));
    border: var(--ftk-section-border-width, var(--ftk-border-width, calc(1px * var(--ftk-border-scale, 1)))) solid var(--ftk-section-border-color, var(--ftk-color-border, var(--borderColor, #dddbda)));
    border-radius: var(--ftk-section-radius, var(--ftk-radius-medium, calc(5px * var(--ftk-radius-scale, 1))));
    background: var(--ftk-section-surface, var(--ftk-color-surface, #ffffff));
}
.fee-card__amount { color: var(--ftk-color-primary, #0176d3); }
.fee-card__note { color: var(--ftk-help-color, var(--ftk-color-text-muted, #5c5c5c)); font-size: var(--ftk-help-font-size, 0.8125rem); }
```

When the admin changes the brand color, a border or a corner radius in Form Style settings, the card follows with no deploy.

Rules, all checked by `scripts/check_lwc.py`:

- **Only the Form Style settings** listed in [style-variables.md](style-variables.md), plus the theme's `--borderColor` and a section theme's `--labelColor`. Never `--_ftk-` names, never other `--ftk-` names you find in the inspector.
- **Always a fallback.** A variable exists only where an admin or a theme set it. Fall back the way the package does: the specific setting, then the general one, then a plain value (`--ftk-section-radius`, then `--ftk-radius-medium`, then `5px`).
- **Scale settings are multipliers**: `calc(1rem * var(--ftk-font-scale, 1))`.

Common choices:

| You are drawing | Use |
|---|---|
| A brand accent, a highlighted amount | `--ftk-color-primary` (text on it: `--ftk-color-on-primary`) |
| A card or panel | `--ftk-section-padding`, `--ftk-section-radius`, `--ftk-section-border-width`, `--ftk-section-border-color`, `--ftk-section-surface`, `--ftk-section-shadow` |
| Body text | `--ftk-color-text`, `--ftk-font-family`, `--ftk-font-size` |
| A label | `--ftk-color-label`, `--ftk-font-size-label`, `--ftk-font-weight-label` |
| A heading inside the card | `--ftk-font-family-heading`, `--ftk-font-size-heading`, `--ftk-font-weight-heading` |
| Help or a note | `--ftk-help-color`, `--ftk-help-font-size` |
| An error | `--ftk-color-danger` |
| A divider line | `--ftk-color-border-muted`, `--ftk-border-width` |

## 3. Let Lightning's own components take the brand

A brand theme also sets Lightning's styling hooks for buttons, inputs, checkboxes and toggles on the template. A `lightning-button` with `variant="brand"` inside your component is the brand color without any CSS. Prefer base components to hand-styled buttons.

## Check it

Look at the section in the template's Preview Form twice: once with the org's default look, once after changing the Brand color and the section corner radius in the template's Style Overrides. The card must follow both changes, and must still look right with no Form Style settings at all (the fallbacks). On an Experience Cloud site, check an Aura and an LWR site if the form is on both; an LWR site shows a change only after it is published.
