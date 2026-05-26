#!/usr/bin/env python3
"""Fetch group + member roster.

Sources, in priority order:
  --input <file>   Read from a local CSV or TXT file.
  (default)        Hit the Canvas API using token at TOKEN_PATH.

Writes a roster.json of the form:
  [{"group": "Group A", "members": [{"name": "...", "email": "...",
                                     "netid": "...", "login_id": "..."}]}]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

ENV_PATH = Path(__file__).resolve().parent / ".env"
ENV_EXAMPLE = Path(__file__).resolve().parent / ".env.example"


def load_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env reader: KEY=VALUE per line, '#' comments, no expansion."""
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if (len(v) >= 2) and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]
        out[k] = v
    return out


_ENV = load_dotenv(ENV_PATH)


def env(key: str, default: str | None = None) -> str | None:
    # OS env wins over .env so callers can override ad-hoc.
    return os.environ.get(key) or _ENV.get(key) or default


def _require_env(key: str) -> str:
    v = env(key)
    if not v:
        raise SystemExit(
            f"missing {key}. Copy {ENV_EXAMPLE.name} to .env and fill it in, "
            f"or export {key} in your shell."
        )
    return v


TOKEN_PATH = env("CANVAS_TOKEN_PATH")
CANVAS_BASE = env("CANVAS_BASE", "https://canvas.instructure.com/api/v1")
DEFAULT_COURSE = int(env("DEFAULT_COURSE") or 0) or None
DEFAULT_GROUP_CATEGORY = int(env("DEFAULT_GROUP_CATEGORY") or 0) or None


def load_token() -> str:
    path = _require_env("CANVAS_TOKEN_PATH")
    return Path(path).read_text().strip()


