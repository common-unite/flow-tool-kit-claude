# Diagnosis: from the message to the cause

## What the person sees, and what it means

| What the person sees | Cause | Fix |
|---|---|---|
| "You do not have the level of access necessary to perform the operation you requested" on a flow, Flow Section or page | The flow is not restricted, or no permission set the running user holds grants it | SKILL.md steps two and three, then a new session |
| "You do not have permission to run this form's save process" | The running user cannot run the save flow. Most often an active save override that their permission sets do not grant | Grant the flow that runs (the override) to that audience's set |
| "could not be updated with your current access", "do not have access to save" | A guest saved a second time (Save Progress, Stages or Autosave) with no save override active | [guest-save-and-resume.md](guest-save-and-resume.md) |
| "linked to a record you do not have access to" | A URL parameter or prefill passes a record the guest cannot read | Stop passing that record; it is not on its own a reason for the save override |
| "Save Failed" with `DUPLICATE_VALUE` on Unique Id | The person saving cannot see their own earlier submission, so the save tried to create it again. Nothing was saved and no duplicate was made | Guests: the save override. Portal users: share the submission with them |
| Save Progress fails with "An error occurred while trying to update the record", or Submit saves nothing, for a portal or staff user only | They hold only Form (Flow User), which has no Edit on Form Submission | [audiences.md](audiences.md): Edit for portal users, Form Builder Internal User for staff |
| "...this form's pre-fill template is not shared with you" | No guest rule on Form Submission for Pre-fill Templates | [guest-sharing.md](guest-sharing.md) |
| Nothing, or "You can't view this form", for guests | No guest rule on Form Template, or the template or the site is not active | [guest-sharing.md](guest-sharing.md) |
| A blank header or section for guests | No guest rule on Form Component for record components | [guest-sharing.md](guest-sharing.md) |
| A resume link opens a new form with a notice | The guest cannot read the saved draft: no system-mode resume copy named on that template | [guest-save-and-resume.md](guest-save-and-resume.md) |
| A picker, list or choice is empty for guests and full for staff | Record access: no guest sharing rule for those records, or no Read on the object | [guest-sharing.md](guest-sharing.md) |
| The fix is in place and it still fails | The guest session started before the fix | A new private window, or `https://<site domain>/<site path>/secur/logout.jsp` |

## The debug log

A flow refused for access starts and stops at once: the log shows `FLOW_CREATE_INTERVIEW_BEGIN` (or a bare `FLOW_CREATE_INTERVIEW_END` when Apex started it) and nothing from the flow's elements. When the log says nothing useful, the error code is in the page's network response, not in the log. Either way, go to the two steps; do not read object or field access first.

## The checks as queries

`python3 scripts/flowaccess.py queries --flow <Flow_Api_Name> --site <Site_Name> --object <Object>` prints all of them. Run them through the Salesforce connector in chat, or let `diagnose` run them in Claude Code. A packaged flow is named with its prefix (`FlowToolKit__Form_Submission_Upsert`); in queries, `ApiName` is the name without the prefix and `NamespacePrefix` holds the prefix.

| Check | Query | Read it as |
|---|---|---|
| The flow, and whether something overrides it | `SELECT DurableId, ApiName, NamespacePrefix, IsActive, ActiveVersionId, IsOverridable, OverriddenById FROM FlowDefinitionView WHERE ApiName = 'Form_Submission_Upsert' AND NamespacePrefix = 'FlowToolKit'` | `OverriddenById` is filled only while an override is active. Then the override is what runs: check it instead |
| Overrides that are not active yet | `SELECT ApiName, IsActive FROM FlowDefinitionView WHERE OverriddenFlowId = '<DurableId>'` | A draft override changes nothing until it is activated |
| Step one: restricted | Tooling API: `SELECT Metadata FROM Flow WHERE Id = '<ActiveVersionId>'` | `Metadata.isAdditionalPermissionRequiredToRun` must be true. No Tooling API in the connector: read the setting in Flow Builder |
| The run mode | `SELECT Status, RunInMode, ApiVersion FROM FlowVersionView WHERE DurableId = '<ActiveVersionId>'` | `DefaultMode` or a system mode |
| Step two: who grants the flow | `SELECT Parent.Name, Parent.IsOwnedByProfile, Parent.Profile.Name FROM SetupEntityAccess WHERE SetupEntityType = 'FlowDefinition' AND SetupEntityId = '<DurableId>'` | The permission sets (and profiles, as their own sets) that grant it |
| The guest user | `SELECT Name, MasterLabel, GuestUserId, Status FROM Site WHERE Name = '<Site_Name>' OR MasterLabel = '<Site_Name>'` | `Name` is also the name guest sharing rules use for the site |
| What the running user holds | `SELECT PermissionSetId, PermissionSet.Name, PermissionSet.IsOwnedByProfile, PermissionSet.PermissionsRunFlow FROM PermissionSetAssignment WHERE AssigneeId = '<user Id>'` | Includes the profile's own set. Step two passes when one of these grants the flow |
| Sharing model | `SELECT QualifiedApiName, InternalSharingModel, ExternalSharingModel FROM EntityDefinition WHERE QualifiedApiName IN ('Campaign')` | External Private: portal users need sharing. Guests always need a guest rule, whatever this says |
| Object and field read | `ObjectPermissions` and `FieldPermissions` where `ParentId` is in the user's sets | Read on the object and every field the flow uses |

Guest sharing rules are metadata and no SOQL reaches them: retrieve `SharingRules:<Object>` in Claude Code, or read Setup, Sharing Settings, the object's Sharing Rules list, in chat.

A grant inside a permission set group: check the group's component sets; the assignment lists the group.

## Looking further, in order

1. **Subflows.** `flowaccess.py inspect <flow file>` lists every subflow. Each needs both steps for the same audience; a missing one fails with the same message, from inside the parent.
2. **Apex actions.** `inspect` lists each Apex action. A custom invocable needs Apex Class Access in the audience's set (`grant --apex <Class>`). Flow Tool Kit's packaged actions come with Form (Flow User).
3. **Object and field access.** Read on every object the flow reads and every field it shows or filters on; Create on what it creates. Guests can never hold Edit or Delete on an object.
4. **Record access.** Guests: [guest-sharing.md](guest-sharing.md). Portal users: the object's external sharing model, then sharing sets and sharing rules. Staff: the internal model and their role.
5. **The flow's own logic.** Only now read the flow's elements and its fault paths.

Report each finding with its consequence first: "guests cannot run Workshop Picker: it is not restricted", not the other way round.
