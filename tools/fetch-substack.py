"""Fetch the latest Substack note and posts for the Substack page.

Run every day by .github/workflows/substack.yml, and on demand. It writes:
  assets/data/substack.json   the latest note and the latest posts
  assets/img/substack/        their pictures, resized and stored on this site,
                              so visitors never load anything from Substack
Then tools/render-substack.py turns the JSON into HTML.

Posts come from the publication's RSS feed. Notes have no feed: they come from the
JSON that Substack's own profile pages use. That is not an official API, so when it
fails the previous note is kept and the run only prints a warning.

Usage: python tools/fetch-substack.py [--debug]
Pictures need Pillow (pip install pillow). Without it, the text is updated and the
pictures already saved are kept.
"""
import argparse
import hashlib
import html
import io
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None

HANDLE = "antoinetranquannam"
SUBSTACK = "https://substack.com"
OUT = "assets/data/substack.json"
IMG_DIR = "assets/img/substack"
NS = {"content": "http://purl.org/rss/1.0/modules/content/", "media": "http://search.yahoo.com/mrss/"}
# Like the open-source Substack clients, look like a browser: Substack may refuse other requests.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "en",
}


def warn(msg):
    # "::warning::" shows the message on the run's summary page in GitHub Actions.
    print(f"::warning::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"warning: {msg}", file=sys.stderr)


def get(url, accept="*/*"):
    req = urllib.request.Request(url, headers={**HEADERS, "Accept": accept})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def get_json(url):
    return json.loads(get(url, "application/json"))


def text(node, path):
    found = node.find(path, NS)
    return (found.text or "").strip() if found is not None else ""


def plain(raw):
    """HTML to one line of text."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def shorten(s, limit):
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:.-–—") + "…"


def day(value):
    """ISO date (YYYY-MM-DD, UTC) from an RSS date or an ISO 8601 timestamp; "" if unreadable."""
    if not value:
        return ""
    try:
        d = parsedate_to_datetime(value) if "," in value else datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).date().isoformat()
    except (TypeError, ValueError):
        return ""


# Posts ------------------------------------------------------------------------

def post_image(item):
    enc = item.find("enclosure")
    if enc is not None and enc.get("url") and enc.get("type", "image/").startswith("image/"):
        return enc.get("url")
    for tag in ("media:content", "media:thumbnail"):
        media = item.find(tag, NS)
        if media is not None and media.get("url"):
            return media.get("url")
    m = re.search(r'<img[^>]+src="([^"]+)"', text(item, "content:encoded") or text(item, "description"))
    return html.unescape(m.group(1)) if m else ""


def fetch_posts(feed, limit):
    root = ET.fromstring(get(feed, "application/rss+xml, application/xml;q=0.9, */*;q=0.8"))
    channel = root.find("channel")
    if channel is None:
        raise ValueError("no <channel> in the feed")
    posts = []
    for item in channel.findall("item"):
        title, link = html.unescape(text(item, "title")), text(item, "link")
        if not (title and link):
            continue
        posts.append({
            "title": title,
            "url": link,
            "date": day(text(item, "pubDate")),
            "excerpt": shorten(plain(text(item, "description") or text(item, "content:encoded")), 220),
            "image_url": post_image(item),
        })
        if len(posts) == limit:
            break
    about = {
        "publication": html.unescape(text(channel, "title")),
        "url": text(channel, "link") or feed.rsplit("/feed", 1)[0],
        "language": (text(channel, "language") or "en").split("-")[0].lower(),
    }
    return about, posts


# Latest note ------------------------------------------------------------------

def fetch_note(base, handle, debug=False):
    profile = get_json(f"{base}/api/v1/user/{handle}/public_profile")
    uid, handle = profile["id"], profile.get("handle") or handle
    feed = get_json(f"{base}/api/v1/reader/feed/profile/{uid}?types=note")
    items = feed.get("items") or []
    if debug:
        print(f"profile: id={uid} handle={handle} name={profile.get('name')!r} keys={sorted(profile)[:25]}")
        print(f"notes feed: {len(items)} items, keys={sorted(feed)}")
        for it in items[:6]:
            c, ctx = it.get("comment") or {}, it.get("context") or {}
            print(f"- item type={it.get('type')!r} entity_key={it.get('entity_key')!r} context.type={ctx.get('type')!r} "
                  f"timestamp={ctx.get('timestamp')!r} parents={len(it.get('parentComments') or [])}")
            print(f"  comment keys={sorted(c)}")
            print(f"  comment id={c.get('id')} user_id={c.get('user_id')} type={c.get('type')!r} date={c.get('date')!r} "
                  f"attachments={[a.get('type') for a in c.get('attachments') or []]} body={(c.get('body') or '')[:90]!r}")

    notes = []
    for it in items:
        c, ctx = it.get("comment") or {}, it.get("context") or {}
        if not c.get("id") or it.get("parentComments"):
            continue  # not a note, or a reply in someone's thread
        if c.get("user_id") not in (None, uid):
            continue  # someone else's note, restacked
        body = (c.get("body") or "").strip()
        image = next((a.get("imageUrl") for a in c.get("attachments") or []
                      if a.get("type") == "image" and a.get("imageUrl")), "")
        if not (body or image):
            continue
        when = c.get("date") or ctx.get("timestamp") or ""
        notes.append((when, {
            "url": f"{base}/@{handle}/note/c-{c['id']}",
            "date": day(when),
            "text": body[:3000],
            "image_url": image,
        }))
    if not notes:
        return None
    note = max(notes, key=lambda n: n[0])[1]
    note.update({
        "author": profile.get("name") or handle,
        "handle": handle,
        "profile_url": f"{base}/@{handle}",
        "avatar_url": profile.get("photo_url") or "",
    })
    return note


# Pictures ---------------------------------------------------------------------

def save_image(url, name, size=None, max_width=720):
    """Save a resized WebP copy of a picture under IMG_DIR. Returns {"src", "width", "height"} or None."""
    if not url or Image is None:
        return None
    path = f"{IMG_DIR}/{name}-{hashlib.sha1(url.encode()).hexdigest()[:12]}.webp"
    try:
        if not os.path.exists(path):  # same source picture as last time: keep the saved copy
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(get(url, "image/*"))))
            im = im.convert("RGBA" if "A" in im.getbands() or "transparency" in im.info else "RGB")
            if size:
                im = ImageOps.fit(im, size, Image.LANCZOS)
            else:
                im.thumbnail((max_width, max_width * 2), Image.LANCZOS)
            os.makedirs(IMG_DIR, exist_ok=True)
            im.save(path, "WEBP", quality=80, method=6)
        with Image.open(path) as im:
            return {"src": path, "width": im.width, "height": im.height}
    except Exception as e:  # a missing picture should never block the update
        warn(f"picture skipped ({e}): {url}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", default=HANDLE)
    ap.add_argument("--feed", help="RSS feed (default: https://HANDLE.substack.com/feed)")
    ap.add_argument("--base", default=SUBSTACK, help="where Substack's profile JSON lives (for tests)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--debug", action="store_true", help="print what Substack returned for the notes")
    args = ap.parse_args()
    feed = args.feed or f"https://{args.handle}.substack.com/feed"

    previous = {}
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as f:
            previous = json.load(f)

    try:
        about, posts = fetch_posts(feed, args.limit)
    except Exception as e:
        sys.exit(f"Could not read the Substack feed {feed}: {e}")

    try:
        note = fetch_note(args.base.rstrip("/"), args.handle, args.debug)
        if note is None:
            warn("no note found on the Substack profile; keeping the previous one")
    except Exception as e:
        note = None
        warn(f"could not read the latest note ({e}); keeping the previous one")
    if note is None:
        note = previous.get("note")
    else:
        note["image"] = save_image(note.pop("image_url"), "note")
        note["avatar"] = save_image(note.pop("avatar_url"), "avatar", size=(96, 96))

    for p in posts:
        p["image"] = save_image(p.pop("image_url"), "post", size=(720, 405))

    data = {**about, "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "note": note, "posts": posts}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Delete pictures nothing uses any more (only when pictures can be made again).
    if Image is not None and os.path.isdir(IMG_DIR):
        used = {x["src"] for x in [*(p.get("image") for p in posts), *((note or {}).get(k) for k in ("image", "avatar"))] if x}
        for f in os.listdir(IMG_DIR):
            if f"{IMG_DIR}/{f}" not in used:
                os.remove(f"{IMG_DIR}/{f}")

    print(f"{len(posts)} posts and {'a' if note else 'no'} note written to {args.out}")


if __name__ == "__main__":
    main()
