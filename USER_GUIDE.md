# RHLC Community Exporter — User Guide

Export your Red Hat Learning Community posts from `learn.redhat.com` to a
self-contained offline HTML archive with all images and attachments downloaded
locally.

---

## Prerequisites

- **Python 3.11+** (or use `uv` which manages the version automatically)
- **uv** (recommended) — install from https://docs.astral.sh/uv/getting-started/installation/
- The JSON dump file: `my_community_content.json`

Install dependencies with uv (first run only):

```bash
uv sync
```

Or with plain pip:

```bash
pip install -r requirements.txt
```

---

## Quick Start

### Option A — Cookie file (recommended, most reliable)

`learn.redhat.com` is a JavaScript single-page application. Its login flow
cannot be automated with a plain HTTP client. The most reliable method is to
export your browser session cookies after logging in manually.

1. Log in to https://learn.redhat.com in your browser
2. Install the **Cookie-Editor** browser extension
   ([Chrome](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) /
   [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/))
3. Click the extension icon → **Export** → **Netscape** format
4. Save the file as `cookies.txt` in this directory
5. Run:

```bash
uv run export_community.py --cookies cookies.txt
```

To save the cookies for future runs automatically, add `--save-cookies`:

```bash
uv run export_community.py --cookies cookies.txt --save-cookies
```

### Option B — Playwright browser login (interactive)

If you have Playwright installed, the script can open a real browser window
for you to log in, then automatically capture the session cookies.

Install Playwright:

```bash
uv pip install playwright
uv run playwright install chromium
```

Then run without `--cookies`:

```bash
uv run export_community.py --save-cookies
```

A Chromium browser window will open. Log in normally, then press Enter in the
terminal. The script captures your session cookies and continues downloading.
Use `--save-cookies` to write them to `cookies.txt` for future runs.

### Option C — No authentication (HTML only, images may be broken)

```bash
uv run export_community.py --no-auth
```

Post HTML files are generated from the JSON. Images that require authentication
will appear as `[Image: <id>]` placeholders.

---

## Output Structure

After running, the `output/` directory will contain:

```
output/
├── rhtlc_main.html          <- Master index — open this in your browser
├── assets/
│   ├── highlight.min.js     <- Syntax highlighting (downloaded once)
│   └── highlight.min.css
├── images/
│   └── <image-id>.png/jpg/  <- All post images
├── attachments/
│   └── <filename>           <- All post attachments
├── posts/
│   └── <Forum-Subject>.html <- One file per post
└── download_errors.log      <- Only created if any downloads failed
```

Open `output/rhtlc_main.html` in any browser to browse your archive.
All links are relative — the entire `output/` folder is portable.

---

## CLI Reference

```
usage: export_community.py [-h] [--json FILE] [--output DIR]
                           [--cookies FILE] [--save-cookies]
                           [--skip-images] [--skip-attachments]
                           [--skip-assets] [--no-auth]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--json FILE` | `my_community_content.json` | Path to the JSON dump |
| `--output DIR` | `output` | Directory to write all output files |
| `--cookies FILE` | _(none)_ | Netscape cookies.txt file for authentication |
| `--save-cookies` | off | Save session cookies to `cookies.txt` after Playwright login |
| `--skip-images` | off | Skip downloading images (use existing files in `output/images/`) |
| `--skip-attachments` | off | Skip downloading attachments |
| `--skip-assets` | off | Skip downloading highlight.js assets |
| `--no-auth` | off | Skip all authentication (images behind login will not download) |

---

## Authentication Details

### Why Authentication Is Needed

Images embedded in Khoros posts are served from URLs like:
```
https://learn.redhat.com/t5/image/serverpage/image-id/12488i.../image-size/original
```
These URLs require an active session cookie. Without authentication, the
server returns a login redirect instead of the image.

### Why Form-Based Login Does Not Work

`learn.redhat.com` is a JavaScript single-page application (SPA). The login
page is rendered entirely by JavaScript — there is no HTML form accessible to
a plain HTTP client like `requests`. Attempting to POST credentials directly
results in a 404 or empty response.

### Cookie File Method (Recommended)

The `--cookies` flag accepts **Netscape/Mozilla** format cookie files —
the standard format exported by browser extensions like Cookie-Editor.

The file starts with:
```
# Netscape HTTP Cookie File
```

Steps:
1. Log in to https://learn.redhat.com in Chrome or Firefox
2. Open Cookie-Editor extension → Export → Netscape format
3. Save as `cookies.txt`
4. Run: `uv run export_community.py --cookies cookies.txt`

