# ConfirmModal

**Flow screen only.** These confirm dialogs exist only for custom buttons on the Buttons component (`buttonsCustom`) placed on a Flow screen. A Form Template's Back, Save Progress, Continue and Submit buttons never open one, so don't draw it in a template design.

The confirm dialog a button opens before it runs, such as "Submit your application?".

**Maps to:** `buttonsCustom` with `enableModal`, drawn by `c-modal`. The fields are `modalHeading`, `modalSubheading`, `modalBody` (rich text), `modalConfirmButtonLabel` (default Confirm) and `modalCancelButtonLabel` (default Cancel). `modalTheme` colors the header band: `slds-theme_default`, `shade`, `inverse`, `alt-inverse`, `success`, `info`, `warning`, `error` or `offline`, always with the alert texture.

On `Buttons`, pass `confirmModal` (true, or these props) on a Flow screen design, or give a custom button in `buttons` its own `confirmModal`.

## Props
- `heading`, `subheading`, `body`, `confirmLabel`, `cancelLabel`, `theme`, `inline` (draws in place, for previews), `onConfirm`, `onCancel`.
