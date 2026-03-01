#!/usr/bin/env python3
"""
export_community.py - Khoros Community Content Exporter for learn.redhat.com

Reads a JSON dump of community posts, authenticates to learn.redhat.com,
downloads all images and attachments, transforms Khoros-specific HTML tags,
and generates a self-contained offline HTML archive.

Usage:
    uv run export_community.py [options]
    python export_community.py [options]

See USER_GUIDE.md for full documentation.
"""

import argparse
import http.cookiejar
import json
import logging
import mimetypes
import re
import time
from collections import defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://learn.redhat.com"
HLJS_JS_URL = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"
HLJS_CSS_URL = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css"

MIME_TO_EXT = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg",
    "image/gif": ".gif", "image/webp": ".webp", "image/svg+xml": ".svg",
    "image/bmp": ".bmp", "image/tiff": ".tiff",
}

EMOJI_MAP = {
    "lia_slightly-smiling-face": "🙂", "lia_smile": "😊", "lia_grinning": "😀",
    "lia_laughing": "😄", "lia_wink": "😉", "lia_thumbsup": "👍",
    "lia_thumbsdown": "👎", "lia_heart": "❤️", "lia_star": "⭐",
    "lia_check": "✅", "lia_x": "❌", "lia_warning": "⚠️",
    "lia_info": "ℹ️", "lia_question": "❓", "lia_exclamation": "❗",
    "lia_rocket": "🚀", "lia_fire": "🔥", "lia_clap": "👏",
    "lia_raised_hands": "🙌", "lia_thinking_face": "🤔", "lia_tada": "🎉",
    "lia_bulb": "💡", "lia_wrench": "🔧", "lia_computer": "💻",
    "lia_books": "📚", "lia_memo": "📝", "lia_link": "🔗",
    "lia_lock": "🔒", "lia_key": "🔑", "lia_bell": "🔔",
    "lia_gear": "⚙️", "lia_shield": "🛡️", "lia_cloud": "☁️",
    "lia_globe": "🌐",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)
error_log_entries = []

def log_error(msg):
    logger.error(msg)
    error_log_entries.append(msg)

def parse_args():
    parser = argparse.ArgumentParser(
        prog="export_community.py",
        description="Export Khoros community posts from learn.redhat.com to offline HTML.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python export_community.py
  python export_community.py --cookies cookies.txt
  python export_community.py --json my_community_content.json --output ./archive
  python export_community.py --skip-images --skip-attachments
  python export_community.py --save-cookies
  python export_community.py --no-auth
  python export_community.py --fetch-json
  python export_community.py --auto

See USER_GUIDE.md for full documentation.
        """,
    )
    parser.add_argument("--json", default="my_community_content.json", metavar="FILE")
    parser.add_argument("--output", default="output", metavar="DIR")
    parser.add_argument("--cookies", default=None, metavar="FILE")
    parser.add_argument("--save-cookies", action="store_true")
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--skip-attachments", action="store_true")
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--no-auth", action="store_true")
    parser.add_argument(
        "--fetch-json",
        action="store_true",
        help=(
            "Use Playwright to log in to learn.redhat.com, navigate to Advanced Profile, "
            "and automatically download my_community_content.json before exporting. "
            "Requires Playwright: uv pip install playwright && uv run playwright install chromium"
        ),
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help=(
            "Shorthand for --fetch-json --save-cookies: log in once, download the JSON, "
            "save session cookies, then run the full export pipeline automatically."
        ),
    )
    return parser.parse_args()

def load_cookies_file(path, session):
    jar = http.cookiejar.MozillaCookieJar(path)
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(jar)
        logger.info(f"Loaded {sum(1 for _ in jar)} cookies from {path}")
        return True
    except Exception as e:
        log_error(f"Failed to load cookies from {path}: {e}")
        return False

def save_cookies_file(path, session):
    jar = http.cookiejar.MozillaCookieJar(path)
    for c in session.cookies:
        jar.set_cookie(c)
    try:
        jar.save(ignore_discard=True, ignore_expires=True)
        logger.info(f"Session cookies saved to {path}")
    except Exception as e:
        log_error(f"Failed to save cookies: {e}")

def _print_cookie_help():
    print("\n" + "="*60)
    print("  ALTERNATIVE: Use browser cookies")
    print("="*60)
    print("  1. Log in to https://learn.redhat.com in your browser")
    print("  2. Use 'Cookie-Editor' extension to export Netscape cookies")
    print("  3. Save as cookies.txt")
    print("  4. Re-run: python export_community.py --cookies cookies.txt")
    print("="*60 + "\n")

def _playwright_login(session, save_cookies_path=None):
    """Use Playwright (headful browser) to log in and extract session cookies."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "playwright not installed"
    print("\n" + "=" * 60)
    print("  Browser Login — learn.redhat.com")
    print("=" * 60)
    print("  A browser window will open at learn.redhat.com.")
    print("  Click 'Sign In' in the top-right corner and log in")
    print("  with your Red Hat account (SSO / username+password).")
    print("  Once you are fully logged in, come back here and")
    print("  press Enter to continue.")
    print("=" * 60)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(BASE_URL, timeout=60000)
            print("  Browser opened. Please click 'Sign In' and log in...")
            input("  Press Enter after you have logged in: ")
            cookies = context.cookies()
            browser.close()
        if not cookies:
            return False, "No cookies captured from browser"
        for c in cookies:
            session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""), path=c.get("path", "/"))
        logger.info(f"  Captured {len(cookies)} cookies from browser session")
        if save_cookies_path:
            jar = http.cookiejar.MozillaCookieJar(save_cookies_path)
            for c in session.cookies:
                jar.set_cookie(c)
            try:
                jar.save(ignore_discard=True, ignore_expires=True)
                logger.info(f"  Cookies saved to {save_cookies_path}")
            except Exception as e:
                logger.warning(f"  Could not save cookies: {e}")
        return True, "ok"
    except Exception as e:
        return False, str(e)