Cookies typically expire after a few hours to days. If images stop downloading,
export fresh cookies and re-run.

### Playwright Browser Method

When Playwright is installed and no `--cookies` file is provided, the script
opens a real Chromium browser window. You log in normally through the browser
UI (including any MFA/SSO steps), then press Enter in the terminal. The script
extracts all cookies from the browser context and uses them for downloads.

Install Playwright once:
```bash
uv pip install playwright && uv run playwright install chromium
```

---

## Re-running / Resuming

The script is **idempotent** — it skips files that already exist:

- Images already in `output/images/` are not re-downloaded
- Attachments already in `output/attachments/` are not re-downloaded
- `highlight.js` assets are not re-downloaded if present

To regenerate only the HTML (after editing the script's templates):

```bash
uv run export_community.py --skip-images --skip-attachments --skip-assets --no-auth
```

To retry failed image downloads (re-run normally — existing files are skipped):

```bash
uv run export_community.py --cookies cookies.txt
```

---

## Troubleshooting

### Images show as `[Image: <id>]` placeholders

- The image was not downloaded (auth failure or network error)
- Check `output/download_errors.log` for details
- Export fresh cookies and re-run: `uv run export_community.py --cookies cookies.txt`

### "Network error during login" in download_errors.log

This means the script attempted form-based login, which does not work against
this site. Use `--cookies cookies.txt` or install Playwright instead.

### `ModuleNotFoundError: No module named 'requests'`

Install dependencies:
```bash
uv sync
# or
pip install -r requirements.txt
```

### `JSONDecodeError` on startup

The JSON file may be malformed. Validate it:
```bash
python3 -c "import json; json.load(open('my_community_content.json'))"
```

### Syntax highlighting not working offline

The `output/assets/highlight.min.js` file may not have downloaded.
Delete it and re-run (without `--skip-assets`):
```bash
rm -rf output/assets/
uv run export_community.py --skip-images --skip-attachments --no-auth
```

### Cookies expired mid-run

If you see auth errors (401/403) in `download_errors.log` after a run that
previously worked, your cookies have expired. Export fresh cookies from your
browser and re-run — already-downloaded files will be skipped.

---

## Post Filename Format

Each post is saved as `output/posts/<Section>-<Subject>.html`.

- Section and subject are slugified (spaces to underscores, special chars removed)
- Duplicate titles get `_2`, `_3` suffixes
- Maximum filename length: ~100 characters

Example: A post titled *"How to use Ansible"* in the *"Automation"* forum
becomes `output/posts/Automation-How_to_use_Ansible.html`.

---

## Supported Khoros Tags

The following Khoros-specific HTML tags are transformed to standard HTML:

| Khoros Tag | Rendered As |
|------------|-------------|
| `<li-image id="...">` | `<img src="../images/...">` |
| `<li-code lang="python">` | `<pre><code class="language-python">` |
| `<li-user uid="123">` | `<span class="user-mention">@user_123</span>` |
| `<li-emoji id="lia_rocket">` | rocket emoji |


---

## Appendix: How to Export Your Community Content from RHLC

> **Note:** RHLC (Red Hat Learning Community at learn.redhat.com) is scheduled
> for decommissioning in Q2. Follow these steps to download your content as a
> JSON file before the site is shut down.

### Step 1 — Log in to RHLC

Navigate to https://learn.redhat.com/ and log in with your Red Hat account.

### Step 2 — Open My Settings

Click your **profile picture** in the upper-right corner of the page and
select **My Settings** from the dropdown menu.

### Step 3 — Open Advanced Profile

In the settings sub-menu, click **Advanced Profile**. Scroll to the bottom
of the page.

### Step 4 — Download My Community Content

In the **Downloads** section at the bottom of the Advanced Profile page,
click **My community content**. The site will generate and download a JSON
file containing all of your posts, replies, and associated image URLs.

> **Note:** It is unclear whether the JSON export includes content from every
> space you have participated in. The file can be inspected and manipulated
> after download if needed.

### Step 5 — Save the JSON file

Save the downloaded file as `my_community_content.json` in the same directory
as `export_community.py` (i.e., this repository root).

The file is listed in `.gitignore` and will **not** be committed to the
repository. A sample file (`my_community_content.sample.json`) is provided
in the repository to demonstrate the expected format.

### Step 6 — Run the exporter

Once you have `my_community_content.json`, follow the Quick Start instructions
at the top of this guide to generate your offline HTML archive:

```bash
# With browser cookie authentication (recommended):
uv run export_community.py --cookies cookies.txt

# Or with Playwright browser login:
uv run export_community.py --save-cookies
```

