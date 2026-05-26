# canvas-group-evaluate

Generate a single Google Form for peer + self evaluations from a Canvas
group set. The form is restricted to your Google Workspace domain (e.g.
`uw.edu`), so only signed-in students can respond.

## How it works

```
Canvas (or CSV/TXT)                 script.google.com
        │                                   │
        │ fetch_roster.py                   │
        ▼                                   │
   roster.json ── generate_apps_script.py ──┴── paste build_form.gs ──▶ Google Form
```

1. `fetch_roster.py` pulls the roster from Canvas (or reads it from a
   file you supply) and writes `roster.json`.
2. `generate_apps_script.py` reads `roster.json` and writes a
   self-contained Apps Script file `build_form.gs`.
3. You paste `build_form.gs` into a new project at
   <https://script.google.com> and run `buildForm()`. The form URL is
   logged to the execution transcript. Share that URL via Canvas.

The form has one page-1 question ("Which group are you in?") that uses
section navigation to route each student to their group's rubric
section. Within a section, each member (including self) gets one Likert
block plus two short-text questions.

## Prerequisites

- Python 3.10+ (uses PEP 604 union types like `str | None`).
- A Canvas API access token (Profile → Settings → Approved Integrations →
  New Access Token).
- A Google account in the Workspace domain you want to restrict to
  (e.g. a `@uw.edu` account). The Apps Script must be run from that
  account; `setRequireLogin(true)` then locks the form to that domain.

## Install

```bash
git clone <this-repo> canvas-group-evaluate
cd canvas-group-evaluate
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

Copy the template and edit:

```bash
cp .env.example .env
$EDITOR .env
```

Required keys:

| Key | What it is | How to find it |
|---|---|---|
| `CANVAS_TOKEN_PATH` | Path to a file containing only your Canvas token (one line). | You create it: `echo 'abc123...' > /path/to/token.txt && chmod 600 /path/to/token.txt` |
| `CANVAS_BASE` | Canvas REST API base URL for your institution. | `https://canvas.uw.edu/api/v1` for UW. |
| `DEFAULT_COURSE` | Default course id used when `--course` is omitted. | URL: `/courses/<id>/`. |
| `DEFAULT_GROUP_CATEGORY` | Default group-set id used when `--group-category` is omitted. | URL fragment on the groups page: `/courses/<id>/groups#tab-<group_category_id>`. |

`.env` is git-ignored. CLI flags and OS environment variables override
values in `.env`.

## Usage

### 1. Fetch the roster

From Canvas using your `.env` defaults:

```bash
python3 fetch_roster.py
# wrote roster.json: 7 groups, 28 students  [canvas:course=1902104,group_category=231120]
```

A different course or group set, one-off:

```bash
python3 fetch_roster.py --course 1234567 --group-category 891011
```

From a CSV file (no Canvas call):

```bash
python3 fetch_roster.py --input roster.csv
```

`roster.csv` example (header row required; case-insensitive; `email` and
`netid` are both optional, but at least one is recommended):

```csv
group,name,email,netid
Team Alpha,Alice Anderson,alice@uw.edu,alice
Team Alpha,Bob Brown,,bob
Team Alpha,Carol Chen,carol@uw.edu,
Team Beta,Dave Davis,dave@uw.edu,dave
Team Beta,Eve Evans,,eve
```

From a plaintext file:

```bash
python3 fetch_roster.py --input roster.txt
```

`roster.txt` example (two accepted styles, can be mixed):

```text
Team Alpha: Alice Anderson <alice@uw.edu>, Bob Brown bob, Carol Chen <carol@uw.edu>
Team Beta:
  Dave Davis  dave@uw.edu
  Eve Evans   eve
```

Write the output somewhere other than the default:

```bash
python3 fetch_roster.py --output spring2026-roster.json
```

### 2. Generate the Apps Script

```bash
python3 generate_apps_script.py
# wrote build_form.gs: 7 groups, 28 students
```

Custom title and description (the description appears at the top of
the form):

```bash
python3 generate_apps_script.py \
    --title "DYOP Peer Evaluation — Spring 2026" \
    --description "Confidential. Submit by Friday June 12."
```

Read from a non-default roster file:

```bash
python3 generate_apps_script.py --roster spring2026-roster.json --output spring2026.gs
```

### 3. Build the form in Apps Script

1. Sign in to <https://script.google.com> using the Google account
   whose domain you want the form locked to (for UW, your `@uw.edu`
   account).
2. **New project**.
3. Replace the contents of `Code.gs` with the contents of
   `build_form.gs`.
4. **Run** → `buildForm`. Approve the OAuth prompt the first time
   (Forms, Drive scopes).
5. Open **Executions** (or **View → Logs**). The log lines contain:
   - `Form (live URL)` — share this with students.
   - `Form (short URL)` — same URL, shortened.
   - `Edit URL` — bookmark for yourself; do not share.

### 4. Share with students

Paste the live URL into a Canvas announcement or assignment. Because
the script sets `setRequireLogin(true)`, only users signed in to your
Google Workspace domain can open the form, and `setCollectEmail(true)`
records each respondent's address.

## Customising the rubric

The rubric is defined at the top of [generate_apps_script.py](generate_apps_script.py):

```python
RUBRIC_LIKERT = [
    ("Technical Contribution", "Did the member contribute a fair share ..."),
    ("Reliability",            "Did the member meet internal milestones ..."),
    ("Communication",          "Did the member respond promptly ..."),
    ("Problem Solving",        "Did the member help resolve blockers ..."),
]

LIKERT_LABELS = [
    "1 - Poor", "2 - Below expectations", "3 - Meets expectations",
    "4 - Exceeds expectations", "5 - Outstanding",
]

RUBRIC_TEXT = [
    "Strengths",
    "Areas for improvement",
]
```

Edit these lists in place; re-run `generate_apps_script.py`; paste the
new `build_form.gs` into a new Apps Script project. (Re-running
`buildForm` creates a fresh form each time — there is no in-place
update.)

## End-to-end example

```bash
# one-time
cp .env.example .env && $EDITOR .env
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# every quarter
python3 fetch_roster.py --course 1902104 --group-category 231120
python3 generate_apps_script.py --title "DYOP Peer Eval — Spring 2026"
# then paste build_form.gs into script.google.com and Run buildForm
```

## Files in the repo

| File | Purpose |
|---|---|
| [fetch_roster.py](fetch_roster.py) | Canvas + CSV/TXT → `roster.json` |
| [generate_apps_script.py](generate_apps_script.py) | `roster.json` → `build_form.gs` |
| [.env.example](.env.example) | Config template; copy to `.env` |
| [requirements.txt](requirements.txt) | Just `requests` |
| `roster.json` | Generated; git-ignored |
| `build_form.gs` | Generated; git-ignored; paste into Apps Script |

## Troubleshooting

- **`missing CANVAS_TOKEN_PATH`** — you have not copied `.env.example`
  to `.env`, or the key is empty.
- **HTTP 401 from Canvas** — token is wrong, expired, or you do not
  have access to that course.
- **No groups returned** — the `--group-category` value is a regular
  group id, not a group-category id. The category id is the
  `tab-<number>` portion of the URL on the course's Groups page.
- **`setRequireLogin` blocks a student** — they are signing in with a
  non-Workspace Google account (e.g. personal gmail). They must use
  their institutional Google account.
- **Form created in the wrong Drive** — you ran the script under a
  personal Google account. Run it from the institutional account whose
  domain you want the form locked to.
