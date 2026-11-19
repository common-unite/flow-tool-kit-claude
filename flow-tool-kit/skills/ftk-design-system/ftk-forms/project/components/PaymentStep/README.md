# PaymentStep

The payment page of a Form Template that takes payment: the FlowToolKit Stripe Connector's payment form, drawn the way it renders.

**Maps to:** `Payment_Required__c`, with `Payment_Conditions__c` and `Price_Book__c`. The payment step is its own page after the last form page. `formTemplate` loads `stripePaymentForm` from the Stripe Connector; that component shows `flowStripePayment`, an iframe of the `StripePaymentForm` Visualforce page, which mounts Stripe's **Payment Element** (`layout: "tabs"`).

## What it looks like, and why
- The page inside the iframe uses plain SLDS (`apex:slds`) and gets no Form Style or Form Theme. The heading, boxes and the full-width **Pay Now** button (2.5rem tall) are stock SLDS, so the button is Salesforce blue, not the form's brand.
- The Payment Element uses Stripe's default appearance (the page sets an empty `appearance`): Stripe's own inputs, labels and tabs, and Stripe blue for the selected tab.
- Which tabs appear (Card, US bank account, Cash App Pay, and so on) comes from the Stripe account's payment method configuration. With only one method there are no tabs. Embedded forms are limited to Card and Link.

## Settings
| Setting | Prop | Effect |
| --- | --- | --- |
| Settings \| Hide Header | `hideHeader` | Hides the "Payment details" heading |
| Billing address | `enableAddress` | Adds **Billing info** (Stripe Address Element, billing mode) at 7 of 12 on the left on wide screens (half at medium, full width on phones) |
| Link | `enableLink` | Adds **Contact info** (Link Authentication Element) under the payment box |
| Settings \| Display Express Checkout | `expressCheckout`, `expressCheckoutButtonType` | Replaces the form with one-click wallet buttons (Apple Pay, Google Pay, PayPal, Link). Button Type: `donate`, `book`, `order`, `plain`, `subscribe`, `buy`, `checkout`, `pay` |
| Payment mode | `mode` | `payment` (Pay Now), `subscription` (Confirm Subscription), `setup` (Save Card) |

Either Billing info or Link, or a hidden header, shows the "Payment" heading over the payment box. A failed payment shows Stripe's message in the red alert above the form (`paymentMessage`). When Stripe can't load, or the Connector isn't installed, the template shows Payment Unavailable (`error`). After payment, the `ConfirmationPage` carries View Receipt.

## What a payment page design holds
Only the template's header (the Banner) and this Stripe block. The payment step has no page of its own to configure, so a design adds no amount summary, info note, rich text or any other custom block to it; the amount and receipt come from what the Stripe block shows. The last form page's submit button reads **Continue to Payment** when payment is required, and Submit Application (or the template's Submit label) when nothing is due. Package gap: the template has one `Submit_Button_Label__c`, so the payment label needs a conditional label or a package addition; flag it in the handoff.

## Why it's a redraw, not the real Stripe Element
Stripe's Payment Element can't be loaded here: Stripe.js has to come from js.stripe.com with a publishable key and a live Elements session, and an artifact page can load scripts only from a few public CDNs. The redraw follows the Payment Element's default layout. Card brand marks are drawn as plain chips, and wallet buttons as labelled stand-ins.

## Props
- `mode`, `buttonLabel`, `hideHeader`, `enableAddress`, `enableLink`, `expressCheckout`, `expressCheckoutButtonType`, `tabs` (payment method types, default `['card', 'us_bank_account', 'cashapp']`), `selectedTab`, `paymentMessage`, `error`.
- `StripePaymentElement` draws the Payment Element alone: `tabs`, `selected`.
