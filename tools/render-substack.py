"""Write the latest Substack articles and note into substack.html and fr/substack.html.

Reads assets/data/substack.json, kept up to date by tools/update-substack.py (every day, by
.github/workflows/substack.yml). Each post has title, url, date "YYYY-MM-DD", and optionally
excerpt, paid, lang and image; the note has url, date, text and optionally image.

Only what sits between the <!-- substack:note --> and <!-- substack:posts --> markers
(and their closing markers) is replaced. The rest of the pages is left untouched.
"""
import json
import re
from datetime import date
from html import escape

DATA = "assets/data/substack.json"
NOTE_CHARS = 600  # longer notes are cut, the card links to the full note
NOTES_URL = "https://substack.com/@antoinetranquannam/notes"
ARROW = ('<svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
         'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 11 11 5M6 5h5v5"/></svg>')
LOCK = ('<svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/>'
        '<path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>')
LOGO = ('<svg class="note__logo" aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">'
        '<path d="M22.54 5.46H1.46V2.93h21.08v2.53zm0 4.48H1.46v2.54h21.08V9.94zM1.46 14.42v8.65L12 17.16l10.54 5.91v-8.65H1.46z"/></svg>')
NEW_TAB = {"en": '<span class="visually-hidden"> (opens in a new tab)</span>',
           "fr": '<span class="visually-hidden"> (s’ouvre dans un nouvel onglet)</span>'}
MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
}
LABELS = {
    "en": {"note": "Latest note", "read_note": "Read the note on Substack", "all_notes": "See all notes on Substack",
           "my_notes": "See my notes on Substack", "read_post": "Read on Substack", "paid": "Paid",
           "no_posts": "No posts yet. Check back soon."},
    "fr": {"note": "Dernière note", "read_note": "Lire la note sur Substack", "all_notes": "Voir toutes les notes sur Substack",
           "my_notes": "Voir mes notes sur Substack", "read_post": "Lire sur Substack", "paid": "Payant",
           "no_posts": "Pas encore de publication. Revenez bientôt."},
}
PAGES = {"substack.html": ("en", ""), "fr/substack.html": ("fr", "../")}


def when(iso, lang):
    if not iso:
        return ""
    d = date.fromisoformat(iso)
    m = MONTHS[lang][d.month - 1]
    return f"{m} {d.day}, {d.year}" if lang == "en" else f"{d.day}{'<sup>er</sup>' if d.day == 1 else ''} {m} {d.year}"


def time_tag(iso, lang, cls):
    return f'<time class="{cls}" datetime="{iso}">{when(iso, lang)}</time>' if iso else ""


def img(pic, cls, root, lazy=True):
    if not pic:
        return ""
    return (f'<img class="{cls}" src="{escape(root + pic["src"], quote=True)}" width="{pic["width"]}" '
            f'height="{pic["height"]}" alt=""{" loading=\"lazy\"" if lazy else ""}>')


def shorten(s, limit):
    if len(s) <= limit:
        return s
    cut = s[:limit]
    cut = cut[: max(cut.rfind(" "), cut.rfind("\n"))] if max(cut.rfind(" "), cut.rfind("\n")) > limit // 2 else cut
    return cut.rstrip(" \n,;:.-–—") + "…"


def note_html(note, lang, root, text_lang):
    L, new_tab = LABELS[lang], NEW_TAB[lang]
    def notes_button(label):
        return (f'<a class="btn btn--outline" href="{NOTES_URL}" target="_blank" rel="noopener">'
                f'{L[label]} {ARROW}{new_tab}</a>')
    if not note:
        return [f'<p class="note-all">{notes_button("my_notes")}</p>']

    note = {"author": "Antoine Tran Quan Nam", "handle": "antoinetranquannam", **note}
    paras = [p.strip() for p in re.split(r"\n\s*\n", shorten(note.get("text", ""), NOTE_CHARS)) if p.strip()]
    text = "".join(f"<p>{escape(p).replace(chr(10), '<br>')}</p>" for p in paras)
    initials = "".join(w[0] for w in note["author"].split()[:2]).upper()
    avatar = img(note.get("avatar"), "note__avatar", root, lazy=False) or \
        f'<span class="note__avatar note__avatar--initials" aria-hidden="true">{escape(initials)}</span>'
    date_part = f' · {time_tag(note["date"], lang, "note__date")}' if note.get("date") else ""
    lines = [
        f'<article class="note" aria-label="{L["note"]}">',
        '  <div class="note__head">',
        f"    {avatar}",
        "    <div>",
        f'      <p class="note__author">{escape(note["author"])}</p>',
        f'      <p class="note__meta">@{escape(note["handle"])}{date_part}</p>',
        "    </div>",
        f"    {LOGO}",
        "  </div>",
    ]
    if text:
        lines.append(f'  <div class="note__text" lang="{text_lang}">{text}</div>')
    if note.get("image"):
        lines.append(f'  {img(note["image"], "note__image", root)}')
    lines += [
        f'  <a class="note__link" href="{escape(note["url"], quote=True)}" target="_blank" rel="noopener">'
        f'{L["read_note"]} {ARROW}{new_tab}</a>',
        "</article>",
        f'<p class="note-all">{notes_button("all_notes")}</p>',
    ]
    return lines


def posts_html(posts, lang, root, text_lang):
    L, new_tab = LABELS[lang], NEW_TAB[lang]
    if not posts:
        return [f'<p class="posts__empty">{L["no_posts"]}</p>']
    lines = ['<ol class="posts">']
    for p in posts:
        lines += [
            '  <li class="post">',
            f'    <a class="post__link" href="{escape(p["url"], quote=True)}" target="_blank" rel="noopener">',
        ]
        if p.get("paid"):
            lines.append(f'      <span class="post__badge">{LOCK} {L["paid"]}</span>')
        # A post without a picture gets the cover's colours and lines instead.
        lines.append(f'      {img(p["image"], "post__image", root)}' if p.get("image")
                     else '      <span class="post__art" aria-hidden="true"></span>')
        lines.append('      <div class="post__body">')
        if p.get("date"):
            lines.append(f'        {time_tag(p["date"], lang, "post__date")}')
        post_lang = p.get("lang") or text_lang
        lines.append(f'        <h3 class="post__title" lang="{post_lang}">{escape(p["title"])}</h3>')
        if p.get("excerpt"):
            lines.append(f'        <p class="post__excerpt" lang="{post_lang}">{escape(p["excerpt"])}</p>')
        lines += [
            f'        <span class="post__more">{L["read_post"]} {ARROW}{new_tab}</span>',
            "      </div>",
            "    </a>",
            "  </li>",
        ]
    return lines + ["</ol>"]


def replace(page, name, lines):
    """Put the lines between the markers, indented like the opening marker."""
    start, end = f"<!-- substack:{name} -->", f"<!-- /substack:{name} -->"
    i, j = page.index(start), page.index(end)
    indent = " " * (i - page.rindex("\n", 0, i) - 1)
    body = "".join(f"\n{indent}{line}" for line in lines)
    return page[: i + len(start)] + body + f"\n{indent}" + page[j:]


def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    text_lang = data.get("language") or "en"
    for path, (lang, root) in PAGES.items():
        with open(path, encoding="utf-8") as f:
            page = f.read()
        page = replace(page, "note", note_html(data.get("note"), lang, root, text_lang))
        page = replace(page, "posts", posts_html(data.get("posts") or [], lang, root, text_lang))
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
        print(f"{path}: {'1 note' if data.get('note') else 'no note'}, {len(data.get('posts') or [])} posts")


if __name__ == "__main__":
    main()
