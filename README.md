# Augmenting Decision · book website

The website for the book *Augmenting Decision: How data and AI are reshaping the way we choose* by Antoine Tran Quan Nam,
published at **https://augmenting-decision.com** (English) and **https://augmenting-decision.com/fr/** (French).

It is plain HTML and CSS, with no build step and nothing to install, hosted for free on GitHub Pages.

## What's where

| File | What it is |
| --- | --- |
| `index.html` | English home page |
| `fr/index.html` | French home page |
| `substack.html` · `fr/substack.html` | Substack page: latest note and latest posts (EN · FR), updated every day |
| `legal.html` · `fr/mentions-legales.html` | Legal notice and privacy policy (EN · FR) |
| `404.html` | "Page not found" page, in both languages |
| `assets/css/style.css` | All the styling. Colors (taken from the cover) and fonts are defined at the top. |
| `assets/js/main.js` | Menu, praise carousel, sign-up form (sends to the Google Sheet) and the footer year |
| `assets/img/cover.webp` | Book cover |
| `assets/img/author.webp` · `author-480.webp` · `author-avatar.webp` | Author portrait (800×1000 and 480×600, for phones) and the round photo on the Substack note card (96×96) |
| `assets/img/waves-*.svg` | The cover's flowing lines and data points, used as background art |
| `assets/img/og-en.jpg` · `og-fr.jpg` | Preview images shown when the link is shared |
| `assets/img/substack/` · `assets/data/substack.json` | Pictures and data of the Substack page, written by the daily update |
| `tools/update-substack.py` · `tools/render-substack.py` | The daily update: read the agent's archive, then write the page |
| `.github/workflows/substack.yml` | Runs the daily update on GitHub |
| `assets/fonts/` | Montserrat (headings, like the cover) and Inter (text), served from the site itself (no Google Fonts) |
| `CNAME` | Tells GitHub Pages the site's domain name |

## Putting the site online (one-time setup)

### 1. Publish with GitHub Pages

1. Merge the website into the `main` branch.
2. In this repository, go to **Settings → General → Danger Zone → Change visibility → Make public**.
   Free GitHub Pages needs a public repository. With a paid GitHub plan it can stay private.
3. Go to **Settings → Pages → Build and deployment** and set:
   - Source: **Deploy from a branch**
   - Branch: **main**, folder **/ (root)**, then **Save**
4. On the same page, check that **Custom domain** shows `augmenting-decision.com`. It is read from the `CNAME` file.
   If the field is empty, type the domain and click **Save**.

### 2. Point the IONOS domain to GitHub

In your IONOS account, open **Domains & SSL**, click `augmenting-decision.com`, then open the **DNS** tab.

1. **Delete** the existing **A** and **AAAA** records for `@`, and the existing record for `www`.
   IONOS creates these by default to show its parking page.
   Leave **MX**, **TXT** and all other records alone, especially if you use an IONOS email address.
2. **Add** these records (**Add record**, then choose the type):

   | Type | Host name | Points to |
   | --- | --- | --- |
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | AAAA | `@` | `2606:50c0:8000::153` |
   | AAAA | `@` | `2606:50c0:8001::153` |
   | AAAA | `@` | `2606:50c0:8002::153` |
   | AAAA | `@` | `2606:50c0:8003::153` |
   | CNAME | `www` | `quannamtran.github.io` |

3. Wait. Changes usually take effect within an hour, but can take up to 24 hours.
   Both `augmenting-decision.com` and `www.augmenting-decision.com` will then show the site.

If IONOS won't let you edit the records because the domain is connected to an IONOS product (such as a parking page,
website builder or webspace), first disconnect it from that product in IONOS. Then edit the DNS records.

### 3. Turn on HTTPS

When **Settings → Pages** says the DNS check succeeded, tick **Enforce HTTPS**.
The certificate can take up to an hour to appear. If the option stays greyed out for longer,
remove the custom domain, save, add it back and save again.

Optional but recommended: verify the domain in your GitHub account
(**your profile picture → Settings → Pages → Add a domain**). This stops anyone else from using it on GitHub.