def download_community_json(dest_path, save_cookies_path=None):
    """
    Use Playwright to:
      1. Open a real Chromium browser so the user can log in to learn.redhat.com
      2. Navigate to the Advanced Profile page
      3. Click "My community content" to trigger the JSON download
      4. Save the downloaded file to dest_path
      5. Optionally save session cookies to save_cookies_path

    Returns (True, session_cookies_list) on success, (False, error_message) on failure.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        return False, "playwright not installed — run: uv pip install playwright && uv run playwright install chromium"

    # Known profile page URLs on learn.redhat.com (Khoros).
    # We try each in order and search for the download link on each page.
    PROFILE_URLS_TO_TRY = [
        # Advanced Profile tab — where "My community content" download lives
        f"{BASE_URL}/t5/user/myprofilepage/tab/personal-profile:advanced-profile",
        # Personal info tab (confirmed reachable by user)
        f"{BASE_URL}/t5/user/myprofilepage/tab/personal-profile:personal-info",
        # Legacy / alternate Khoros paths
        f"{BASE_URL}/t5/s/personal-settings/advanced-profile",
        f"{BASE_URL}/t5/user/myprofilepage/tab/personal-profile:privacy-settings",
    ]

    # Selectors tried in order for the "My community content" download element.
    DOWNLOAD_SELECTORS = [
        "a[href*='downloadmycommunitycontentpage']",
        "a[href*='download-my-community-content']",
        "a[href*='DownloadMyCommunityContent']",
        "a[href*='community-content']",
        "a[href*='my_community_content']",
        "a[data-action='download-community-content']",
        "button[data-action='download-community-content']",
    ]
    DOWNLOAD_TEXT_PHRASES = [
        "My community content",
        "my community content",
        "Download my community content",
        "community content",
    ]

    def _find_download_link(pg):
        """Search for the download link on the current page. Returns locator or None."""
        for sel in DOWNLOAD_SELECTORS:
            try:
                el = pg.locator(sel).first
                if el.count() > 0:
                    logger.info(f"  Found download element via selector: {sel}")
                    return el
            except Exception:
                continue
        for phrase in DOWNLOAD_TEXT_PHRASES:
            try:
                el = pg.get_by_text(phrase, exact=False).first
                if el.count() > 0:
                    logger.info(f"  Found download element via text: '{phrase}'")
                    return el
            except Exception:
                continue
        return None

    def _debug_page_links(pg):
        """Log all links/buttons on the page to help identify the right selector."""
        try:
            all_els = pg.locator("a, button").all()
            logger.info(f"  Page has {len(all_els)} links/buttons:")
            for el in all_els[:80]:
                try:
                    txt = (el.inner_text() or "").strip()[:80]
                    href = el.get_attribute("href") or ""
                    tag = el.evaluate("e => e.tagName")
                    if txt or href:
                        logger.info(f"    [{tag}] text={txt!r}  href={href!r}")
                except Exception:
                    pass
        except Exception:
            pass

    print("\n" + "=" * 60)
    print("  Auto-download: My Community Content JSON")
    print("=" * 60)
    print("  A browser window will open at learn.redhat.com.")
    print()
    print("  ⚠️  IMPORTANT: Click 'Sign In' in the top-right corner")
    print("  of the page and log in with your Red Hat account.")
    print("  Do NOT navigate away — wait until you are fully logged in,")
    print("  then come back here and press Enter.")
    print()
    print("  The script will then navigate to your Advanced Profile")
    print("  and download your community content JSON automatically.")
    print("=" * 60)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            # Step 1: Open the homepage so the user can click Sign In
            logger.info("  Opening browser at learn.redhat.com — please click Sign In and log in...")
            page.goto(BASE_URL, timeout=60000)
            input("\n  Press Enter after you have fully logged in: ")

            # Step 2: Try each profile URL until we find the download link
            download_link = None
            for profile_url in PROFILE_URLS_TO_TRY:
                logger.info(f"  Trying profile URL: {profile_url}")
                try:
                    page.goto(profile_url, timeout=30000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except PWTimeout:
                        pass
                    download_link = _find_download_link(page)
                    if download_link is not None:
                        logger.info(f"  Download link found on: {profile_url}")
                        break
                    logger.info(f"  Download link not found on: {profile_url}")
                except Exception as nav_err:
                    logger.warning(f"  Could not navigate to {profile_url}: {nav_err}")
                    continue

            # Debug: if still not found, log all links on the last page visited
            if download_link is None:
                logger.info("  Download link not found on any profile URL. Logging page links for diagnosis:")
                _debug_page_links(page)

            if download_link is None:
                # Last resort: leave browser open for manual click
                print("\n  Could not automatically locate the 'My community content' download button.")
                print("  The browser is still open — please navigate to your Advanced Profile")
                print(f"  ({BASE_URL}/t5/user/myprofilepage/tab/personal-profile:advanced-profile)")
                print("  and click 'My community content' to start the download.")
                print("  After clicking, press Enter here to continue.")
                with page.expect_download(timeout=120000) as dl_info:
                    input("  Press Enter after clicking the download button: ")
                download = dl_info.value
            else:
                logger.info("  Clicking download button...")
                with page.expect_download(timeout=60000) as dl_info:
                    download_link.click()
                download = dl_info.value

            # Step 4: Save the downloaded file
            dest = Path(dest_path)
            download.save_as(str(dest))
            logger.info(f"  Community JSON saved to: {dest.resolve()}")

            # Step 5: Capture cookies for the requests session
            cookies = context.cookies()
            browser.close()

        # Optionally persist cookies to file
        if save_cookies_path and cookies:
            import http.cookiejar as _cj
            jar = _cj.MozillaCookieJar(save_cookies_path)
            # We can't easily convert Playwright cookies to http.cookiejar without a live
            # requests session, so we write a minimal Netscape file directly.
            lines = ["# Netscape HTTP Cookie File\n"]
            for c in cookies:
                domain = c.get("domain", "")
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = c.get("path", "/")
                secure = "TRUE" if c.get("secure", False) else "FALSE"
                expires = int(c.get("expires", 0)) if c.get("expires") else 0
                name = c.get("name", "")
                value = c.get("value", "")
                lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
            Path(save_cookies_path).write_text("".join(lines), encoding="utf-8")
            logger.info(f"  Session cookies saved to: {save_cookies_path}")

        return True, cookies

    except Exception as e:
        return False, str(e)

def interactive_login(session, save_cookies_path=None):
    """
    learn.redhat.com is a JavaScript SPA — form-based login via requests is not
    possible. This function attempts Playwright browser login if available,
    otherwise prints clear instructions for the cookie-file method.
    """
    print("\n" + "="*60)
    print("  Authentication Required - learn.redhat.com")
    print("="*60)
    print("  learn.redhat.com uses a JavaScript SSO flow that cannot")
    print("  be automated with a plain HTTP client.")
    print("="*60)
    # Try Playwright first
    ok, msg = _playwright_login(session, save_cookies_path)
    if ok:
        return True
    if "playwright not installed" not in msg:
        logger.warning(f"Browser login failed: {msg}")
    _print_cookie_help()
    return False

def _playwright_available():
    try:
        import importlib
        importlib.import_module("playwright.sync_api")
        return True
    except ImportError:
        return False

def setup_session(args):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    if args.no_auth:
        logger.info("Skipping authentication (--no-auth)")
        return session
    if args.cookies:
        if not load_cookies_file(args.cookies, session):
            logger.error("Cookie file failed to load. Cannot authenticate.")
            _print_cookie_help()
            raise SystemExit(1)
        return session
    # No --cookies provided: try Playwright or exit with instructions
    if _playwright_available():
        save_path = "cookies.txt" if args.save_cookies else None
        ok, msg = _playwright_login(session, save_cookies_path=save_path)
        if ok:
            return session
        logger.error(f"Playwright login failed: {msg}")
    else:
        print("\n" + "="*60)
        print("  Authentication Required - learn.redhat.com")
        print("="*60)
        print("  learn.redhat.com uses a JavaScript SSO flow.")
        print("  Choose one of these options:")
        print()
        print("  OPTION 1 — Install Playwright (opens a browser for login):")
        print("    uv pip install playwright")
        print("    uv run playwright install chromium")
        print("    uv run export_community.py --save-cookies")
        print()
        print("  OPTION 2 — Export cookies from your browser:")
        print("    1. Log in to https://learn.redhat.com in Chrome/Firefox")
        print("    2. Install Cookie-Editor extension")
        print("    3. Export -> Netscape format -> save as cookies.txt")
        print("    4. uv run export_community.py --cookies cookies.txt")
        print()
        print("  OPTION 3 — Skip auth (images will be placeholders):")
        print("    uv run export_community.py --no-auth")
        print("="*60 + "\n")
    raise SystemExit(1)

def _apply_playwright_cookies(cookies_list, session):
    """Inject a list of Playwright cookie dicts directly into a requests.Session."""
    for c in cookies_list:
        name = c.get("name", "")
        value = c.get("value", "")
        if not name:
            continue
        session.cookies.set(
            name,
            value,
            domain=c.get("domain", ""),
            path=c.get("path", "/"),
        )
    logger.info(f"Injected {len(cookies_list)} Playwright cookies into requests session")

def slugify(text, max_len=80):
    text = text.strip()
    text = text.replace("&", "and").replace("/", "_").replace("\\", "_")
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[_\-]{2,}", "_", text)
    text = text.strip("_-")
    return text[:max_len]

def make_post_filename(section, subject, used_slugs):
    base = f"{slugify(section, 40)}-{slugify(subject, 60)}"
    if base not in used_slugs:
        used_slugs[base] = 1
        return f"{base}.html"
    used_slugs[base] += 1
    return f"{base}_{used_slugs[base]}.html"

def download_assets(output_dir, skip):
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    js_path = assets_dir / "highlight.min.js"
    css_path = assets_dir / "highlight.min.css"
    if not skip:
        for url, dest in [(HLJS_JS_URL, js_path), (HLJS_CSS_URL, css_path)]:
            if dest.exists():
                logger.info(f"Asset exists, skipping: {dest.name}")
                continue
            try:
                logger.info(f"Downloading asset: {dest.name}")
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                dest.write_bytes(r.content)
            except Exception as e:
                log_error(f"Failed to download asset {url}: {e}")
    return "../assets/highlight.min.js", "../assets/highlight.min.css"

def extract_image_id_from_url(url):
    m = re.search(r"/image-id/([^/]+)/", url)
    return m.group(1) if m else None

def _try_download_image(image_id, url, images_dir, session, image_map):
    try:
        resp = session.get(url, timeout=30, stream=True)
        if resp.status_code in (401, 403, 404):
            return None
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
        ext = MIME_TO_EXT.get(ct, ".png")
        filename = f"{image_id}{ext}"
        dest = images_dir / filename
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        image_map[image_id] = filename
        logger.info(f"  On-the-fly downloaded: {filename}")
        return filename
    except Exception:
        return None

def download_images(image_urls, images_dir, session, skip):
    images_dir.mkdir(parents=True, exist_ok=True)
    image_map = {}
    if skip:
        logger.info("Skipping image downloads. Building map from existing files.")
        for f in images_dir.iterdir():
            if f.is_file():
                image_map[f.stem] = f.name
        return image_map
    total = len(image_urls)
    logger.info(f"Downloading {total} images...")
    for i, url in enumerate(image_urls, 1):
        image_id = extract_image_id_from_url(url)
        if not image_id:
            log_error(f"Could not extract image ID from: {url}")
            continue
        existing = list(images_dir.glob(f"{image_id}.*"))
        if existing:
            image_map[image_id] = existing[0].name
            continue
        try:
            logger.info(f"  [{i}/{total}] Downloading image {image_id}")
            resp = session.get(url, timeout=30, stream=True)
            if resp.status_code in (401, 403):
                log_error(f"Auth error ({resp.status_code}) for image {image_id}")
                continue
            resp.raise_for_status()
            ct = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
            ext = MIME_TO_EXT.get(ct, "") or mimetypes.guess_extension(ct) or ".bin"
            filename = f"{image_id}{ext}"
            dest = images_dir / filename
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            image_map[image_id] = filename
            time.sleep(0.1)
        except requests.RequestException as e:
            log_error(f"Failed to download image {image_id}: {e}")
    logger.info(f"Downloaded {len(image_map)} images.")
    return image_map

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.strip(". ")
    return name or "attachment"

def download_attachments(messages, attachments_dir, session, skip):
    attachments_dir.mkdir(parents=True, exist_ok=True)
    url_to_local = {}
    used_names = {}
    if skip:
        logger.info("Skipping attachment downloads.")
        return url_to_local
    all_atts = [att for msg in messages for att in msg.get("attachments", [])]
    total = len(all_atts)
    if total == 0:
        logger.info("No attachments found.")
        return url_to_local
    logger.info(f"Downloading {total} attachments...")
    for i, att in enumerate(all_atts, 1):
        url = att.get("url", "")
        filename = sanitize_filename(att.get("filename", "attachment"))
        if not url or url in url_to_local:
            continue
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        base_name = filename
        if base_name in used_names:
            used_names[base_name] += 1
            filename = f"{stem}_{used_names[base_name]}{suffix}"
        else:
            used_names[base_name] = 1
        dest = attachments_dir / filename
        if dest.exists():
            url_to_local[url] = filename
            continue
        try:
            logger.info(f"  [{i}/{total}] Downloading: {filename}")
            resp = session.get(url, timeout=60, stream=True)
            if resp.status_code in (401, 403):
                log_error(f"Auth error ({resp.status_code}) for: {url}")
                continue
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            url_to_local[url] = filename
            time.sleep(0.1)
        except requests.RequestException as e:
            log_error(f"Failed to download {filename}: {e}")
    logger.info(f"Downloaded {len(url_to_local)} attachments.")
    return url_to_local

def transform_body_html(body_html, image_map, url_to_local_attachment, session, images_dir):
    if not body_html:
        return ""
    soup = BeautifulSoup(body_html, "lxml")
    for tag in soup.find_all("li-image"):
        image_id = tag.get("id", "")
        alt_text = tag.get("alt", "")
        width = tag.get("width", "")
        local_file = image_map.get(image_id)
        if not local_file:
            img_url = f"{BASE_URL}/t5/image/serverpage/image-id/{image_id}/image-size/original?v=v2&px=-1"
            local_file = _try_download_image(image_id, img_url, images_dir, session, image_map)
        if local_file:
            img_tag = soup.new_tag("img")
            img_tag["src"] = f"../images/{local_file}"
            img_tag["alt"] = str(alt_text) if alt_text is not None else ""
            img_tag["class"] = "post-image"
            if width:
                img_tag["style"] = f"max-width: min({width}px, 100%);"
            tag.replace_with(img_tag)
        else:
            ph = soup.new_tag("span")
            ph["class"] = "missing-image"
            ph.string = f"[Image: {image_id}]"
            tag.replace_with(ph)
    lang_map = {"markup": "xml", "bash": "bash", "shell": "bash", "python": "python",
                "yaml": "yaml", "json": "json", "ini": "ini", "plaintext": "plaintext", "text": "plaintext"}
    for tag in soup.find_all("li-code"):
        lang = str(tag.get("lang") or "plaintext")
        hljs_lang = lang_map.get(lang.lower(), lang.lower())
        pre_tag = soup.new_tag("pre")
        code_tag = soup.new_tag("code")
        code_tag["class"] = f"language-{hljs_lang}"
        code_tag.string = tag.get_text()
        pre_tag.append(code_tag)
        tag.replace_with(pre_tag)
    for tag in soup.find_all("li-user"):
        uid = tag.get("uid", "")
        span = soup.new_tag("span")
        span["class"] = "user-mention"
        span.string = f"@user_{uid}" if uid else "@user"
        tag.replace_with(span)
    for tag in soup.find_all("li-emoji"):
        emoji_id = str(tag.get("id") or "")
        title = str(tag.get("title") or "")
        emoji_char = EMOJI_MAP.get(emoji_id, "") or title.strip(":")
        span = soup.new_tag("span")
        span["class"] = "emoji"
        span["title"] = title
        span.string = emoji_char or "😊"
        tag.replace_with(span)
    body = soup.find("body")
    if body:
        return "".join(str(c) for c in body.children)
    return str(soup)

INLINE_CSS = """
*, *::before, *::after { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #1a1a1a; background: #f5f5f5; margin: 0; padding: 0; }
.container { max-width: 960px; margin: 0 auto; background: #fff; min-height: 100vh; box-shadow: 0 0 20px rgba(0,0,0,0.08); }
.site-header { background: #cc0000; color: #fff; padding: 18px 28px; }
.site-header h1 { margin: 0; font-size: 1.3rem; font-weight: 700; }
.site-header .subtitle { font-size: 0.82rem; opacity: 0.85; margin-top: 3px; }
.content-area { padding: 24px 28px; }
.breadcrumb { font-size: 0.83rem; color: #666; padding-bottom: 14px; border-bottom: 1px solid #eee; margin-bottom: 20px; }
.breadcrumb a { color: #cc0000; text-decoration: none; }
.breadcrumb a:hover { text-decoration: underline; }
.breadcrumb .sep { margin: 0 6px; color: #bbb; }
h1.post-title { font-size: 1.45rem; font-weight: 700; color: #1a1a1a; margin: 0 0 10px 0; line-height: 1.3; }
.post-meta { font-size: 0.83rem; color: #666; margin-bottom: 24px; padding-bottom: 14px; border-bottom: 2px solid #cc0000; }
.section-badge { display: inline-block; background: #cc0000; color: #fff; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; margin-right: 8px; text-transform: uppercase; letter-spacing: 0.05em; }
.post-body { line-height: 1.75; color: #222; }
.post-body p { margin: 0 0 1em 0; }
.post-body ul, .post-body ol { margin: 0 0 1em 1.5em; padding: 0; }
.post-body li { margin-bottom: 0.3em; }
.post-body a { color: #cc0000; word-break: break-word; }
.post-body a:hover { text-decoration: underline; }
.post-body strong { font-weight: 700; }
.post-body em { font-style: italic; }
.post-body table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.88rem; display: block; overflow-x: auto; }
.post-body th, .post-body td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; vertical-align: top; }
.post-body th { background: #f0f0f0; font-weight: 600; }
.post-body tr:nth-child(even) td { background: #fafafa; }
.post-body pre { background: #f4f4f4; border: 1px solid #ddd; border-left: 4px solid #cc0000; border-radius: 4px; padding: 16px; overflow-x: auto; margin: 1em 0; font-size: 0.85rem; line-height: 1.5; }
.post-body code { font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 0.875em; background: #f0f0f0; padding: 2px 5px; border-radius: 3px; }
.post-body pre code { background: none; padding: 0; font-size: inherit; }
.post-body img.post-image { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; margin: 1em 0; display: block; }
.missing-image { display: inline-block; background: #fff3cd; border: 1px solid #ffc107; color: #856404; padding: 3px 8px; border-radius: 4px; font-size: 0.82rem; font-style: italic; }
.user-mention { display: inline-block; background: #e8f0fe; color: #1a73e8; padding: 1px 6px; border-radius: 10px; font-size: 0.875em; font-weight: 500; }
.emoji { font-style: normal; }
.attachments-section { margin-top: 32px; padding-top: 20px; border-top: 1px solid #eee; }
.attachments-section h3 { font-size: 0.82rem; font-weight: 700; color: #555; margin: 0 0 12px 0; text-transform: uppercase; letter-spacing: 0.06em; }
.attachment-list { list-style: none; padding: 0; margin: 0; }
.attachment-list li { display: flex; align-items: center; gap: 10px; padding: 9px 14px; background: #f8f8f8; border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 8px; }
.attachment-list li a { color: #cc0000; text-decoration: none; font-weight: 500; flex: 1; }
.attachment-list li a:hover { text-decoration: underline; }
.attachment-icon { font-size: 1.1em; flex-shrink: 0; }
.attachment-badge { font-size: 0.72rem; background: #e0e0e0; color: #555; padding: 2px 7px; border-radius: 10px; margin-left: auto; flex-shrink: 0; }
.pdf-embed { width: 100%; height: 620px; border: 1px solid #ddd; border-radius: 4px; margin-top: 10px; display: block; }
.json-embed { background: #f4f4f4; border: 1px solid #ddd; border-left: 4px solid #1a73e8; border-radius: 4px; padding: 14px; overflow: auto; max-height: 400px; font-size: 0.82rem; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; white-space: pre; margin-top: 10px; }
.index-header { margin-bottom: 28px; }
.index-header h1 { font-size: 1.8rem; font-weight: 700; margin: 0 0 6px 0; }
.index-header p { color: #666; margin: 0; font-size: 0.9rem; }
.stats-bar { background: #f5f5f5; border-radius: 6px; padding: 12px 16px; margin-bottom: 28px; font-size: 0.84rem; color: #555; display: flex; gap: 20px; flex-wrap: wrap; border: 1px solid #e8e8e8; }
.stats-bar span strong { color: #1a1a1a; }
.section-group { margin-bottom: 32px; }
.section-group h2 { font-size: 0.9rem; font-weight: 700; color: #cc0000; text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 10px 0; padding-bottom: 7px; border-bottom: 2px solid #cc0000; }
.post-list { list-style: none; padding: 0; margin: 0; }
.post-list li { padding: 8px 0; border-bottom: 1px solid #f0f0f0; display: flex; align-items: baseline; gap: 10px; }
.post-list li:last-child { border-bottom: none; }
.post-list a { color: #1a1a1a; text-decoration: none; font-size: 0.93rem; flex: 1; }
.post-list a:hover { color: #cc0000; text-decoration: underline; }
.attachment-count-badge { font-size: 0.7rem; background: #cc0000; color: #fff; padding: 2px 7px; border-radius: 10px; white-space: nowrap; flex-shrink: 0; }
.back-link { display: inline-flex; align-items: center; gap: 5px; color: #cc0000; text-decoration: none; font-size: 0.88rem; font-weight: 500; margin-bottom: 18px; }
.back-link:hover { text-decoration: underline; }
.site-footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #eee; font-size: 0.78rem; color: #aaa; text-align: center; }
@media (max-width: 640px) { .content-area { padding: 16px 14px; } .post-body pre { font-size: 0.78rem; } .stats-bar { flex-direction: column; gap: 5px; } .site-header { padding: 14px 16px; } }
"""

def _get_attachment_icon(filename):
    ext = Path(filename).suffix.lower()
    return {".pdf": "📄", ".json": "📋", ".zip": "📦", ".tar": "📦", ".gz": "📦",
            ".rpm": "📦", ".png": "🖼️", ".jpg": "🖼️", ".jpeg": "🖼️", ".gif": "🖼️",
            ".mp4": "🎬", ".mp3": "🎵", ".txt": "📝", ".md": "📝", ".csv": "📊",
            ".xlsx": "📊", ".docx": "📝", ".pptx": "📊"}.get(ext, "📎")

def _he(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))

def render_attachment_section(attachments, url_to_local, attachments_dir):
    if not attachments:
        return ""
    items_html = ""
    embeds_html = ""
    for att in attachments:
        url = att.get("url", "")
        filename = att.get("filename", "attachment")
        scan_status = att.get("scan_status", "")
        local_name = url_to_local.get(url, "")
        icon = _get_attachment_icon(filename)
        ext = Path(filename).suffix.lower()
        if local_name:
            link_html = f'<a href="../attachments/{local_name}" download="{_he(local_name)}">{_he(filename)}</a>'
        else:
            link_html = f'<a href="{_he(url)}" target="_blank" rel="noopener">{_he(filename)}</a> <em>(not downloaded)</em>'
        badge = f'<span class="attachment-badge">{_he(scan_status)}</span>' if scan_status else ""
        items_html += f'<li><span class="attachment-icon">{icon}</span>{link_html}{badge}</li>\n'
        if ext == ".pdf" and local_name:
            embeds_html += (f'<div style="margin-bottom:20px;"><p style="font-size:0.85rem;color:#666;margin:0 0 6px 0;">'
                            f'Preview: <strong>{_he(filename)}</strong></p>'
                            f'<iframe class="pdf-embed" src="../attachments/{local_name}" title="{_he(filename)}"></iframe></div>\n')
        elif ext == ".json" and local_name:
            json_path = attachments_dir / local_name
            if json_path.exists():
                try:
                    raw = json_path.read_text(encoding="utf-8")
                    pretty = _he(json.dumps(json.loads(raw), indent=2))
                    embeds_html += (f'<div style="margin-bottom:20px;"><p style="font-size:0.85rem;color:#666;margin:0 0 6px 0;">'
                                    f'Contents: <strong>{_he(filename)}</strong></p>'
                                    f'<div class="json-embed">{pretty}</div></div>\n')
                except Exception:
                    pass
    return (f'<div class="attachments-section">\n<h3>📎 Attachments ({len(attachments)})</h3>\n'
            f'<ul class="attachment-list">\n{items_html}</ul>\n{embeds_html}</div>\n')

def build_post_html(msg, transformed_body, url_to_local_attachment, attachments_dir, hljs_js, hljs_css):
    section = msg.get("forum") or msg.get("blog") or "General"
    subject = msg.get("subject", "Untitled")
    attachments = msg.get("attachments", [])
    att_html = render_attachment_section(attachments, url_to_local_attachment, attachments_dir)
    return (
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>{_he(subject)} - {_he(section)}</title>\n'
        f'<link rel="stylesheet" href="{hljs_css}">\n'
        f'<style>{INLINE_CSS}</style>\n</head>\n<body>\n'
        f'<div class="site-header"><h1>Red Hat Learning Community</h1><div class="subtitle">Offline Archive</div></div>\n'
        f'<div class="container"><div class="content-area">\n'
        f'<a class="back-link" href="../rhtlc_main.html">&#8592; Back to Index</a>\n'
        f'<div class="breadcrumb"><a href="../rhtlc_main.html">Index</a>'
        f'<span class="sep">›</span><span>{_he(section)}</span>'
        f'<span class="sep">›</span><span>{_he(subject)}</span></div>\n'
        f'<h1 class="post-title">{_he(subject)}</h1>\n'
        f'<div class="post-meta"><span class="section-badge">{_he(section)}</span></div>\n'
        f'<div class="post-body">\n{transformed_body}\n</div>\n'
        f'{att_html}'
        f'<div class="site-footer">Exported from learn.redhat.com &mdash; Offline Archive</div>\n'
        f'</div></div>\n'
        f'<script src="{hljs_js}"></script>\n'
        f'<script>document.addEventListener("DOMContentLoaded",function(){{document.querySelectorAll("pre code").forEach(function(b){{hljs.highlightElement(b);}});}});</script>\n'
        f'</body>\n</html>'
    )

def build_index_html(posts_meta, hljs_js, hljs_css):
    sections = defaultdict(list)
    for pm in posts_meta:
        sections[pm["section"]].append(pm)
    total_posts = len(posts_meta)
    total_sections = len(sections)
    total_attachments = sum(pm["attachment_count"] for pm in posts_meta)
    stats_html = (f'<div class="stats-bar">'
                  f'<span><strong>{total_posts}</strong> posts</span>'
                  f'<span><strong>{total_sections}</strong> sections</span>'
                  f'<span><strong>{total_attachments}</strong> attachments</span>'
                  f'</div>\n')
    sections_html = ""
    for section_name in sorted(sections.keys()):
        posts = sections[section_name]
        items_html = ""
        for pm in posts:
            badge = (f'<span class="attachment-count-badge">📎 {pm["attachment_count"]}</span>'
                     if pm["attachment_count"] > 0 else "")
            items_html += f'<li><a href="posts/{pm["filename"]}">{_he(pm["subject"])}</a>{badge}</li>\n'
        sections_html += (f'<div class="section-group">\n<h2>{_he(section_name)}</h2>\n'
                          f'<ul class="post-list">\n{items_html}</ul>\n</div>\n')
    return (
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>Red Hat Learning Community - Offline Archive</title>\n'
        f'<link rel="stylesheet" href="{hljs_css}">\n'
        f'<style>{INLINE_CSS}</style>\n</head>\n<body>\n'
        f'<div class="site-header"><h1>Red Hat Learning Community</h1><div class="subtitle">Offline Archive - All Posts</div></div>\n'
        f'<div class="container"><div class="content-area">\n'
        f'<div class="index-header"><h1>Post Index</h1><p>All community posts exported from learn.redhat.com</p></div>\n'
        f'{stats_html}{sections_html}'
        f'<div class="site-footer">Exported from learn.redhat.com &mdash; Offline Archive</div>\n'
        f'</div></div>\n</body>\n</html>'
    )

def main():
    args = parse_args()
    json_path = Path(args.json)

    # --auto implies --fetch-json + --save-cookies
    if args.auto:
        args.fetch_json = True
        args.save_cookies = True

    # playwright_cookies holds the raw cookie list returned by download_community_json()
    # so we can inject them directly into the requests.Session without a file round-trip.
    playwright_cookies = None

    # --fetch-json: use Playwright to log in, download my_community_content.json, then continue
    if args.fetch_json:
        if not _playwright_available():
            logger.error(
                "--fetch-json / --auto requires Playwright.\n"
                "  Install it with:\n"
                "    uv pip install playwright\n"
                "    uv run playwright install chromium\n"
                "  Then re-run with --fetch-json or --auto"
            )
            raise SystemExit(1)
        save_cookies_path = "cookies.txt" if args.save_cookies else None
        ok, result = download_community_json(json_path, save_cookies_path=save_cookies_path)
        if not ok:
            logger.error(f"Failed to download community JSON: {result}")
            raise SystemExit(1)
        # result is the list of Playwright cookie dicts — keep them for direct injection below
        playwright_cookies = result if isinstance(result, list) else None
        # Also point --cookies at the saved file as a fallback (used only if direct injection fails)
        if save_cookies_path and Path(save_cookies_path).exists():
            args.cookies = save_cookies_path

    # Load the JSON (must exist by now, either pre-existing or just downloaded)
    if not json_path.exists():
        logger.error(
            f"JSON file not found: {json_path}\n"
            "  Download it from learn.redhat.com (Advanced Profile → My community content)\n"
            "  or run with --fetch-json / --auto to download it automatically."
        )
        raise SystemExit(1)
    logger.info(f"Loading {json_path}")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    image_urls = data.get("images", [])
    messages = data.get("messages", [])
    logger.info(f"Found {len(image_urls)} images and {len(messages)} messages")

    output_dir = Path(args.output)
    posts_dir = output_dir / "posts"
    images_dir = output_dir / "images"
    attachments_dir = output_dir / "attachments"
    for d in [output_dir, posts_dir, images_dir, attachments_dir]:
        d.mkdir(parents=True, exist_ok=True)

    if playwright_cookies:
        # We already have a live authenticated Playwright session — build the requests.Session
        # and inject the cookies directly.  This avoids the Netscape file round-trip and
        # guarantees the same cookies used to download the JSON are used for images/attachments.
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        _apply_playwright_cookies(playwright_cookies, session)
    else:
        session = setup_session(args)
    hljs_js, hljs_css = download_assets(output_dir, args.skip_assets)
    image_map = download_images(image_urls, images_dir, session, args.skip_images)
    url_to_local_attachment = download_attachments(messages, attachments_dir, session, args.skip_attachments)
    used_slugs = {}
    posts_meta = []
    logger.info(f"Generating {len(messages)} post HTML files...")
    for i, msg in enumerate(messages, 1):
        section = msg.get("forum") or msg.get("blog") or "General"
        subject = msg.get("subject", "Untitled")
        filename = make_post_filename(section, subject, used_slugs)
        att_count = len(msg.get("attachments", []))
        transformed_body = transform_body_html(
            msg.get("body", ""), image_map, url_to_local_attachment, session, images_dir)
        post_html = build_post_html(
            msg, transformed_body, url_to_local_attachment, attachments_dir, hljs_js, hljs_css)
        (posts_dir / filename).write_text(post_html, encoding="utf-8")
        posts_meta.append({"section": section, "subject": subject,
                            "filename": filename, "attachment_count": att_count})
        if i % 10 == 0 or i == len(messages):
            logger.info(f"  Generated {i}/{len(messages)} posts")
    logger.info("Generating master index: rhtlc_main.html")
    index_html = build_index_html(posts_meta, "assets/highlight.min.js", "assets/highlight.min.css")
    (output_dir / "rhtlc_main.html").write_text(index_html, encoding="utf-8")
    if error_log_entries:
        error_log_path = output_dir / "download_errors.log"
        error_log_path.write_text("\n".join(error_log_entries), encoding="utf-8")
        logger.warning(f"{len(error_log_entries)} errors logged to {error_log_path}")
    logger.info(f"\nDone! Output written to: {output_dir.resolve()}")
    logger.info(f"  Open {output_dir.resolve()}/rhtlc_main.html in your browser to view.")

if __name__ == "__main__":
    main()
