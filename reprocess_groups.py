#!/usr/bin/env python3
"""
reprocess_groups.py - Reprocess group backup to download missing media and regenerate HTML

This script reads the JSON files from a group backup and:
1. Downloads any missing or corrupted images
2. Downloads any missing or corrupted attachments
3. Regenerates HTML pages with proper media references

Usage:
    uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto
    uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --cookies cookies.txt
"""

import argparse
import http.cookiejar
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests

# Import HTML generation functions
from html_generator import (
    group_messages_by_thread,
    generate_thread_html,
    generate_index_html
)

# Configuration
BASE_URL = "https://learn.redhat.com"
REQUEST_DELAY = 0.5
MAX_RETRIES = 3

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Reprocess group backup to download missing media and regenerate HTML"
    )
    parser.add_argument("--backup-dir", required=True, metavar="DIR",
                       help="Path to existing group backup directory")
    parser.add_argument("--cookies", default=None, metavar="FILE",
                       help="Path to Netscape cookies file")
    parser.add_argument("--auto", action="store_true",
                       help="Use Playwright to log in automatically")
    parser.add_argument("--save-cookies", action="store_true",
                       help="Save session cookies for future use (with --auto)")
    parser.add_argument("--force", action="store_true",
                       help="Re-download all media, even if they exist")
    parser.add_argument("--skip-images", action="store_true",
                       help="Skip downloading images")
    parser.add_argument("--skip-attachments", action="store_true",
                       help="Skip downloading attachments")
    parser.add_argument("--fast", action="store_true",
                       help="Use faster processing with reduced delays")
    return parser.parse_args()


def load_cookies_file(cookie_file: str, session: requests.Session) -> bool:
    """Load cookies from Netscape format file."""
    try:
        cookie_jar = http.cookiejar.MozillaCookieJar(cookie_file)
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(cookie_jar)
        logger.info(f"Loaded {len(cookie_jar)} cookies from {cookie_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to load cookies: {e}")
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


def playwright_login(session: requests.Session, save_path: Optional[str] = None) -> bool:
    """Use Playwright to log in and transfer cookies to requests session."""
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
            
            page.goto(BASE_URL)
            
            logger.info("Waiting for login... (press Enter when logged in)")
            input()
            
            cookies = context.cookies()
            browser.close()
            
            # Transfer cookies to requests session
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
            if save_path:
                save_cookies_file(save_path, session)
                logger.info(f"Cookies saved to {save_path}")
            
            logger.info("Authentication successful")
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
        raise SystemExit(1)
    
    return session


