#!/usr/bin/env python3
"""
Crawl missing replies from group backup threads.

This script visits each thread page and extracts reply URLs that weren't
captured during the initial group crawl.
"""

import json
import logging
import sys
import time
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Configuration
BASE_URL = "https://learn.redhat.com"
REQUEST_DELAY = 1.0  # seconds between requests
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 5  # seconds to wait when rate limited

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def setup_session_with_browser() -> requests.Session:
    """Set up authenticated session using Playwright browser."""
    logger.info("Opening browser for authentication...")
    logger.info("Please log in to learn.redhat.com in the browser window")
    
    session = requests.Session()
    
    # Set up headers to mimic browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Navigate to the site
        page.goto(BASE_URL, timeout=60000)
        
        # Wait for user to log in
        logger.info("Waiting for you to log in...")
        logger.info("Press ENTER in this terminal once you're logged in")
        input()
        
        # Extract cookies
        cookies = context.cookies()
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
        
        browser.close()
    
    logger.info("✓ Authentication successful")
    return session


def fetch_page(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
    """Fetch and parse a page with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY)
            response = session.get(url, timeout=30)
            
            if response.status_code == 200:
                return BeautifulSoup(response.text, "lxml")
            elif response.status_code == 429:
                wait_time = RATE_LIMIT_DELAY * (attempt + 1)
                logger.warning(f"Rate limited (429), waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                logger.warning(f"Status {response.status_code} for {url}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return None
    
    return None


def extract_reply_links(soup: BeautifulSoup) -> Set[str]:
    """Extract all reply message links from a thread page."""
    links = set()
    
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        # Look for reply URLs (m-p)
        if href and isinstance(href, str) and "/m-p/" in href:
            full_url = urljoin(BASE_URL, href)
            # Remove anchors and query params
            full_url = full_url.split("#")[0].split("?")[0]
            links.add(full_url)
    
    return links


def download_message(session: requests.Session, url: str) -> Optional[Dict]:
    """Download and parse a single message."""
    soup = fetch_page(session, url)
    if not soup:
        return None
    
    message_data = {
        "url": url,
        "id": url.split("/")[-1] if "/" in url else "unknown",
        "title": "",
        "author": "",
        "date": "",
        "content": "",
        "images": [],
        "attachments": []
    }
    
    # Extract title from URL
    try:
        url_parts = url.split("/")
        for i, part in enumerate(url_parts):
            if part in ("td-p", "m-p") and i > 0:
                title_slug = url_parts[i - 1]
                message_data["title"] = title_slug.replace("-", " ").title()
                break
    except Exception:
        pass
    
    # Extract author
    author_elem = soup.find("a", class_=re.compile("lia-user-name-link"))
    if author_elem:
        message_data["author"] = author_elem.get_text(strip=True)
    
    # Extract date
    date_elem = soup.find("span", class_=re.compile("DateTime"))
    if date_elem:
        message_data["date"] = date_elem.get_text(strip=True)
    
    # Extract content
    content_elem = soup.find("div", class_=re.compile("lia-message-body-content"))
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
    
    # Extract group info from URL
    try:
        # URL format: /t5/GROUP-NAME/thread-title/m-p/ID
        match = re.search(r'/t5/([^/]+)/', url)
        if match:
            group_slug = match.group(1)
            message_data["group_id"] = group_slug
            # Try to find group title from existing data
    except Exception:
        pass
    
    return message_data


def main():
    if len(sys.argv) != 2:
        print("Usage: python crawl_missing_replies.py <backup_directory>")
        print("\nExample:")
        print("  python crawl_missing_replies.py groups_backup_20260315_215501")
        sys.exit(1)
    
    backup_dir = Path(sys.argv[1])
    
    if not backup_dir.exists():
        logger.error(f"Backup directory not found: {backup_dir}")
        sys.exit(1)
    
    # Load existing messages
    all_messages_file = backup_dir / "all_messages.json"
    if not all_messages_file.exists():
        logger.error(f"Messages file not found: {all_messages_file}")
        sys.exit(1)
    
    logger.info(f"Loading existing messages from {all_messages_file}")
    with open(all_messages_file, "r", encoding="utf-8") as f:
        existing_messages = json.load(f)
    
    logger.info(f"Found {len(existing_messages)} existing messages")
    
    # Get existing message URLs
    existing_urls = {msg["url"].split("#")[0].split("?")[0] for msg in existing_messages}
    
    # Find all thread URLs (td-p) and clean them
    thread_urls = set()
    for msg in existing_messages:
        if "/td-p/" in msg["url"]:
            # Clean URL - remove anchors and query params
            clean_url = msg["url"].split("#")[0].split("?")[0]
            # Remove /jump-to/first-unread-message suffix if present
            clean_url = clean_url.replace("/jump-to/first-unread-message", "")
            thread_urls.add(clean_url)
    logger.info(f"Found {len(thread_urls)} thread URLs to check for replies")
    
    # Set up session
    logger.info("\nSetting up authenticated session...")
    session = setup_session_with_browser()
    
    # Crawl replies
    all_reply_urls = set()
    new_reply_urls = set()
    
    logger.info(f"\nCrawling {len(thread_urls)} threads for reply links...")
    for i, thread_url in enumerate(thread_urls, 1):
        if i % 10 == 0:
            logger.info(f"  Progress: {i}/{len(thread_urls)} threads checked")
        
        soup = fetch_page(session, thread_url)
        if soup:
            reply_links = extract_reply_links(soup)
            all_reply_urls.update(reply_links)
            new_links = reply_links - existing_urls
            new_reply_urls.update(new_links)
    
    logger.info(f"\nFound {len(all_reply_urls)} total reply URLs")
    logger.info(f"Found {len(new_reply_urls)} NEW reply URLs to download")
    
    if not new_reply_urls:
        logger.info("No new replies to download!")
        return
    
    # Download new replies
    logger.info(f"\nDownloading {len(new_reply_urls)} new replies...")
    new_messages = []
    
    for i, reply_url in enumerate(new_reply_urls, 1):
        if i % 10 == 0:
            logger.info(f"  Downloaded {i}/{len(new_reply_urls)} replies")
        
        message_data = download_message(session, reply_url)
        if message_data:
            # Try to match group info from thread
            for existing_msg in existing_messages:
                if existing_msg["url"] in reply_url or reply_url in existing_msg["url"]:
                    message_data["group_id"] = existing_msg.get("group_id", "")
                    message_data["group_title"] = existing_msg.get("group_title", "")
                    break
            new_messages.append(message_data)
    
    logger.info(f"\nSuccessfully downloaded {len(new_messages)} new replies")
    
    # Merge with existing messages
    all_messages = existing_messages + new_messages
    
    # Save updated messages
    logger.info(f"Saving {len(all_messages)} total messages...")
    with open(all_messages_file, "w", encoding="utf-8") as f:
        json.dump(all_messages, f, indent=2, ensure_ascii=False)
    
    logger.info("\n" + "="*60)
    logger.info("CRAWL COMPLETE")
    logger.info("="*60)
    logger.info(f"Original messages: {len(existing_messages)}")
    logger.info(f"New replies added: {len(new_messages)}")
    logger.info(f"Total messages: {len(all_messages)}")
    logger.info("="*60)
    logger.info("\nNext step: Regenerate HTML")
    logger.info(f"  uv run python regenerate_groups_html.py {backup_dir.name}")


if __name__ == "__main__":
    main()

# Made with Bob
