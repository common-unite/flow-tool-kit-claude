# The fixes as clicks

For chat without a deploy, or a person who prefers Setup. Each step names where to click; menu labels can move between Salesforce releases, so describe what to look for when the person cannot find a label.

## Step one: restrict the flow

1. Setup, Flows, open the flow in Flow Builder.
2. Open the flow's properties (the gear), then **Show Advanced**.
3. Check **Override default behavior and restrict access to enabled profiles or permission sets**.
4. **Save as New Version**, then **Activate**.

Do the same for every subflow it calls.

## Step two: grant the flow

1. Setup, Permission Sets, open the audience's own set (for guests, **Form Flow (Guest User)**). No set yet: **New**, label it, leave **License** as None for a guest set, Save.
2. **Flow Access**, **Edit**, move the flow to Enabled Flows, **Save**.
3. Apex actions the flow calls: **Apex Class Access**, **Edit**, add the class, **Save**.

## Assign the set to the site's guest user

1. Experience Builder for the site, **Settings**, **General**, the **Guest User Profile** link.
2. **View Users**, open the guest user.
3. **Permission Set Assignments**, **Edit Assignments**, add **Form (Flow User)** and the org's guest set, **Save**.

## A guest sharing rule

1. Setup, **Sharing Settings**.
2. Find the object's **Sharing Rules** list, **New**.
3. Label and rule name as proposed; **Rule Type: Guest user access, based on criteria**.
4. Criteria: the proposed field, operator and value, one row each.
5. **Share with**: the site's guest user.
6. **Access Level: Read Only**. **Save**.

## The guest save override

Only when a guest form uses Save Progress, Stages or Autosave; otherwise leave the packaged flow in place. Check first that Setup, Flows does not already list **(Form) Upsert | Guest Override** (the installer may have added it, inactive). If it does, open it, review it with the person, and Activate.

1. Setup, Flows, open **(Form) Upsert | Overridable**.
2. **Save As**. Flow Builder offers **Save as flow override** for this flow; choose it.
3. Label `(Form) Upsert | Guest Override`, API name `Form_Submission_Upsert_Guest`, a description saying what it is for and why it runs in system context (the text `guest-copy` writes is a good start).
4. Flow properties, **Show Advanced**, **How to Run the Flow: System Context Without Sharing, Access All Data**. Confirm "Override default behavior and restrict access" is still checked.
5. **Save**. Before asking for the yes, say: "Once this override is active, every save in the org runs through it in system mode: guests, portal users and staff, on every form, not only this one." Activate on the yes.
6. Step two: grant it in the guest's set, and in every other audience's set.

## The guest resume copy

1. Setup, Flows, open **(Form) Prefill | Template**.
2. **Save As**, **A New Flow**: label `(Form) Prefill | Guest Resume`, API name `Form_Submission_Prefill_Guest`, a description.
3. Flow properties, **Show Advanced**: **How to Run the Flow: System Context Without Sharing, Access All Data**; check "Override default behavior and restrict access" is on.
4. **Save**, then Activate on the person's yes.
5. Setup, Object Manager, **Form Template**, Fields & Relationships, **Prefill Flow**, **New** under Values: value `Form_Submission_Prefill_Guest` exactly, label `(Form) Prefill | Guest Resume`. Save.
6. Grant the copy in the guest's set (step two).
7. On each Form Template whose guests resume, set **Prefill Flow** to the copy.

## Edit for portal users

1. Setup, Permission Sets, **New** (for example "Form Portal User"), with the license your members hold.
2. **Object Settings**: Form Submission, Edit; Form Submission Stage, Edit. Save.
3. Assign it to every member who fills in forms, beside Form (Flow User). Never to the guest user.

## Test in a new session

A private window where nobody is signed in, or sign the guest out at `https://<site domain>/<site path>/secur/logout.jsp` first. A session opened before a change keeps failing.
