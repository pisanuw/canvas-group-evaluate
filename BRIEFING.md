# canvas-group-evaluate

Generate a Google Form for DYOP peer + self evaluations from a Canvas
group set roster.

## Scope

- Pull group + member roster from Canvas (course/group-set IDs as CLI args)
  or read it from a local CSV/TXT file.
- Emit a Google Apps Script (`build_form.gs`) that, when pasted into
  script.google.com under the user's UW account and run, creates a single
  Google Form.
- The form is domain-restricted to `uw.edu` (Google login = UW NetID),
  collects respondent email, and uses section navigation so each student
  picks their group then sees rubric blocks for each teammate (incl. self).

## Decisions

- One form total for the whole class (group + member selection inside the form).
- Standard peer-evaluation rubric: 5 Likert items (1-5) + 2 open-text items
  per teammate.
- Google Apps Script (no GCP OAuth setup required).
- Canvas token read from `/Users/pisan/local/bin/token-canvas.txt`.

## Non-goals

- Per-student personalised forms.
- Automated distribution to students (link is shared by user via Canvas).
- Response analysis / scoring.

## Defaults

- Course: `1902104`
- Group category (group set): `231120`
- Canvas base URL: `https://canvas.uw.edu/api/v1`
