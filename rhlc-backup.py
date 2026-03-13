#!/usr/bin/env python3
"""
rhlc-backup.py - Complete Khoros Community Site Backup for learn.redhat.com

This script performs a full backup of the Khoros community site by:
1. Authenticating to learn.redhat.com using browser login or cookies
2. Crawling the site structure (boards, categories, messages)
3. Downloading all accessible content, images, and attachments
4. Creating a complete offline archive with threaded HTML pages

Usage:
    uv run rhlc-backup.py [options]
    python rhlc-backup.py [options]

Requirements:
    - Moderator/admin access to learn.redhat.com
    - Playwright for browser authentication (or exported cookies)
    - uv pip install playwright requests beautifulsoup4 lxml
    - uv run playwright install chromium
"""

import argparse
import http.cookiejar
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

# Import HTML generation functions
from html_generator import (
    group_messages_by_thread,
    generate_thread_html,
    generate_index_html
)

# Configuration
BASE_URL = "https://learn.redhat.com"
HLJS_JS_URL = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"
HLJS_CSS_URL = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css"

# Rate limiting
REQUEST_DELAY = 1.0  # seconds between requests
MAX_RETRIES = 3

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)
error_log_entries = []


def log_error(msg):
    """Log error message to both logger and error list."""
    logger.error(msg)
    error_log_entries.append(msg)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="rhlc-backup.py",
        description="Complete backup of Khoros community site from learn.redhat.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rhlc-backup.py --auto
  python rhlc-backup.py --cookies cookies.txt
  python rhlc-backup.py --output ./full-backup
  python rhlc-backup.py --max-pages 10  # Test mode

Authentication:
  --auto              : Use Playwright to log in and save cookies automatically
  --cookies FILE      : Use exported cookies from browser
  --save-cookies      : Save session cookies for future use

Content Selection:
  --max-pages N       : Limit total pages to crawl (for testing)
  --max-messages N    : Limit total messages to download (for testing)

Output Options:
  --output DIR        : Output directory (default: backup_YYYYMMDD_HHMMSS)
  --skip-images       : Skip downloading images
  --skip-attachments  : Skip downloading attachments
        """,
    )
    parser.add_argument("--output", default=None, metavar="DIR",
                       help="Output directory (default: backup_YYYYMMDD_HHMMSS)")
    parser.add_argument("--cookies", default=None, metavar="FILE",
                       help="Path to Netscape cookies file")
    parser.add_argument("--save-cookies", action="store_true",
                       help="Save session cookies to cookies.txt")
    parser.add_argument("--auto", action="store_true",
                       help="Auto-login with Playwright and save cookies")
    parser.add_argument("--skip-images", action="store_true",
                       help="Skip downloading images")
    parser.add_argument("--skip-attachments", action="store_true",
                       help="Skip downloading attachments")
    parser.add_argument("--max-pages", type=int, metavar="N",
                       help="Limit total pages to crawl (for testing)")
    parser.add_argument("--max-messages", type=int, metavar="N",
                       help="Limit total messages (for testing)")
    return parser.parse_args()


def load_cookies_file(path: str, session: requests.Session) -> bool:
    """Load cookies from Netscape format file."""
    jar = http.cookiejar.MozillaCookieJar(path)
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(jar)
        logger.info(f"Loaded {sum(1 for _ in jar)} cookies from {path}")
        return True
    except Exception as e:
        log_error(f"Failed to load cookies from {path}: {e}")
        return False


def save_cookies_file(path: str, session: requests.Session):
    """Save session cookies to Netscape format file."""
    jar = http.cookiejar.MozillaCookieJar(path)
    for c in session.cookies:
        jar.set_cookie(c)
    try:
        jar.save(ignore_discard=True, ignore_expires=True)
        logger.info(f"Session cookies saved to {path}")
    except Exception as e:
        log_error(f"Failed to save cookies: {e}")


def playwright_login(session: requests.Session, save_cookies_path: Optional[str] = None) -> bool:
    """Use Playwright to log in via browser and capture cookies."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: uv pip install playwright && uv run playwright install chromium")
        return False

    print("\n" + "=" * 60)
    print("  Browser Login — learn.redhat.com")
    print("=" * 60)
    print("  A browser window will open. Please:")
    print("  1. Click 'Sign In' in the top-right corner")
    print("  2. Log in with your Red Hat account")
    print("  3. Wait until fully logged in")
    print("  4. Return here and press Enter")
    print("=" * 60)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(BASE_URL, timeout=60000)
            print("\n  Browser opened. Please log in...")
            input("  Press Enter after you have logged in: ")
            
            cookies = context.cookies()
            browser.close()

        if not cookies:
            logger.error("No cookies captured from browser")
            return False

        # Inject cookies into requests session
        for c in cookies:
            name = c.get("name", "")
            value = c.get("value", "")
            if name and value:
                session.cookies.set(
                    name,
                    value,
                    domain=c.get("domain", ""),
                    path=c.get("path", "/")
                )
        
        logger.info(f"Captured {len(cookies)} cookies from browser")

        # Save cookies if requested
        if save_cookies_path:
            save_cookies_file(save_cookies_path, session)

        return True

    except Exception as e:
        logger.error(f"Browser login failed: {e}")
        return False


