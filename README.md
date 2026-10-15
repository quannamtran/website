# Augmenting Decision · book website

The website for the book *Augmenting Decision: How data and AI are reshaping the way we choose* by Antoine Tran Quan Nam,
published at **https://augmenting-decision.com** (English) and **https://augmenting-decision.com/fr/** (French).

It is plain HTML and CSS, with no build step and nothing to install, hosted for free on GitHub Pages.

## What's where

| File | What it is |
| --- | --- |
| `index.html` | English home page |
| `fr/index.html` | French home page |
| `legal.html` · `fr/mentions-legales.html` | Legal notice and privacy policy (EN · FR) |
| `404.html` | "Page not found" page, in both languages |
| `assets/css/style.css` | All the styling. Colors (taken from the cover) and fonts are defined at the top. |
| `assets/js/main.js` | Sign-up form (sends to the Google Sheet) and the footer year |
| `assets/img/cover.webp` | Book cover |
| `assets/img/waves-*.svg` | The cover's flowing lines and data points, used as background art |
| `assets/img/og-en.jpg` · `og-fr.jpg` | Preview images shown when the link is shared |
| `assets/fonts/` | Montserrat (headings, like the cover) and Inter (text), served from the site itself (no Google Fonts) |
| `CNAME` | Tells GitHub Pages the site's domain name |

## Before launch: things to fill in

Placeholders are highlighted in lavender on the pages. Search the HTML for `class="todo"` to find them.

- [ ] **Author**: short bio and photo, in both `index.html` and `fr/index.html`
- [ ] **Legal pages**: publisher name and contact email, in `legal.html` and `fr/mentions-legales.html`
- [ ] **Sign-up form**: connect it to the Google Sheet (see below)
- [ ] **Texts**: the book description, themes and audience are drafts written from the title. Rewrite them in your own words.

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

## Editing the site

- Texts live directly in the HTML files. The English and French pages have the same structure,
  so a change in one usually needs the same change in the other.
- Colors and fonts are CSS variables at the top of `assets/css/style.css`.
- To preview locally, run `python3 -m http.server` in this folder and open http://localhost:8000.
- Every push to `main` updates the live site within a minute or two.
