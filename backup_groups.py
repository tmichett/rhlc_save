#!/usr/bin/env python3
"""
backup_groups.py - Backup Red Hat Learning Community Group Hubs

This script backs up discussion groups (group hubs) from learn.redhat.com by:
1. Authenticating to learn.redhat.com using browser login or cookies
2. Discovering all group hubs from the group hub page
3. Crawling each group's discussions and content
4. Downloading all messages, images, and attachments
5. Creating a complete offline archive with threaded HTML pages

Group hubs are separate from the main community boards and include course-specific
discussion groups like RH124, RH134, etc.

Usage:
    uv run python backup_groups.py --auto
    uv run python backup_groups.py --cookies cookies.txt
    uv run python backup_groups.py --auto --groups "RH124" "RH134"

Requirements:
    - Valid learn.redhat.com account
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
from urllib.parse import urljoin, urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

# Import HTML generation functions
from html_generator import (
    group_messages_by_thread_for_groups,
    generate_thread_html,
    generate_index_html
)

# Configuration
BASE_URL = "https://learn.redhat.com"
GROUP_HUB_URL = f"{BASE_URL}/t5/grouphubs/page"
HLJS_JS_URL = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"
HLJS_CSS_URL = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css"

# Rate limiting
REQUEST_DELAY = 0.5  # seconds between requests
MAX_RETRIES = 3
BROWSER_WAIT_TIME = 1000  # milliseconds to wait for dynamic content
RATE_LIMIT_DELAY = 5  # seconds to wait when rate limited (429 error)

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
        prog="backup_groups.py",
        description="Backup Red Hat Learning Community Group Hubs from learn.redhat.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python backup_groups.py --auto
  python backup_groups.py --cookies cookies.txt
  python backup_groups.py --auto --groups "RH124" "RH134"
  python backup_groups.py --auto --output ./group-backup

Authentication:
  --auto              : Use Playwright to log in and save cookies automatically
  --cookies FILE      : Use exported cookies from browser
  --save-cookies      : Save session cookies for future use

Content Selection:
  --groups NAME [NAME...] : Backup specific groups only (e.g., "RH124" "RH134")
  --max-pages N       : Limit total pages to crawl per group (for testing)
  --max-messages N    : Limit total messages to download (for testing)

Output Options:
  --output DIR        : Output directory (default: groups_backup_YYYYMMDD_HHMMSS)
  --skip-images       : Skip downloading images
  --skip-attachments  : Skip downloading attachments
  --fast              : Use faster crawling (reduced delays)
        """,
    )
    parser.add_argument("--output", default=None, metavar="DIR",
                       help="Output directory (default: groups_backup_YYYYMMDD_HHMMSS)")
    parser.add_argument("--cookies", default=None, metavar="FILE",
                       help="Path to cookies.txt file")
    parser.add_argument("--auto", action="store_true",
                       help="Use Playwright to log in automatically")
    parser.add_argument("--save-cookies", action="store_true",
                       help="Save cookies after authentication")
    parser.add_argument("--groups", nargs="+", metavar="NAME",
                       help="Backup specific groups only (e.g., RH124 RH134)")
    parser.add_argument("--max-pages", type=int, default=None, metavar="N",
                       help="Max pages to crawl per group (for testing)")
    parser.add_argument("--max-messages", type=int, default=None, metavar="N",
                       help="Max messages to download total (for testing)")
    parser.add_argument("--skip-images", action="store_true",
                       help="Skip downloading images")
    parser.add_argument("--skip-attachments", action="store_true",
                       help="Skip downloading attachments")
    parser.add_argument("--fast", action="store_true",
                       help="Use faster crawling with reduced delays")
    
    return parser.parse_args()


