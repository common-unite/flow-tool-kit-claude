# SurveyQuestion

One question at a time in survey mode: each question sits in its own card, and the one in focus lifts.

**Maps to:** `formSurveyQuestion` inside `formSurveyScope`, turned on per page section with `Survey_Section__c`.
- The meta row shows "Question {n} of {total}" (only when total is over 1) and two pills: **Required** (red on pink) and **Answered** (green with a check).
- The active card takes the brand border and a lifted shadow, and grows slightly toward the respondent.
- The other cards sit under a white veil at 90%. Clicking one makes it active.
- **Next** is brand on the active card and neutral elsewhere.

Wrap the field component. A Likert matrix wraps its whole section (`section`).

## Props
- `active`, `position`, `total`, `required`, `answered`, `showNext`, `nextLabel`, `section`, `scale`, `onNext`, `onActivate`.
- `SurveyScope`: the run of questions.

## Not in the package
Quiz answer feedback (correct or incorrect marks) is not drawn by any component. `picklistOptionScores__c` only feeds Likert scoring.