def canvas_get(path: str, token: str, params: dict | None = None) -> Any:
    """GET with pagination. Returns a list (for list endpoints) or dict."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{CANVAS_BASE}{path}"
    p = dict(params or {})
    p.setdefault("per_page", 100)
    results: list = []
    first = True
    while url:
        r = requests.get(url, headers=headers, params=p if first else None)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return data
        results.extend(data)
        url = _next_link(r.headers.get("Link", ""))
        first = False
    return results


def _next_link(link_header: str) -> str | None:
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return None


def netid_from_email(email: str | None) -> str | None:
    if not email:
        return None
    local = email.split("@", 1)[0].strip()
    return local or None


def fetch_from_canvas(course_id: int, group_category_id: int) -> list[dict]:
    token = load_token()
    groups = canvas_get(f"/group_categories/{group_category_id}/groups", token)
    # Sort groups by name for stable output.
    groups = sorted(groups, key=lambda g: g.get("name") or "")
    roster: list[dict] = []
    for g in groups:
        members = canvas_get(
            f"/groups/{g['id']}/users",
            token,
            params={"include[]": "email"},
        )
        members = sorted(members, key=lambda m: m.get("sortable_name") or m.get("name") or "")
        roster.append({
            "group": g.get("name"),
            "canvas_group_id": g.get("id"),
            "members": [
                {
                    "name": m.get("name"),
                    "email": m.get("email"),
                    "login_id": m.get("login_id"),
                    "netid": netid_from_email(m.get("email")) or m.get("login_id"),
                }
                for m in members
            ],
        })
    # Drop empty groups so the form does not include them.
    return [g for g in roster if g["members"]]


def read_csv(path: Path) -> list[dict]:
    """CSV columns (case-insensitive): group, name, email|netid.

    Email is preferred; if only netid is given, email is derived as
    netid@uw.edu.
    """
    by_group: dict[str, list[dict]] = {}
    order: list[str] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"{path}: empty CSV")
        cols = {c.lower().strip(): c for c in reader.fieldnames}
        need = {"group", "name"}
        missing = need - set(cols)
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        for row in reader:
            group = (row[cols["group"]] or "").strip()
            name = (row[cols["name"]] or "").strip()
            if not group or not name:
                continue
            email = (row[cols["email"]] if "email" in cols else "").strip() if "email" in cols else ""
            netid = (row[cols["netid"]] if "netid" in cols else "").strip() if "netid" in cols else ""
            if not email and netid:
                email = f"{netid}@uw.edu"
            if not netid and email:
                netid = netid_from_email(email)
            if group not in by_group:
                by_group[group] = []
                order.append(group)
            by_group[group].append({
                "name": name,
                "email": email or None,
                "login_id": netid or None,
                "netid": netid or None,
            })
    return [{"group": g, "members": by_group[g]} for g in order]


def read_txt(path: Path) -> list[dict]:
    """Plaintext format:

        Group A: Alice <alice@uw.edu>, Bob <bnetid>
        Group B:
          Carol carol@uw.edu
          Dave  dnetid

    A bare token after a name is treated as a NetID. An angle-bracketed
    or whitespace-separated email is treated as the address.
    """
    text = path.read_text(encoding="utf-8")
    out: list[dict] = []
    current: dict | None = None
    inline_re = re.compile(r"^([^:]+):\s*(.*)$")
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = inline_re.match(line)
        if m and not line.startswith((" ", "\t")):
            group = m.group(1).strip()
            rest = m.group(2).strip()
            current = {"group": group, "members": []}
            out.append(current)
            if rest:
                for tok in _split_members(rest):
                    current["members"].append(_parse_member(tok))
            continue
        if current is None:
            raise ValueError(f"member line before any group header: {line!r}")
        current["members"].append(_parse_member(line.strip()))
    return [g for g in out if g["members"]]


def _split_members(s: str) -> list[str]:
    return [t.strip() for t in s.split(",") if t.strip()]


def _parse_member(token: str) -> dict:
    angle = re.match(r"^(.*?)\s*<([^>]+)>\s*$", token)
    if angle:
        name = angle.group(1).strip()
        email = angle.group(2).strip()
        return {
            "name": name,
            "email": email,
            "login_id": netid_from_email(email),
            "netid": netid_from_email(email),
        }
    parts = token.rsplit(None, 1)
    if len(parts) == 2 and ("@" in parts[1] or re.fullmatch(r"[A-Za-z0-9._-]+", parts[1])):
        name, ident = parts[0].strip(), parts[1].strip()
        if "@" in ident:
            email = ident
            netid = netid_from_email(email)
        else:
            netid = ident
            email = f"{netid}@uw.edu"
        return {"name": name, "email": email, "login_id": netid, "netid": netid}
    return {"name": token.strip(), "email": None, "login_id": None, "netid": None}


def read_input_file(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv(path)
    if suffix in {".txt", ".text", ".md", ""}:
        return read_txt(path)
    raise ValueError(f"unrecognised input extension: {path.suffix!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", type=int, default=DEFAULT_COURSE)
    ap.add_argument("--group-category", type=int, default=DEFAULT_GROUP_CATEGORY,
                    help="Canvas group_category_id (the tab-XXXXXX number from the groups page URL)")
    ap.add_argument("--input", type=Path, default=None,
                    help="Read roster from this CSV or TXT file instead of Canvas")
    ap.add_argument("--output", type=Path, default=Path("roster.json"))
    args = ap.parse_args()

    if args.input:
        if not args.input.exists():
            print(f"input file not found: {args.input}", file=sys.stderr)
            return 2
        roster = read_input_file(args.input)
        source = f"file:{args.input}"
    else:
        if args.course is None or args.group_category is None:
            print(
                "missing course or group-category. Set DEFAULT_COURSE and "
                "DEFAULT_GROUP_CATEGORY in .env, or pass --course and "
                "--group-category on the command line.",
                file=sys.stderr,
            )
            return 2
        token_path = _require_env("CANVAS_TOKEN_PATH")
        if not Path(token_path).exists():
            print(f"Canvas token file not found: {token_path}", file=sys.stderr)
            return 2
        roster = fetch_from_canvas(args.course, args.group_category)
        source = f"canvas:course={args.course},group_category={args.group_category}"

    args.output.write_text(json.dumps(roster, indent=2, ensure_ascii=False))
    n_students = sum(len(g["members"]) for g in roster)
    print(f"wrote {args.output}: {len(roster)} groups, {n_students} students  [{source}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