def playwright_login(session: requests.Session, save_cookies_path: Optional[str] = None) -> bool:
    """Use Playwright to log in and capture cookies."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: uv pip install playwright && uv run playwright install chromium")
        return False
    
    logger.info("Opening browser for login...")
    logger.info("Please log in to learn.redhat.com in the browser window")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            # Navigate to the site
            page.goto(BASE_URL, timeout=60000)
            
            logger.info("Waiting for you to log in...")
            logger.info("Press Enter in this terminal once you're logged in")
            input()
            
            # Get cookies from browser
            cookies = context.cookies()
            browser.close()
            
            # Add cookies to session
            for cookie in cookies:
                name = cookie.get("name")
                value = cookie.get("value")
                if name and value:
                    session.cookies.set(
                        name,
                        value,
                        domain=cookie.get("domain", "learn.redhat.com"),
                        path=cookie.get("path", "/")
                    )
            
            # Save cookies if requested
            if save_cookies_path:
                save_cookies_file(save_cookies_path, session)
                logger.info(f"Cookies saved to {save_cookies_path}")
            
            logger.info("Authentication successful")
            return True
            
    except Exception as e:
        logger.error(f"Browser login failed: {e}")
        return False


def save_cookies_file(filepath: str, session: requests.Session) -> bool:
    """Save session cookies to Netscape format file."""
    try:
        jar = http.cookiejar.MozillaCookieJar(filepath)
        for cookie in session.cookies:
            jar.set_cookie(cookie)
        jar.save(ignore_discard=True, ignore_expires=True)
        return True
    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")
        return False


def load_cookies_file(filepath: str, session: requests.Session) -> bool:
    """Load cookies from Netscape format file."""
    try:
        jar = http.cookiejar.MozillaCookieJar(filepath)
        jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(jar)
        logger.info(f"Loaded {len(jar)} cookies from {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to load cookies: {e}")
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
            elif response.status_code == 429:
                # Rate limited - wait longer
                wait_time = RATE_LIMIT_DELAY * (attempt + 1)
                logger.warning(f"Rate limited (429), waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                if attempt < MAX_RETRIES - 1:
                    continue
                return None
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


def discover_group_hubs(session: requests.Session, filter_groups: Optional[List[str]] = None) -> List[Dict]:
    """Discover all group hubs using browser automation for JavaScript pagination."""
    logger.info("Discovering group hubs (using browser for pagination)...")
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright required for group discovery. Run: uv pip install playwright && uv run playwright install chromium")
        return []
    
    group_links = set()
    
    try:
        with sync_playwright() as p:
            # Launch browser and inject cookies
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            
            # Inject session cookies
            cookies_list = []
            for cookie in session.cookies:
                domain = cookie.domain if cookie.domain else "learn.redhat.com"
                if domain.startswith("."):
                    domain = domain[1:]
                
                cookie_dict = {
                    "name": cookie.name,
                    "value": cookie.value,
                    "url": f"https://{domain}{cookie.path if cookie.path else '/'}",
                }
                cookies_list.append(cookie_dict)
            
            if cookies_list:
                context.add_cookies(cookies_list)
            
            page = context.new_page()
            page.goto(GROUP_HUB_URL, timeout=60000)
            page.wait_for_timeout(2000)  # Wait for initial load
            
            page_num = 1
            consecutive_empty = 0
            
            while True:
                logger.info(f"  Processing page {page_num}...")
                
                # Wait for content to load
                page.wait_for_timeout(1000)
                
                # Extract group links from current page
                html_content = page.content()
                soup = BeautifulSoup(html_content, "lxml")
                
                page_group_links = set()
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if href and isinstance(href, str) and "/gh-p/" in href:
                        full_url = urljoin(BASE_URL, href)
                        page_group_links.add(full_url)
                
                # Check for new groups
                new_groups = page_group_links - group_links
                if not new_groups:
                    consecutive_empty += 1
                    logger.info(f"  No new groups on page {page_num}")
                    
                    if consecutive_empty >= 2:
                        logger.info(f"  No new groups for 2 consecutive pages, stopping")
                        break
                else:
                    consecutive_empty = 0
                    group_links.update(new_groups)
                    logger.info(f"  Found {len(new_groups)} new groups ({len(group_links)} total)")
                
                # Try to click "Next" button
                try:
                    # Look for Next link/button
                    next_button = page.locator("a:has-text('Next')").first
                    if next_button.is_visible(timeout=1000):
                        next_button.click()
                        page.wait_for_timeout(2000)  # Wait for new content
                        page_num += 1
                    else:
                        logger.info(f"  No 'Next' button found, stopping")
                        break
                except Exception as e:
                    logger.info(f"  Could not find/click Next button: {e}")
                    break
                
                # Safety limit
                if page_num > 20:
                    logger.warning(f"  Reached safety limit of 20 pages")
                    break
            
            browser.close()
            logger.info(f"Found {len(group_links)} total groups across {page_num} pages")
            
    except Exception as e:
        logger.error(f"Browser automation failed: {e}")
        logger.info("Falling back to single page fetch...")
        # Fallback to simple fetch
        soup = fetch_page(session, GROUP_HUB_URL)
        if soup:
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if href and isinstance(href, str) and "/gh-p/" in href:
                    full_url = urljoin(BASE_URL, href)
                    group_links.add(full_url)
    
    # Now visit each discovered group to get details
    groups = []
    for i, group_url in enumerate(sorted(group_links), 1):
        logger.info(f"  [{i}/{len(group_links)}] Checking {group_url}")
        
        soup = fetch_page(session, group_url)
        if not soup:
            continue
        
        # Extract group info
        title_elem = soup.find("h1", class_=re.compile("lia-page-title"))
        if not title_elem:
            title_elem = soup.find("h1")
        
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Group"
        group_id = group_url.split("/")[-1] if "/" in group_url else "unknown"
        
        # Filter by group names if specified
        if filter_groups:
            # Check if any filter matches the title or ID
            if not any(filter_name.lower() in title.lower() or filter_name.lower() in group_id.lower() 
                      for filter_name in filter_groups):
                logger.info(f"    Skipping {title} (not in filter list)")
                continue
        
        groups.append({
            "url": group_url,
            "title": title,
            "id": group_id
        })
        
        logger.info(f"    Added: {title}")
    
    logger.info(f"Discovered {len(groups)} groups to backup")
    return groups


def is_group_hub_url(url: str, group_id: str) -> bool:
    """Check if a URL belongs to a group hub (not a regular board)."""
    # Group hub URLs have format: /t5/GROUP-ID-Name/thread-title/td-p/ID
    # Regular board URLs have format: /t5/Board-Name/thread-title/td-p/ID
    # Group IDs typically contain course codes like RH124, AD141, etc.
    
    # Extract the board/group part from URL
    match = re.search(r'/t5/([^/]+)/', url)
    if not match:
        return False
    
    url_group = match.group(1)
    
    # Check if URL contains the group ID we're backing up
    # Group IDs are like "RH124-Red-Hat-System" or "AD141-Python-Programming"
    if group_id.lower() in url_group.lower():
        return True
    
    # Additional check: Group hub URLs typically have course codes (RH###, AD###, etc.)
    # Regular boards don't (like "Platform-Linux", "General-Discussion")
    if re.search(r'(RH|AD|DO|EX|CL)\d{3}', url_group, re.IGNORECASE):
        return True
    
    return False


def extract_message_links(soup: BeautifulSoup, group_id: str = "") -> Set[str]:
    """Extract message/thread links from a page, filtering to group hub content only."""
    links = set()
    
    # Look for message links
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        
        # Match message URLs like /t5/group/thread/m-p/message-id or /td-p/
        if href and isinstance(href, str) and ("/m-p/" in href or "/td-p/" in href):
            full_url = urljoin(BASE_URL, href)
            
            # Clean URL - remove ALL variations
            # 1. Remove anchors (#M240, etc.)
            if "#" in full_url:
                full_url = full_url.split("#")[0]
            
            # 2. Remove query parameters (?highlight=true, etc.)
            if "?" in full_url:
                full_url = full_url.split("?")[0]
            
            # 3. Remove /jump-to/first-unread-message suffix
            full_url = full_url.replace("/jump-to/first-unread-message", "")
            
            # 4. Remove /highlight/true suffix
            full_url = full_url.replace("/highlight/true", "")
            
            # 5. Remove /page/N - these are pagination URLs, not message URLs
            if "/page/" in full_url:
                continue
            
            # Filter: Only include URLs that belong to group hubs
            if group_id and not is_group_hub_url(full_url, group_id):
                continue
                
            links.add(full_url)
    
    return links


def crawl_group_messages(session: requests.Session, group: Dict, max_pages: Optional[int] = None) -> Set[str]:
    """Crawl all message links from a group, including replies from thread pages."""
    logger.info(f"Crawling group: {group['title']}")
    
    all_message_links = set()
    thread_urls = set()
    page_num = 0
    group_url = group["url"]
    consecutive_empty = 0
    
    # Phase 1: Crawl group listing pages for thread URLs
    logger.info(f"  Phase 1: Crawling group listing pages...")
    while True:
        if max_pages and page_num >= max_pages:
            logger.info(f"  Reached max pages limit: {max_pages}")
            break
        
        # Build pagination URL
        if page_num == 0:
            page_url = group_url
        else:
            page_url = f"{group_url}/page/{page_num}"
        
        logger.info(f"  Page {page_num + 1}: {page_url}")
        soup = fetch_page(session, page_url)
        
        if not soup:
            logger.warning(f"  Failed to fetch page {page_num + 1}")
            break
        
        # Extract message links (filter to this group only)
        message_links = extract_message_links(soup, group.get("id", ""))
        
        if not message_links:
            consecutive_empty += 1
            logger.info(f"  No messages found on page {page_num + 1}")
            
            if consecutive_empty >= 3:
                logger.info(f"  No messages found for 3 consecutive pages, stopping")
                break
        else:
            consecutive_empty = 0
            new_links = message_links - all_message_links
            all_message_links.update(new_links)
            # Track thread URLs for phase 2
            for link in new_links:
                if "/td-p/" in link:
                    thread_urls.add(link)
            logger.info(f"  Found {len(new_links)} new messages ({len(all_message_links)} total)")
        
        # Check for next page
        next_link = soup.find("a", class_=re.compile("lia-link-navigation.*next"))
        if not next_link:
            logger.info(f"  No more pages found")
            break
        
        page_num += 1
    
    logger.info(f"  Phase 1 complete: Found {len(thread_urls)} threads")
    
    # Phase 2: Crawl each thread page for reply URLs (with pagination)
    # Note: Reply links are often loaded via JavaScript, so we use Playwright
    if thread_urls:
        logger.info(f"  Phase 2: Crawling thread pages for replies (using browser for JS rendering)...")
        reply_count = 0
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                
                # Transfer cookies from requests session to browser
                cookies_to_add = []
                for cookie in session.cookies:
                    cookie_dict = {
                        'name': cookie.name,
                        'value': cookie.value,
                        'url': BASE_URL,  # Use URL instead of domain/path
                    }
                    cookies_to_add.append(cookie_dict)
                if cookies_to_add:
                    context.add_cookies(cookies_to_add)
                
                page = context.new_page()
                
                for i, thread_url in enumerate(thread_urls, 1):
                    if i % 10 == 0:
                        logger.info(f"    Progress: {i}/{len(thread_urls)} threads checked, {reply_count} replies found")
                    
                    # Crawl all pages of this thread
                    page_num = 0
                    consecutive_empty = 0
                    while True:
                        # Build pagination URL for thread
                        if page_num == 0:
                            page_url = thread_url
                        else:
                            page_url = f"{thread_url}/page/{page_num}"
                        
                        try:
                            # Use Playwright to render JavaScript
                            page.goto(page_url, wait_until="networkidle", timeout=30000)
                            time.sleep(REQUEST_DELAY)  # Respect rate limiting
                            
                            # Get rendered HTML
                            html = page.content()
                            soup = BeautifulSoup(html, "lxml")
                            
                            reply_links = extract_message_links(soup, group.get("id", ""))
                            new_replies = reply_links - all_message_links
                            
                            if not new_replies:
                                consecutive_empty += 1
                                if consecutive_empty >= 2:  # Stop after 2 empty pages
                                    break
                            else:
                                consecutive_empty = 0
                                all_message_links.update(new_replies)
                                reply_count += len(new_replies)
                            
                            # Check for next page
                            next_link = soup.find("a", class_=re.compile("lia-link-navigation.*next"))
                            if not next_link:
                                break
                            
                            page_num += 1
                        except Exception as e:
                            logger.warning(f"Error crawling {page_url}: {e}")
                            break
                
                browser.close()
        
        except ImportError:
            logger.warning("Playwright not available, skipping JavaScript-rendered reply links")
            logger.warning("Install with: uv pip install playwright && uv run playwright install chromium")
        
        logger.info(f"  Phase 2 complete: Found {reply_count} additional replies")
    
    logger.info(f"Crawled {len(all_message_links)} total messages from {group['title']}")
    return all_message_links


def download_message(session: requests.Session, url: str, output_dir: Path) -> Optional[Dict]:
    """Download and parse a single message."""
    soup = fetch_page(session, url)
    if not soup:
        return None
    
    # Extract message ID from URL
    message_id = url.split("/")[-1] if "/" in url else "unknown"
    
    # Extract message data (similar to rhlc-backup.py)
    message_data = {
        "url": url,
        "id": message_id,
        "title": "",
        "author": "",
        "date": "",
        "content": "",
        "images": [],
        "attachments": []
    }
    
    # Find the specific message div by ID
    # Khoros uses div with id like "message_48389" or data-messageid="48389"
    message_div = None
    
    # Try finding by ID attribute
    message_div = soup.find("div", id=f"message_{message_id}")
    if not message_div:
        # Try finding by data-messageid attribute
        message_div = soup.find("div", attrs={"data-messageid": message_id})
    if not message_div:
        # Fallback: find div containing a link to this message ID
        for div in soup.find_all("div", class_=re.compile("lia-message")):
            link = div.find("a", href=re.compile(f"/{message_id}"))
            if link:
                message_div = div
                break
    
    # If we still can't find the specific message, use the first one (thread starter)
    if not message_div:
        logger.warning(f"Could not find specific message {message_id}, using first message on page")
        message_div = soup
    
    # Extract title from page (thread title)
    title_elem = message_div.find("h1", class_=re.compile("lia-message-subject"))
    if not title_elem:
        # Try finding in the whole page if not in message div
        title_elem = soup.find("h1", class_=re.compile("lia-message-subject"))
    if title_elem:
        message_data["title"] = title_elem.get_text(strip=True)
    
    # Fallback: Extract title from URL if not found in page
    # URL format: /t5/GROUP-NAME/TITLE/td-p/ID or /t5/GROUP-NAME/TITLE/m-p/ID
    if not message_data["title"]:
        try:
            # Split URL and find the title part (between group name and /td-p/ or /m-p/)
            url_parts = url.split("/")
            # Find index of td-p or m-p
            for i, part in enumerate(url_parts):
                if part in ("td-p", "m-p") and i > 0:
                    # Title is the part before td-p/m-p
                    title_slug = url_parts[i - 1]
                    # Convert URL slug to readable title (replace hyphens with spaces)
                    message_data["title"] = title_slug.replace("-", " ").title()
                    break
        except Exception as e:
            logger.debug(f"Could not extract title from URL: {e}")
    
    # Extract author from the specific message div
    author_elem = message_div.find("a", class_=re.compile("lia-user-name-link"))
    if author_elem:
        message_data["author"] = author_elem.get_text(strip=True)
    
    # Extract date from the specific message div
    date_elem = message_div.find("span", class_=re.compile("DateTime"))
    if date_elem:
        message_data["date"] = date_elem.get_text(strip=True)
    
    # Extract content from the specific message div
    content_elem = message_div.find("div", class_=re.compile("lia-message-body-content"))
    if content_elem:
        message_data["content"] = str(content_elem)
        
        # Extract images
        for img in content_elem.find_all("img"):
            img_src = img.get("src")
            if img_src and isinstance(img_src, str) and img_src.startswith(("http", "/")):
                full_url = urljoin(BASE_URL, img_src)
                if "learn.redhat.com" in full_url:
                    message_data["images"].append(full_url)
        
        # Extract attachments
        for link in content_elem.find_all("a", href=True):
            href = link.get("href")
            if href and isinstance(href, str) and "/attachment/" in href:
                full_url = urljoin(BASE_URL, href)
                if "learn.redhat.com" in full_url:
                    message_data["attachments"].append({
                        "url": full_url,
                        "name": link.get_text(strip=True)
                    })
    
    return message_data


def main():
    """Main execution function."""
    args = parse_args()
    
    # Adjust delays for fast mode
    global REQUEST_DELAY, BROWSER_WAIT_TIME
    if args.fast:
        REQUEST_DELAY = 0.2
        BROWSER_WAIT_TIME = 500
        logger.info("Fast mode enabled (reduced delays)")
    
    # Set up output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"groups_backup_{timestamp}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")
    
    # Set up session
    session = setup_session(args)
    
    # Discover groups
    groups = discover_group_hubs(session, args.groups)
    
    if not groups:
        logger.error("No groups found to backup")
        return
    
    # Save group list
    groups_file = output_dir / "groups.json"
    with open(groups_file, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved group list to {groups_file}")
    
    # Crawl each group
    all_messages = []
    total_messages = 0
    
    for i, group in enumerate(groups, 1):
        logger.info(f"\n[{i}/{len(groups)}] Processing group: {group['title']}")
        
        # Crawl messages
        message_links = crawl_group_messages(session, group, args.max_pages)
        
        # Download messages
        group_messages = []
        for j, msg_url in enumerate(sorted(message_links), 1):
            if args.max_messages and total_messages >= args.max_messages:
                logger.info(f"Reached max messages limit: {args.max_messages}")
                break
            
            logger.info(f"  [{j}/{len(message_links)}] Downloading {msg_url}")
            message_data = download_message(session, msg_url, output_dir)
            
            if message_data:
                message_data["group_id"] = group["id"]
                message_data["group_title"] = group["title"]
                group_messages.append(message_data)
                total_messages += 1
        
        all_messages.extend(group_messages)
        
        # Save group messages
        group_file = output_dir / f"group_{group['id']}.json"
        with open(group_file, "w", encoding="utf-8") as f:
            json.dump(group_messages, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(group_messages)} messages to {group_file}")
    
    # Save all messages
    all_messages_file = output_dir / "all_messages.json"
    with open(all_messages_file, "w", encoding="utf-8") as f:
        json.dump(all_messages, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved {len(all_messages)} total messages to {all_messages_file}")
    
    # Generate HTML (using existing html_generator functions)
    logger.info("\nGenerating HTML pages...")
    html_dir = output_dir / "html"
    html_dir.mkdir(exist_ok=True)
    
    # Group messages by thread and generate HTML
    threads = group_messages_by_thread_for_groups(all_messages)
    logger.info(f"Organized into {len(threads)} threads")
    
    # Track used filenames and prepare thread files list
    used_filenames = set()
    thread_files = []
    downloaded_media = {"images": {}, "attachments": {}}  # Empty for now, can be enhanced later
    
    # Generate thread pages
    for thread_url, messages in threads.items():
        filename, html_content = generate_thread_html(
            thread_url,
            messages,
            downloaded_media,
            used_filenames,
            None,  # attachments_dir - not implemented yet
            "groups_index.html"  # index_link - files are in same directory
        )
        thread_file = html_dir / filename
        with open(thread_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Track thread info for index - use "subject" key for compatibility with html_generator
        first_msg = messages[0] if messages else {}
        thread_files.append({
            "filename": filename,
            "subject": first_msg.get("title", "Untitled"),  # html_generator expects "subject"
            "title": first_msg.get("title", "Untitled"),    # keep "title" for compatibility
            "board_name": first_msg.get("group_title", "Unknown Group"),
            "author": first_msg.get("author", "Unknown"),
            "replies": len(messages) - 1,
            "message_count": len(messages),
            "url": thread_url
        })
    
    # Generate index page
    index_file = html_dir / "groups_index.html"
    index_content = generate_index_html(
        groups,  # boards parameter
        thread_files,  # thread_files parameter
        len(all_messages),  # messages_count parameter
        downloaded_media,  # downloaded_media parameter
        thread_path_prefix=""  # files are in same directory as index
    )
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(index_content)
    
    # Create top-level index.html for easy access
    top_index_file = output_dir / "index.html"
    top_index_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RHLC Group Backup</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
               margin: 0; padding: 0; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 50px auto; padding: 40px; background: white;
                     border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #cc0000; margin-top: 0; }}
        .subtitle {{ color: #666; margin-bottom: 30px; }}
        .info {{ background: #f8f8f8; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        .info-item {{ margin: 10px 0; }}
        .info-label {{ font-weight: bold; color: #333; }}
        .button {{ display: inline-block; padding: 15px 30px; background: #cc0000; color: white;
                  text-decoration: none; border-radius: 5px; font-weight: 500; margin-top: 20px; }}
        .button:hover {{ background: #aa0000; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;
                  text-align: center; color: #999; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Red Hat Learning Community</h1>
        <div class="subtitle">Group Hub Backup</div>
        
        <div class="info">
            <div class="info-item">
                <span class="info-label">Groups Backed Up:</span> {len(groups)}
            </div>
            <div class="info-item">
                <span class="info-label">Total Messages:</span> {len(all_messages)}
            </div>
            <div class="info-item">
                <span class="info-label">Total Threads:</span> {len(threads)}
            </div>
            <div class="info-item">
                <span class="info-label">Backup Date:</span> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </div>
        </div>
        
        <a href="html/groups_index.html" class="button">📚 Browse Backup Content</a>
        
        <div class="footer">
            <p>This is an offline backup of Red Hat Learning Community group discussions.</p>
            <p>All content is stored locally for archival purposes.</p>
        </div>
    </div>
</body>
</html>
"""
    with open(top_index_file, "w", encoding="utf-8") as f:
        f.write(top_index_content)
    
    logger.info(f"HTML pages generated in {html_dir}")
    logger.info(f"\nBackup complete! Open {top_index_file} in your browser to view.")
    
    # Print summary
    print("\n" + "="*60)
    print("BACKUP SUMMARY")
    print("="*60)
    print(f"Groups backed up: {len(groups)}")
    print(f"Total messages: {len(all_messages)}")
    print(f"Total threads: {len(threads)}")
    print(f"Output directory: {output_dir}")
    print(f"HTML index: {index_file}")
    
    if error_log_entries:
        print(f"\nErrors encountered: {len(error_log_entries)}")
        error_file = output_dir / "errors.log"
        with open(error_file, "w") as f:
            f.write("\n".join(error_log_entries))
        print(f"Error log saved to: {error_file}")
    
    print("="*60)


if __name__ == "__main__":
    main()

# Made with Bob