def setup_session(args) -> requests.Session:
    """Set up authenticated requests session."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })

    # Try authentication methods in order
    if args.cookies:
        if not load_cookies_file(args.cookies, session):
            logger.error("Failed to load cookies file")
            raise SystemExit(1)
    elif args.auto:
        save_path = "cookies.txt" if args.save_cookies else None
        if not playwright_login(session, save_path):
            logger.error("Browser login failed")
            raise SystemExit(1)
    else:
        logger.error("Authentication required. Use --auto or --cookies")
        print("\nOptions:")
        print("  --auto              : Open browser for login")
        print("  --cookies FILE      : Use exported cookies")
        raise SystemExit(1)

    return session


def fetch_page(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
    """Fetch and parse a page."""
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY)
            response = session.get(url, timeout=30)
            
            if response.status_code == 200:
                return BeautifulSoup(response.text, "lxml")
            elif response.status_code in (401, 403):
                log_error(f"Access denied for {url}")
                return None
            elif response.status_code == 404:
                logger.warning(f"Not found: {url}")
                return None
            else:
                logger.warning(f"Status {response.status_code} for {url}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
        
        except Exception as e:
            log_error(f"Failed to fetch {url}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return None
    
    return None


def discover_boards(session: requests.Session) -> List[Dict]:
    """Discover all boards by crawling the community structure."""
    logger.info("Discovering community boards...")
    
    boards = []
    
    # Start from the main community page
    soup = fetch_page(session, f"{BASE_URL}/t5/forums/recentpostspage")
    if not soup:
        logger.warning("Could not fetch community page, trying alternative...")
        soup = fetch_page(session, BASE_URL)
    
    if not soup:
        log_error("Could not access community pages")
        return boards
    
    # Find all board links
    board_links = set()
    
    # Look for board links in navigation
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        
        # Match board URLs like /t5/board-name/bd-p/board-id
        if href and isinstance(href, str) and ("/bd-p/" in href or "/ct-p/" in href):
            full_url = urljoin(BASE_URL, href)
            board_links.add(full_url)
    
    logger.info(f"Found {len(board_links)} potential boards")
    
    # Visit each board to get details
    for i, board_url in enumerate(sorted(board_links), 1):
        logger.info(f"  [{i}/{len(board_links)}] Checking {board_url}")
        
        soup = fetch_page(session, board_url)
        if not soup:
            continue
        
        # Extract board info
        title_elem = soup.find("h1", class_=re.compile("lia-page-title"))
        if not title_elem:
            title_elem = soup.find("h1")
        
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Board"
        
        boards.append({
            "url": board_url,
            "title": title,
            "id": board_url.split("/")[-1] if "/" in board_url else "unknown"
        })
    
    logger.info(f"Discovered {len(boards)} boards")
    return boards


def extract_message_links(soup: BeautifulSoup) -> Set[str]:
    """Extract message/thread links from a page."""
    links = set()
    
    # Look for message links
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        
        # Match message URLs like /t5/board/thread/m-p/message-id
        if href and isinstance(href, str) and ("/m-p/" in href or "/td-p/" in href):
            full_url = urljoin(BASE_URL, href)
            links.add(full_url)
    
    return links


def crawl_board_messages(session: requests.Session, board: Dict, max_pages: Optional[int] = None) -> Set[str]:
    """Crawl all message links from a board with improved pagination."""
    logger.info(f"Crawling board: {board['title']}")
    
    all_message_links = set()
    page_num = 0
    board_url = board["url"]
    consecutive_empty = 0
    
    while True:
        if max_pages and page_num >= max_pages:
            logger.info(f"  Reached max pages limit: {max_pages}")
            break
        
        # Construct page URL - try multiple pagination patterns
        if page_num == 0:
            page_url = board_url
        else:
            # Try different pagination URL patterns
            page_url = f"{board_url}/page/{page_num + 1}"
        
        logger.info(f"  Fetching page {page_num + 1}: {page_url}")
        soup = fetch_page(session, page_url)
        
        if not soup:
            logger.warning(f"  Failed to fetch page {page_num + 1}")
            break
        
        # Extract message links
        message_links = extract_message_links(soup)
        
        if not message_links:
            consecutive_empty += 1
            logger.info(f"  No messages found on page {page_num + 1}")
            
            # Stop if we get 2 consecutive empty pages
            if consecutive_empty >= 2:
                logger.info(f"  No more messages after {consecutive_empty} empty pages")
                break
        else:
            new_links = message_links - all_message_links
            
            if not new_links:
                # All messages on this page were already seen
                consecutive_empty += 1
                logger.info(f"  Found 0 new messages (all duplicates) on page {page_num + 1}")
                
                # Stop if we get 2 consecutive pages with no new content
                if consecutive_empty >= 2:
                    logger.info(f"  No new content after {consecutive_empty} pages, moving to next board")
                    break
            else:
                consecutive_empty = 0
                all_message_links.update(message_links)
                logger.info(f"  Found {len(new_links)} new messages (total: {len(all_message_links)})")
        
        # Check for next page link
        next_link = soup.find("a", class_=re.compile("lia-link-navigation.*next|lia-paging-page-next"))
        if not next_link:
            # Also try finding pagination by text
            for link in soup.find_all("a"):
                link_text = link.get_text(strip=True)
                if link_text and re.search(r"Next|›|»", link_text, re.IGNORECASE):
                    next_link = link
                    break
        
        if not next_link:
            logger.info(f"  No next page link found, stopping")
            break
        
        page_num += 1
        
        # Safety limit - don't crawl more than 1000 pages per board
        if page_num >= 1000:
            logger.warning(f"  Reached safety limit of 1000 pages")
            break
    
    logger.info(f"  Total messages found in board: {len(all_message_links)}")
    return all_message_links


def extract_subject_from_url(url: str) -> str:
    """Extract subject from Khoros URL pattern as fallback."""
    # Pattern: /t5/BOARD/SUBJECT/td-p/ID or /t5/BOARD/SUBJECT/m-p/ID
    match = re.search(r'/t5/[^/]+/([^/]+?)/(td-p|m-p)/', url)
    if match:
        subject_slug = match.group(1)
        # Convert slug to readable title
        from urllib.parse import unquote
        subject = subject_slug.replace('-', ' ')
        subject = unquote(subject)
        # Capitalize first letter of each word
        subject = ' '.join(word.capitalize() for word in subject.split())
        return subject
    return "Untitled"


def extract_board_from_url(url: str) -> str:
    """Extract board name from Khoros URL pattern."""
    # Pattern: /t5/BOARD/...
    match = re.search(r'/t5/([^/]+)/', url)
    if match:
        board_slug = match.group(1)
        # Convert slug to readable name
        from urllib.parse import unquote
        board = board_slug.replace('-', ' ')
        board = unquote(board)
        # Capitalize appropriately
        board = ' '.join(word.capitalize() for word in board.split())
        return board
    return "Unknown Board"


def extract_message_content(soup: BeautifulSoup, url: str) -> Dict:
    """Extract message content from a page."""
    message = {
        "url": url,
        "subject": "",
        "body": "",
        "author": "",
        "post_time": "",
        "images": [],
        "attachments": [],
        "board": ""
    }
    
    # Extract subject - try multiple selectors
    subject_elem = soup.find("h1", class_=re.compile("lia-message-subject"))
    if not subject_elem:
        # Try page title
        subject_elem = soup.find("title")
    if not subject_elem:
        # Try any h1
        subject_elem = soup.find("h1")
    if not subject_elem:
        # Try meta og:title
        meta_title = soup.find("meta", property="og:title")
        if meta_title:
            content = meta_title.get("content")
            if content and isinstance(content, str):
                message["subject"] = content.strip()
    
    if subject_elem and not message["subject"]:
        title_text = subject_elem.get_text(strip=True)
        # Clean up title - remove site name suffix
        if " - Red Hat Learning Community" in title_text:
            title_text = title_text.split(" - Red Hat Learning Community")[0].strip()
        message["subject"] = title_text
    
    # Fallback: Extract subject from URL if still empty
    if not message["subject"]:
        message["subject"] = extract_subject_from_url(url)
    
    # Always extract board from URL
    message["board"] = extract_board_from_url(url)
    
    # Extract body
    body_elem = soup.find("div", class_=re.compile("lia-message-body"))
    if body_elem:
        message["body"] = str(body_elem)
        
        # Extract images from body
        for img in body_elem.find_all("img"):
            src = img.get("src")
            if src and isinstance(src, str):
                message["images"].append(urljoin(BASE_URL, src))
    
    # Extract author
    author_elem = soup.find("a", class_=re.compile("lia-user-name-link"))
    if author_elem:
        message["author"] = author_elem.get_text(strip=True)
    
    # Extract post time
    time_elem = soup.find("span", class_=re.compile("lia-message-post-date"))
    if time_elem:
        message["post_time"] = time_elem.get_text(strip=True)
    
    # Extract attachments
    for att_link in soup.find_all("a", class_=re.compile("lia-attachment")):
        href = att_link.get("href")
        if href and isinstance(href, str):
            message["attachments"].append({
                "url": urljoin(BASE_URL, href),
                "filename": att_link.get_text(strip=True)
            })
    
    return message


def download_messages(session: requests.Session, message_links: Set[str],
                     max_messages: Optional[int] = None,
                     output_dir: Optional[Path] = None) -> List[Dict]:
    """Download all messages and save incrementally to disk."""
    total = len(message_links)
    
    if max_messages:
        message_links = set(list(message_links)[:max_messages])
        total = len(message_links)
    
    logger.info(f"Downloading {total} messages...")
    
    # Create json directory and initialize messages file
    messages_file = None
    if output_dir:
        json_dir = output_dir / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        messages_file = json_dir / "messages.jsonl"  # JSON Lines format for streaming
        # Clear file if it exists
        if messages_file.exists():
            messages_file.unlink()
    
    downloaded_count = 0
    
    for i, url in enumerate(sorted(message_links), 1):
        logger.info(f"  [{i}/{total}] {url}")
        
        soup = fetch_page(session, url)
        if not soup:
            continue
        
        message = extract_message_content(soup, url)
        
        # Write message immediately to disk (JSON Lines format - one JSON object per line)
        if messages_file:
            with open(messages_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(message, ensure_ascii=False) + "\n")
        
        downloaded_count += 1
        
        # Log progress every 10 messages
        if i % 10 == 0:
            logger.info(f"  Progress: {downloaded_count}/{total} messages saved to disk")
    
    # Read all messages back from disk for return value (needed for media download)
    messages = []
    if messages_file and messages_file.exists():
        with open(messages_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
    
    logger.info(f"Total messages downloaded: {len(messages)}")
    return messages


def download_media(session: requests.Session, messages: List[Dict], 
                  output_dir: Path, args) -> Dict:
    """Download all images and attachments."""
    downloaded = {
        "images": {},
        "attachments": {}
    }
    
    # Collect all unique URLs
    image_urls = set()
    attachment_urls = []
    
    for msg in messages:
        image_urls.update(msg.get("images", []))
        attachment_urls.extend(msg.get("attachments", []))
    
    # Download images
    if not args.skip_images and image_urls:
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        total = len(image_urls)
        logger.info(f"Downloading {total} images...")
        
        for i, url in enumerate(sorted(image_urls), 1):
            try:
                time.sleep(REQUEST_DELAY)
                response = session.get(url, timeout=30, stream=True)
                
                if response.status_code == 200:
                    # Get content type to determine extension
                    content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
                    
                    # Map content type to extension
                    ext_map = {
                        "image/jpeg": ".jpg",
                        "image/jpg": ".jpg",
                        "image/png": ".png",
                        "image/gif": ".gif",
                        "image/webp": ".webp",
                        "image/svg+xml": ".svg",
                        "image/bmp": ".bmp",
                    }
                    
                    # Try to get filename from URL first
                    url_filename = Path(urlparse(url).path).name
                    if url_filename and "." in url_filename:
                        filename = url_filename
                    else:
                        # Generate filename with proper extension
                        ext = ext_map.get(content_type, ".png")
                        # Use hash of URL for unique filename
                        import hashlib
                        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                        filename = f"image_{url_hash}{ext}"
                    
                    dest = images_dir / filename
                    
                    with open(dest, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    downloaded["images"][url] = filename
                    
                    if i % 10 == 0:
                        logger.info(f"  Downloaded {i}/{total} images")
            
            except Exception as e:
                log_error(f"Failed to download image {url}: {e}")
        
        logger.info(f"Downloaded {len(downloaded['images'])} images")
    
    # Download attachments
    if not args.skip_attachments and attachment_urls:
        attachments_dir = output_dir / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)
        
        total = len(attachment_urls)
        logger.info(f"Downloading {total} attachments...")
        
        for i, att in enumerate(attachment_urls, 1):
            url = att["url"]
            filename = att["filename"] or f"attachment_{i}"
            
            try:
                time.sleep(REQUEST_DELAY)
                response = session.get(url, timeout=60, stream=True)
                
                if response.status_code == 200:
                    dest = attachments_dir / filename
                    
                    with open(dest, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    downloaded["attachments"][url] = filename
                    
                    if i % 10 == 0:
                        logger.info(f"  Downloaded {i}/{total} attachments")
            
            except Exception as e:
                log_error(f"Failed to download attachment {url}: {e}")
        
        logger.info(f"Downloaded {len(downloaded['attachments'])} attachments")
    
    return downloaded


def save_backup_data(output_dir: Path, boards: List[Dict], messages: List[Dict], 
                    downloaded_media: Dict):
    """Save all backup data."""
    json_dir = output_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    
    # Save boards
    (json_dir / "boards.json").write_text(
        json.dumps(boards, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Convert messages.jsonl to messages.json (pretty formatted)
    # Note: messages are already saved in .jsonl format during download
    messages_jsonl = json_dir / "messages.jsonl"
    if messages_jsonl.exists():
        logger.info("Converting messages.jsonl to messages.json...")
        (json_dir / "messages.json").write_text(
            json.dumps(messages, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        logger.info(f"Saved {len(messages)} messages to messages.json")
    else:
        # Fallback if .jsonl doesn't exist (shouldn't happen)
        (json_dir / "messages.json").write_text(
            json.dumps(messages, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    # Save media mapping
    (json_dir / "media_mapping.json").write_text(
        json.dumps(downloaded_media, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Generate HTML pages for each thread
    logger.info("Generating HTML pages for threads...")
    threads_dir = output_dir / "threads"
    threads_dir.mkdir(parents=True, exist_ok=True)
    
    threads = group_messages_by_thread(messages)
    thread_files = []
    used_filenames = set()  # Track filenames to prevent collisions
    
    for i, (thread_url, thread_messages) in enumerate(threads.items(), 1):
        filename, html = generate_thread_html(thread_url, thread_messages, downloaded_media, used_filenames)
        thread_path = threads_dir / filename
        thread_path.write_text(html, encoding="utf-8")
        
        # Store for index
        first_msg = thread_messages[0]
        thread_files.append({
            "filename": filename,
            "subject": first_msg.get("subject", "Untitled"),
            "author": first_msg.get("author", "Unknown"),
            "replies": len(thread_messages) - 1,
            "url": thread_url,
            "board_name": first_msg.get("board", "Other")  # Add board info
        })
        
        if i % 10 == 0:
            logger.info(f"  Generated {i}/{len(threads)} thread pages")
    
    logger.info(f"Generated {len(threads)} thread HTML pages in {threads_dir}")
    logger.info(f"Actual files created: {len(list(threads_dir.glob('*.html')))}")
    
    # Generate main index
    logger.info("Generating main index...")
    index_html = generate_index_html(boards, thread_files, len(messages), downloaded_media)
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")
    
    logger.info(f"Saved backup data to {json_dir}")
    logger.info(f"Generated {len(thread_files)} thread pages in {threads_dir}")


def main():
    """Main execution function."""
    args = parse_args()
    
    # Set up output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"backup_{timestamp}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir.resolve()}")
    
    # Set up authenticated session
    session = setup_session(args)
    
    # Discover boards
    boards = discover_boards(session)
    
    if not boards:
        logger.error("No boards discovered. Check authentication and site access.")
        return
    
    # Initialize messages file for streaming
    json_dir = output_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    messages_file = json_dir / "messages.jsonl"
    if messages_file.exists():
        messages_file.unlink()
    
    # Track all message links globally to avoid duplicates
    all_message_links = set()
    total_downloaded = 0
    
    # Process each board: crawl AND download immediately
    for i, board in enumerate(boards, 1):
        logger.info(f"[{i}/{len(boards)}] Processing board: {board['title']}")
        
        # Crawl board to get message links
        message_links = crawl_board_messages(session, board, max_pages=args.max_pages)
        logger.info(f"  Found {len(message_links)} message links in board")
        
        # Filter out already-downloaded messages
        new_links = message_links - all_message_links
        logger.info(f"  New messages to download: {len(new_links)}")
        
        if new_links:
            # Download messages immediately and append to file
            for j, url in enumerate(sorted(new_links), 1):
                if j == 1 or j % 10 == 0 or j == len(new_links):
                    logger.info(f"    [{j}/{len(new_links)}] Downloading: {url}")
                
                soup = fetch_page(session, url)
                if not soup:
                    continue
                
                message = extract_message_content(soup, url)
                
                # Write message immediately to disk (streaming)
                with open(messages_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(message, ensure_ascii=False) + "\n")
                
                total_downloaded += 1
                all_message_links.add(url)
        
        logger.info(f"  Total unique messages downloaded so far: {total_downloaded}")
    
    if not all_message_links:
        logger.warning("No messages found. Check site access and permissions.")
        return
    
    # Read all messages back from disk for media download
    logger.info(f"\nReading {total_downloaded} messages from disk for media processing...")
    messages = []
    if messages_file.exists():
        with open(messages_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
    
    # Download media
    downloaded_media = download_media(session, messages, output_dir, args)
    
    # Save all data
    save_backup_data(output_dir, boards, messages, downloaded_media)
    
    # Save error log if any errors occurred
    if error_log_entries:
        error_log_path = output_dir / "errors.log"
        error_log_path.write_text("\n".join(error_log_entries), encoding="utf-8")
        logger.warning(f"{len(error_log_entries)} errors logged to {error_log_path}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Backup complete!")
    logger.info(f"Output directory: {output_dir.resolve()}")
    logger.info(f"Total boards: {len(boards)}")
    logger.info(f"Total messages: {len(messages)}")
    logger.info(f"Images downloaded: {len(downloaded_media.get('images', {}))}")
    logger.info(f"Attachments downloaded: {len(downloaded_media.get('attachments', {}))}")
    logger.info(f"Open {output_dir.resolve()}/index.html to view the backup")
    logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    main()

# Made with Bob