def download_file(session: requests.Session, url: str, dest_path: Path, 
                 force: bool = False) -> bool | None:
    """Download a file with corruption detection.
    
    Returns:
        True: Successfully downloaded
        False: Failed to download
        None: Skipped (already exists and valid)
    """
    
    # Check if file already exists and is valid
    if dest_path.exists() and not force:
        file_size = dest_path.stat().st_size
        
        # Check for SAML corruption
        is_corrupted = False
        if file_size < 10000:
            try:
                with open(dest_path, 'rb') as f:
                    content = f.read(1000)
                    if b'SAMLRequest' in content or b'saml2p:AuthnRequest' in content:
                        is_corrupted = True
                        logger.warning(f"  Detected corrupted SAML redirect: {dest_path.name}")
            except Exception:
                pass
        
        if not is_corrupted and file_size > 0:
            logger.debug(f"  Skipping {dest_path.name} (already exists, {file_size} bytes)")
            return None
        elif is_corrupted:
            logger.warning(f"  Re-downloading corrupted file: {dest_path.name}")
    
    # Map content type to extension
    ext_map = {
        "application/pdf": ".pdf",
        "application/zip": ".zip",
        "application/x-zip-compressed": ".zip",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-powerpoint": ".ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "text/plain": ".txt",
        "text/csv": ".csv",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY)
            response = session.get(url, timeout=60, stream=True, allow_redirects=True)
            
            if response.status_code == 200:
                # Check content type and add extension if missing
                content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
                current_ext = dest_path.suffix.lower()
                
                if content_type in ext_map and not current_ext:
                    new_ext = ext_map[content_type]
                    dest_path = dest_path.with_suffix(new_ext)
                    logger.info(f"  Added extension {new_ext} based on Content-Type: {content_type}")
                
                # Download file
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = dest_path.stat().st_size
                logger.info(f"  Downloaded {dest_path.name} ({file_size} bytes)")
                return True
            
            elif response.status_code in (401, 403):
                logger.error(f"  Access denied for {url}")
                return False
            elif response.status_code == 404:
                logger.warning(f"  Not found: {url}")
                return False
            else:
                logger.warning(f"  Status {response.status_code} for {url}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return False
        
        except Exception as e:
            logger.error(f"  Failed to download {url}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return False
    
    return False


def process_images(session: requests.Session, messages: List[Dict], 
                   images_dir: Path, force: bool = False) -> Dict[str, str]:
    """Download all images from messages."""
    logger.info("Processing images...")
    
    # Collect all unique image URLs
    image_urls = set()
    for msg in messages:
        for img_url in msg.get("images", []):
            if isinstance(img_url, str) and "learn.redhat.com" in img_url:
                image_urls.add(img_url)
    
    logger.info(f"Found {len(image_urls)} unique images to process")
    
    # Download images
    downloaded = {}
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for i, img_url in enumerate(sorted(image_urls), 1):
        logger.info(f"[{i}/{len(image_urls)}] Processing {img_url}")
        
        # Generate filename from URL
        parsed = urlparse(img_url)
        filename = Path(parsed.path).name
        if not filename:
            import hashlib
            filename = f"image_{hashlib.md5(img_url.encode()).hexdigest()[:12]}.jpg"
        
        dest_path = images_dir / filename
        result = download_file(session, img_url, dest_path, force)
        
        if result is True:
            downloaded[img_url] = filename
            success_count += 1
        elif result is None:
            downloaded[img_url] = filename
            skip_count += 1
        else:
            fail_count += 1
    
    logger.info(f"Images: {success_count} downloaded, {skip_count} skipped, {fail_count} failed")
    return downloaded


def process_attachments(session: requests.Session, messages: List[Dict],
                       attachments_dir: Path, force: bool = False) -> Dict[str, str]:
    """Download all attachments from messages."""
    logger.info("Processing attachments...")
    
    # Collect all unique attachment URLs
    attachment_map = {}  # url -> name
    for msg in messages:
        for att in msg.get("attachments", []):
            if isinstance(att, dict):
                url = att.get("url", "")
                name = att.get("name", "attachment")
                if url and "learn.redhat.com" in url:
                    attachment_map[url] = name
    
    logger.info(f"Found {len(attachment_map)} unique attachments to process")
    
    # Download attachments
    downloaded = {}
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for i, (att_url, att_name) in enumerate(sorted(attachment_map.items()), 1):
        logger.info(f"[{i}/{len(attachment_map)}] Processing {att_name}")
        
        # Sanitize filename
        filename = att_name
        if filename.startswith("http://") or filename.startswith("https://"):
            parsed = urlparse(filename)
            filename = Path(parsed.path).name
            if not filename:
                import hashlib
                filename = f"attachment_{hashlib.md5(att_url.encode()).hexdigest()[:12]}"
        
        dest_path = attachments_dir / filename
        result = download_file(session, att_url, dest_path, force)
        
        if result is True:
            downloaded[att_url] = filename
            success_count += 1
        elif result is None:
            downloaded[att_url] = filename
            skip_count += 1
        else:
            fail_count += 1
    
    logger.info(f"Attachments: {success_count} downloaded, {skip_count} skipped, {fail_count} failed")
    return downloaded


def regenerate_html(backup_dir: Path, messages: List[Dict], groups: List[Dict],
                   downloaded_media: Dict):
    """Regenerate HTML pages with updated media references."""
    logger.info("Regenerating HTML pages...")
    
    html_dir = backup_dir / "html"
    html_dir.mkdir(exist_ok=True)
    attachments_dir = backup_dir / "attachments"
    
    # Group messages by thread
    threads = group_messages_by_thread(messages)
    logger.info(f"Organized into {len(threads)} threads")
    
    # Track used filenames and prepare thread files list
    used_filenames = set()
    thread_files = []
    
    # Generate thread pages
    for thread_url, thread_messages in threads.items():
        filename, html_content = generate_thread_html(
            thread_url,
            thread_messages,
            downloaded_media,
            used_filenames,
            attachments_dir if attachments_dir.exists() else None
        )
        thread_file = html_dir / filename
        with open(thread_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Track thread info for index - use "subject" key for compatibility with html_generator
        first_msg = thread_messages[0] if thread_messages else {}
        thread_files.append({
            "filename": filename,
            "subject": first_msg.get("title", "Untitled"),  # html_generator expects "subject"
            "title": first_msg.get("title", "Untitled"),    # keep "title" for compatibility
            "board_name": first_msg.get("group_title", "Unknown Group"),
            "author": first_msg.get("author", "Unknown"),
            "replies": len(thread_messages) - 1,
            "message_count": len(thread_messages),
            "url": thread_url
        })
    
    # Generate index page (use empty prefix since files are in same directory)
    index_file = html_dir / "groups_index.html"
    index_content = generate_index_html(
        groups,
        thread_files,
        len(messages),
        downloaded_media,
        thread_path_prefix=""
    )
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(index_content)
    
    logger.info(f"Generated {len(thread_files)} thread pages and index")
    logger.info(f"HTML index: {index_file}")


def main():
    """Main execution function."""
    args = parse_args()
    
    # Adjust delays for fast mode
    global REQUEST_DELAY
    if args.fast:
        REQUEST_DELAY = 0.2
        logger.info("Fast mode enabled (reduced delays)")
    
    # Validate backup directory
    backup_dir = Path(args.backup_dir)
    if not backup_dir.exists():
        logger.error(f"Backup directory not found: {backup_dir}")
        return
    
    # Load messages
    all_messages_file = backup_dir / "all_messages.json"
    if not all_messages_file.exists():
        logger.error(f"Messages file not found: {all_messages_file}")
        return
    
    logger.info(f"Loading messages from {all_messages_file}")
    with open(all_messages_file, "r", encoding="utf-8") as f:
        messages = json.load(f)
    logger.info(f"Loaded {len(messages)} messages")
    
    # Load groups
    groups_file = backup_dir / "groups.json"
    groups = []
    if groups_file.exists():
        with open(groups_file, "r", encoding="utf-8") as f:
            groups = json.load(f)
        logger.info(f"Loaded {len(groups)} groups")
    
    # Set up session
    session = setup_session(args)
    
    # Create directories
    images_dir = backup_dir / "images"
    attachments_dir = backup_dir / "attachments"
    images_dir.mkdir(exist_ok=True)
    attachments_dir.mkdir(exist_ok=True)
    
    # Process media
    downloaded_media = {"images": {}, "attachments": {}}
    
    if not args.skip_images:
        downloaded_media["images"] = process_images(
            session, messages, images_dir, args.force
        )
    
    if not args.skip_attachments:
        downloaded_media["attachments"] = process_attachments(
            session, messages, attachments_dir, args.force
        )
    
    # Save media mapping
    media_mapping_file = backup_dir / "media_mapping.json"
    with open(media_mapping_file, "w", encoding="utf-8") as f:
        json.dump(downloaded_media, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved media mapping to {media_mapping_file}")
    
    # Regenerate HTML
    regenerate_html(backup_dir, messages, groups, downloaded_media)
    
    # Print summary
    print("\n" + "="*60)
    print("REPROCESSING COMPLETE")
    print("="*60)
    print(f"Images: {len(downloaded_media['images'])} processed")
    print(f"Attachments: {len(downloaded_media['attachments'])} processed")
    print(f"HTML index: {backup_dir}/html/groups_index.html")
    print("="*60)


if __name__ == "__main__":
    main()

# Made with Bob
