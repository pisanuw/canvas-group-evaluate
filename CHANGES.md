# Changes

2026-05-26 scope initial scope: Canvas roster fetch + Apps Script generator for one-form DYOP peer evaluation, UW domain restricted
2026-05-26 decision one form total, group selection routes via section navigation; standard 5-Likert + 2-text rubric per teammate
2026-05-26 decision Google Apps Script chosen over Python+Forms API to avoid GCP OAuth setup
2026-05-26 code add fetch_roster.py (Canvas API + CSV/TXT fallback) and generate_apps_script.py
2026-05-26 scope rubric updated to DYOP-specific 4-item Likert: Technical Contribution, Reliability, Communication, Problem Solving (text items unchanged)
2026-05-26 code config (token path, Canvas base URL, default course + group category) moved from constants in fetch_roster.py to a .env file; .env.example committed as template; .env git-ignored
2026-05-26 doc add README.md covering install, .env config, CSV/TXT input formats, Apps Script paste-and-run flow, rubric customisation, and troubleshooting
2026-05-26 code Apps Script now uses one GridItem (rubric × Likert) per member instead of four MultipleChoiceItems; drops shortenFormUrl (goo.gl shutdown); rationale: prior version was hitting the 6-minute Apps Script execution limit on larger rosters
2026-05-26 code switch Apps Script progress to console.log (streams live to Executions panel); add per-group and per-member progress with elapsed time; update group dropdown incrementally so a cancelled run still produces a usable partial form
2026-05-26 code sanitize control chars (tab, newline) from Canvas-supplied group and member names in fetch_roster.py; Canvas was returning names like "Group 1<TAB>UW Compass" which broke JSON parsing under Python 3.14 and rendered badly in form labels; generate_apps_script.py also reads with strict=False as a safety net