## Sign-up form (Google Sheet)

Both "Notify me" forms send addresses to a private Google Sheet, through a small Google Apps Script
(`tools/google-sheet-signup.gs`). Each sign-up adds a row: date, email, language, page. Duplicates and spam bots are ignored.

To set it up, or to move it to another Google account:

1. Create a Google Sheet (for example "Augmenting Decision – Launch list").
2. In the sheet: **Extensions → Apps Script**. Delete what is there, paste the contents of `tools/google-sheet-signup.gs`, and save.
3. **Deploy → New deployment →** type **Web app**. Set *Execute as*: **Me**, *Who has access*: **Anyone**. Click **Deploy** and authorize.
4. Copy the **Web app URL** (it ends in `/exec`) into `assets/js/main.js`, as `SIGNUP_ENDPOINT`.

While `SIGNUP_ENDPOINT` is empty, the forms tell visitors that sign-ups are not open yet.
On launch day, export the email column and send the announcement yourself, with the addresses in **BCC**.

## Substack page

`substack.html` (and `fr/substack.html`) shows your latest Substack note, your 5 latest articles and a link to
your Substack. Each card opens on Substack.

It is filled from your publishing agent's repository, **quannamtran/substack-post**, not from Substack (Substack
refuses automated requests from GitHub's servers). Each run of the agent logs the link Substack gave the post and
where it archived the text. The website reads those logs, then takes the title, subtitle, cover and note text from
the archive.

- **When** (workflow `.github/workflows/substack.yml`): the **note** every day at **11:07 UTC**, the latest one
  posted by then; the **articles** on **Thursday and Sunday at 15:07 UTC**, after the agent publishes the free
  article (Thursday) and the paid one (Sunday), usually around 14:20. An article published later than that shows up
  at the next run, or right away if you run the update by hand. Nothing is published when nothing changed.
- **Update right away** (note and articles): in this repository, open **Actions → Refresh Substack page → Run
  workflow → Run workflow**.
- **A post you published by hand:** if you ran the agent's "Announce article" for it, it is picked up automatically.
  Otherwise run "Refresh Substack page" and paste its link in **post_url**.
- **Pictures** (covers and charts) are copied from the archive onto this site and resized, so visitors never load
  anything from Substack. This keeps the privacy promise of the legal page.
- If a run fails (red cross in **Actions**), GitHub usually emails you. The page simply keeps its last content.

### One-time setup: the access key

The agent's repository is private, so the website needs a read-only key to it.

1. Open https://github.com/settings/personal-access-tokens/new (GitHub → your profile picture → **Settings →
   Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**).
2. **Token name:** `Website reads substack-post`. **Expiration:** 1 year (note the date: the key must be renewed).
3. **Repository access:** **Only select repositories** → `quannamtran/substack-post`.
4. **Permissions → Repository permissions:** **Actions: Read-only** and **Contents: Read-only**.
5. Click **Generate token** and copy it.
6. In this repository (`website`): **Settings → Secrets and variables → Actions → New repository secret**.
   Name: `SUBSTACK_POST_TOKEN`. Secret: paste the key. Click **Add secret**.

Until the key is there, the daily run only shows a yellow reminder. When the key expires, the run fails: create a
new key the same way and replace the secret's value.

To change the number of articles, the texts around the cards or the date format, see the top of
`tools/update-substack.py` and `tools/render-substack.py`. Do not edit the HTML between the
`<!-- substack:... -->` markers: the next update replaces it.

## Editing the site

- Texts live directly in the HTML files. The English and French pages have the same structure,
  so a change in one usually needs the same change in the other.
- Colors and fonts are CSS variables at the top of `assets/css/style.css`.
- To change the author photo, replace the three `assets/img/author*.webp` files with new ones of the same sizes.
- To preview locally, run `python3 -m http.server` in this folder and open http://localhost:8000.
- Every push to `main` updates the live site within a minute or two.
- The pages load `style.css` and `main.js` with a version tag (`?v=…`). After changing either file, change that tag in
  the six HTML pages (any new value works), so browsers fetch the new file instead of a cached copy.
