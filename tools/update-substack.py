"""Update the Substack page from the publishing agent's repository (quannamtran/substack-post).

The agent publishes the articles and notes on Substack. Each of its runs logs the link the
post got on Substack and where it archived the text, for example:

    archived to articles/Data foundation/…/published/article-002/
    ARTICLE_STATUS=published
    ARTICLE_URL=https://antoinetranquannam.substack.com/p/the-model-worked-the-rollout-didnt

    NOTE_URL=https://substack.com/note/c-371413677
    archived to notes/social/note-341.md

This script reads those logs with the GitHub API, takes the title, subtitle, cover and note
text from the archive (a checkout of the agent repository), and updates
assets/data/substack.json (the 5 latest articles and the latest note) and their pictures in
assets/img/substack/. Substack itself is never contacted. Then tools/render-substack.py
writes the pages.

Needs SUBSTACK_POST_TOKEN: a GitHub token that can read the agent repository (Contents and
Actions, read-only).

    python tools/update-substack.py --agent .agent [--only notes|articles]
    python tools/update-substack.py --agent .agent --add URL [ARCHIVE_DIR] [YYYY-MM-DD]
        adds a post published by hand; its archive is found from the link when not given
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None

REPO = "quannamtran/substack-post"
API = "https://api.github.com"
# Agent workflows that publish articles (the weekly free and paid ones, the occasional
# ones, and "Announce article" for a post published by hand), and those that post notes.
ARTICLE_WORKFLOWS = ["publish.yml", "publish-paid.yml", "adhoc-article.yml", "adhoc-paid-article.yml",
                     "handson-article.yml", "dossier.yml", "announce-article.yml"]
NOTE_WORKFLOWS = ["social-note.yml", "insight-note.yml"]
OUT = "assets/data/substack.json"
IMG_DIR = "assets/img/substack"
KEEP = 5             # articles shown on the page
FIRST_LOOKBACK = 30  # days of agent runs read the first time
MARGIN = 2           # days read again before the last check, in case a run was still going

STAMP = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.\d+)?Z ")
ANNOUNCE = re.compile(r"^→ announcing «(.+)» \((free|paid)\) → (\S+)$")


def warn(msg):
    # "::warning::" shows the message on the run's summary page in GitHub Actions.
    print(f"::warning::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"warning: {msg}", file=sys.stderr)


# GitHub API ------------------------------------------------------------------------

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _request(url, token=None, accept="application/vnd.github+json"):
    headers = {"Accept": accept, "User-Agent": "augmenting-decision.com", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def api(path, token):
    with urllib.request.urlopen(_request(API + path, token), timeout=30) as r:
        return json.load(r)


def job_log(job_id, token, log_dir=None):
    """The job's log as text. GitHub answers with a redirect to a storage link, which is
    opened without the token (the link carries its own short-lived permission)."""
    if log_dir:
        path = os.path.join(log_dir, f"{job_id}.log")
        return open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(_request(f"{API}/repos/{REPO}/actions/jobs/{job_id}/logs", token), timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303, 307, 308) or not e.headers.get("Location"):
            raise
        with urllib.request.urlopen(e.headers["Location"], timeout=60) as r:
            return r.read().decode("utf-8", "replace")


def runs(workflow, since, token):
    """Successful runs of one agent workflow since a date, newest first."""
    try:
        data = api(f"/repos/{REPO}/actions/workflows/{workflow}/runs"
                   f"?status=success&created=%3E%3D{since}&per_page=100", token)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # workflow renamed or removed in the agent
            return []
        raise
    return data.get("workflow_runs", [])


def run_logs(run, token, log_dir=None):
    for job in api(f"/repos/{REPO}/actions/runs/{run['id']}/jobs", token).get("jobs", []):
        if job.get("conclusion") == "success":
            yield job_log(job["id"], token, log_dir)


# Reading the logs ------------------------------------------------------------------

def log_lines(log):
    """(timestamp, text) for each line of a GitHub Actions log."""
    for raw in log.splitlines():
        m = STAMP.match(raw)
        yield (m.group(1) + "Z", raw[m.end():].strip()) if m else ("", raw.strip())


def parse_article(log):
    """The article a run published: {url, date, dir?, title?, paid}, or None."""
    archived = status = url = when = None
    paid = False
    announced = None
    for ts, line in log_lines(log):
        if line.startswith("archived to "):
            archived = line[len("archived to "):].rstrip("/")
        elif line.startswith("ARTICLE_STATUS="):
            status = line.split("=", 1)[1].strip()
        elif line.startswith("ARTICLE_URL="):
            url, when = line.split("=", 1)[1].strip(), ts
        elif line.startswith("PUBLISH_SETTINGS=") and "Paid subscribers only" in line:
            paid = True
        elif ANNOUNCE.match(line):
            m = ANNOUNCE.match(line)
            announced = {"title": m.group(1), "paid": m.group(2) == "paid", "url": m.group(3), "time": ts}
    if status == "published" and url and archived:
        return {"url": url, "time": when, "dir": archived,
                "paid": paid or archived.split("/")[0].endswith("-paid")}
    return announced


def parse_note(log):
    """The note a run posted: {url, time, path}, or None."""
    url = path = when = None
    for ts, line in log_lines(log):
        if line.startswith("NOTE_URL="):
            url, when = line.split("=", 1)[1].strip(), ts
        elif line.startswith("archived to "):
            path = line[len("archived to "):].rstrip("/")
    return {"url": url, "time": when, "path": path} if url and path else None


# Reading the archive -----------------------------------------------------------------

def read_archived(path):
    """Header fields (TITLE, SUBTITLE, …) and body of an archived article.md or note-NNN.md."""
    head, body = {}, []
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    i = 0
    while i < len(lines) and lines[i].strip():
        key, sep, value = lines[i].partition(":")
        if sep and key.isupper():
            head[key] = value.strip()
        i += 1
    body = "\n".join(lines[i:]).strip()
    return head, body


def markdown_to_text(md):
    """The note's markdown as plain paragraphs."""
    md = re.sub(r"%%[A-Z_0-9]+%%", "", md)              # the agent's placeholders
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)        # images
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)    # links: keep the words
    md = re.sub(r"^#{1,6}\s*", "", md, flags=re.M)      # headings
    md = re.sub(r"(\*\*|__|\*|_)(\S.*?\S|\S)\1", r"\2", md)  # bold, italics
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def slugify(text):
    """Roughly how Substack turns a title into a link: lower case, no apostrophes, dashes."""
    text = re.sub(r"[’'`]", "", text.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def find_archive(agent, title=None, url=None):
    """Archive folder of a post published by hand, found by its title or by its link."""
    slug = url.rstrip("/").rsplit("/p/", 1)[-1] if url and "/p/" in url else None
    for root, _dirs, files in sorted(os.walk(agent), reverse=True):
        if "article.md" not in files:
            continue
        head, _ = read_archived(os.path.join(root, "article.md"))
        archived = head.get("TITLE", "").strip()
        if not archived:
            continue
        if (title and archived.lower() == title.strip().lower()) or (slug and slugify(archived).startswith(slug)):
            return os.path.relpath(root, agent)
    return None


# Pictures --------------------------------------------------------------------------

def save_image(path, name, size=None, max_width=720):
    """A resized WebP copy of an archived picture in IMG_DIR: {src, width, height} or None."""
    if not path or not os.path.exists(path) or Image is None:
        return None
    digest = hashlib.sha1(open(path, "rb").read()).hexdigest()[:12]
    out = f"{IMG_DIR}/{name}-{digest}.webp"
    try:
        if not os.path.exists(out):
            with Image.open(path) as src:
                im = ImageOps.exif_transpose(src)
                im = im.convert("RGBA" if "A" in im.getbands() or "transparency" in im.info else "RGB")
                if size:
                    im = ImageOps.fit(im, size, Image.LANCZOS)
                else:
                    im.thumbnail((max_width, max_width * 2), Image.LANCZOS)
                os.makedirs(IMG_DIR, exist_ok=True)
                im.save(out, "WEBP", quality=80, method=6)
        with Image.open(out) as im:
            return {"src": out, "width": im.width, "height": im.height}
    except Exception as e:  # a picture problem never blocks the update
        warn(f"picture skipped ({e}): {path}")
        return None


# Building the page data ------------------------------------------------------------

def build_post(rec, agent):
    d = rec.get("dir") or find_archive(agent, rec.get("title"), rec.get("url"))
    head, body = read_archived(os.path.join(agent, d, "article.md")) if d and os.path.exists(
        os.path.join(agent, d, "article.md")) else ({}, "")
    title = head.get("TITLE") or rec.get("title")
    if not title:
        return None
    image = None
    if d:
        cover = os.path.join(agent, d, "cover.png")
        image = save_image(cover if os.path.exists(cover) else os.path.join(agent, d, "figure_01.png"),
                           "post", size=(720, 405))
    return {
        "title": title,
        "url": rec["url"],
        "date": rec["time"][:10],
        "excerpt": head.get("SUBTITLE", ""),
        "paid": bool(rec.get("paid")) or bool(d and d.split("/")[0].endswith("-paid")),
        "image": image,
    }


def build_note(rec, agent):
    path = os.path.join(agent, rec["path"])
    if os.path.isdir(path):  # an insight note: article.md and its chart
        head, body = read_archived(os.path.join(path, "article.md"))
        text, image = markdown_to_text(body), save_image(os.path.join(path, "figure_01.png"), "note")
    elif os.path.exists(path):  # a social note: note-NNN.md
        head, body = read_archived(path)
        text, image = body, None
    else:
        return None
    return {"url": rec["url"], "date": rec["time"][:10], "time": rec["time"], "text": text, "image": image}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default=".agent", help="checkout of the agent repository")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--only", choices=["notes", "articles"], help="update only the note or only the articles")
    ap.add_argument("--add", nargs="+", metavar=("URL", "ARCHIVE_DIR"),
                    help="add a post published by hand: URL ARCHIVE_DIR [YYYY-MM-DD]")
    ap.add_argument("--log-dir", help="read job logs from <job id>.log files here (tests)")
    args = ap.parse_args()
    token = os.environ.get("SUBSTACK_POST_TOKEN") or None

    previous = {}
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as f:
            previous = json.load(f)
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def since(kind):
        """Read the agent's runs from a little before this part's last check."""
        last = previous.get(f"checked_{kind}") or previous.get("checked")
        start = (datetime.fromisoformat(last.replace("Z", "+00:00")) - timedelta(days=MARGIN)) if last \
            else now - timedelta(days=FIRST_LOOKBACK)
        return start.strftime("%Y-%m-%d")

    do_articles = args.add or args.only in (None, "articles")
    do_notes = not args.add and args.only in (None, "notes")
    checked = {k: previous.get(f"checked_{k}") or previous.get("checked") for k in ("articles", "notes")}

    posts = {p["url"]: p for p in previous.get("posts", [])}
    if do_articles:
        found = []
        if args.add:
            url, d = args.add[0], (args.add[1] if len(args.add) > 1 and args.add[1] else None)
            when = (args.add[2] if len(args.add) > 2 else now.strftime("%Y-%m-%d")) + "T12:00:00Z"
            found.append({"url": url, "time": when, "dir": d})
        else:
            for wf in ARTICLE_WORKFLOWS:
                for run in runs(wf, since("articles"), token):
                    for log in run_logs(run, token, args.log_dir):
                        rec = parse_article(log)
                        if rec:
                            found.append(rec)
            checked["articles"] = stamp
        for rec in found:
            post = build_post(rec, args.agent)
            if post:
                posts[post["url"]] = post
                print(f"article {post['date']}: {post['title']} → {post['url']}")
    posts = sorted(posts.values(), key=lambda p: p["date"], reverse=True)[:KEEP]

    note = previous.get("note")
    if do_notes:
        for wf in NOTE_WORKFLOWS:
            for run in runs(wf, since("notes"), token):  # newest first: stop at the first note found
                rec = next((r for r in (parse_note(log) for log in run_logs(run, token, args.log_dir)) if r), None)
                if rec:
                    if not note or rec["time"] > note.get("time", ""):
                        new = build_note(rec, args.agent)
                        if new:
                            note = new
                    break
        checked["notes"] = stamp
    if note:
        print(f"note {note['date']}: {note['url']}")

    data = {"language": "en", "checked_articles": checked["articles"], "checked_notes": checked["notes"],
            "note": note, "posts": posts}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Delete pictures nothing uses any more.
    if Image is not None and os.path.isdir(IMG_DIR):
        used = {x["src"] for x in [*(p.get("image") for p in posts), (note or {}).get("image")] if x}
        for name in os.listdir(IMG_DIR):
            if f"{IMG_DIR}/{name}" not in used:
                os.remove(f"{IMG_DIR}/{name}")
    print(f"{len(posts)} articles and {'a' if note else 'no'} note in {args.out}")


if __name__ == "__main__":
    main()
