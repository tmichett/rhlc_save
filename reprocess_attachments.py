#!/usr/bin/env python3
"""
reprocess_attachments.py - Reprocess and download attachments from existing backup JSON

This script reads the messages.json from a previous backup and downloads any missing
or incorrectly downloaded attachments. It handles:
- Authentication using existing cookies or browser login
- File extension detection from Content-Type headers
- Retry logic for failed downloads
- Preserving existing successfully downloaded files

Usage:
    uv run python reprocess_attachments.py --backup-dir backup_20240314_123456 --auto
    uv run python reprocess_attachments.py --backup-dir backup_20240314_123456 --cookies cookies.txt
"""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests

# Configuration
BASE_URL = "https://learn.redhat.com"
REQUEST_DELAY = 1.0
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
        description="Reprocess and download attachments from existing backup JSON"
    )
    parser.add_argument("--backup-dir", required=True, metavar="DIR",
                       help="Path to existing backup directory")
    parser.add_argument("--cookies", default=None, metavar="FILE",
                       help="Path to Netscape cookies file")
    parser.add_argument("--auto", action="store_true",
                       help="Use Playwright to log in automatically")
    parser.add_argument("--save-cookies", action="store_true",
                       help="Save session cookies for future use (with --auto)")
    parser.add_argument("--force", action="store_true",
                       help="Re-download all attachments, even if they exist")
    return parser.parse_args()


def load_cookies_file(cookie_file: str, session: requests.Session) -> bool:
    """Load cookies from Netscape format file."""
    import http.cookiejar
    
    try:
        cookie_jar = http.cookiejar.MozillaCookieJar(cookie_file)
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(cookie_jar)
        logger.info(f"Loaded {len(cookie_jar)} cookies from {cookie_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to load cookies: {e}")
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
                session.cookies.set(
                    cookie.get("name", ""),
                    cookie.get("value", ""),
                    domain=cookie.get("domain", ""),
                    path=cookie.get("path", "/")
                )
            
            logger.info(f"Transferred {len(cookies)} cookies to session")
            
            # Save cookies if requested
            if save_path:
                import http.cookiejar
                cookie_jar = http.cookiejar.MozillaCookieJar(save_path)
                for cookie in cookies:
                    expires = cookie.get("expires")
                    cookie_jar.set_cookie(http.cookiejar.Cookie(
                        version=0,
                        name=cookie.get("name", ""),
                        value=cookie.get("value", ""),
                        port=None,
                        port_specified=False,
                        domain=cookie.get("domain", ""),
                        domain_specified=True,
                        domain_initial_dot=cookie.get("domain", "").startswith("."),
                        path=cookie.get("path", "/"),
                        path_specified=True,
                        secure=cookie.get("secure", False),
                        expires=int(expires) if expires is not None else None,
                        discard=False,
                        comment=None,
                        comment_url=None,
                        rest={}
                    ))
                cookie_jar.save(ignore_discard=True, ignore_expires=True)
                logger.info(f"Saved cookies to {save_path}")
            
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


def download_attachment(session: requests.Session, url: str, filename: str,
                       dest_path: Path, force: bool = False) -> bool | None:
    """Download a single attachment with proper extension detection.
    
    Returns:
        True: Successfully downloaded
        False: Failed to download
        None: Skipped (already exists and valid)
    """
    
    # Sanitize filename - if it looks like a URL, extract just the filename
    if filename.startswith("http://") or filename.startswith("https://"):
        # Extract filename from URL
        from urllib.parse import urlparse
        parsed = urlparse(filename)
        filename = Path(parsed.path).name
        if not filename:
            # Fallback to hash if we can't extract a filename
            import hashlib
            filename = f"attachment_{hashlib.md5(url.encode()).hexdigest()[:12]}"
        logger.info(f"  Sanitized filename from URL to: {filename}")
    
    # Update dest_path with sanitized filename
    dest_path = dest_path.parent / filename
    
    # Check if file already exists and has content
    # Also check if it's a corrupted SAML redirect (typically 6-7KB HTML files)
    if dest_path.exists() and not force:
        file_size = dest_path.stat().st_size
        
        # Check if it's a corrupted SAML redirect page
        is_corrupted = False
        if file_size < 10000:  # Less than 10KB is suspicious
            try:
                with open(dest_path, 'rb') as f:
                    content = f.read(1000)  # Read first 1KB
                    # Check for SAML authentication markers
                    has_saml_request = b'SAMLRequest' in content
                    has_saml_authn = b'saml2p:AuthnRequest' in content
                    if has_saml_request or has_saml_authn:
                        is_corrupted = True
                        logger.warning(f"  Detected corrupted SAML redirect: {filename} ({file_size} bytes, SAMLRequest={has_saml_request}, AuthnRequest={has_saml_authn})")
            except Exception as e:
                logger.debug(f"  Error checking file corruption: {e}")
        
        if not is_corrupted and file_size > 0:
            logger.info(f"  Skipping {filename} (already exists, {file_size} bytes)")
            return None  # Return None to indicate skipped (not success or failure)
        elif is_corrupted:
            logger.warning(f"  Re-downloading corrupted file: {filename}")
            # Continue to download
        else:
            logger.info(f"  Re-downloading empty file: {filename}")
            # Continue to download
    
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
        "application/json": ".json",
        "application/xml": ".xml",
        "text/xml": ".xml",
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
                # Get content type to determine extension
                content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
                
                # Check if filename needs an extension
                final_filename = filename
                if not Path(filename).suffix:
                    ext = ext_map.get(content_type, "")
                    if ext:
                        final_filename = f"{filename}{ext}"
                        logger.info(f"  Added extension {ext} (Content-Type: {content_type})")
                
                # Update destination path with corrected filename
                final_dest = dest_path.parent / final_filename
                
                with open(final_dest, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"  ✓ Downloaded {final_filename} ({final_dest.stat().st_size} bytes)")
                return True
                
            elif response.status_code in (401, 403):
                logger.error(f"  ✗ Authentication failed for {filename} (status {response.status_code})")
                return False
            else:
                logger.warning(f"  Attempt {attempt + 1}/{MAX_RETRIES}: Status {response.status_code} for {filename}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
        except Exception as e:
            logger.warning(f"  Attempt {attempt + 1}/{MAX_RETRIES}: Error downloading {filename}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    
    logger.error(f"  ✗ Failed to download {filename} after {MAX_RETRIES} attempts")
    return False


def main():
    """Main reprocessing function."""
    args = parse_args()
    
    backup_dir = Path(args.backup_dir)
    if not backup_dir.exists():
        logger.error(f"Backup directory not found: {backup_dir}")
        raise SystemExit(1)
    
    # Load messages.json
    messages_file = backup_dir / "json" / "messages.json"
    if not messages_file.exists():
        logger.error(f"Messages file not found: {messages_file}")
        raise SystemExit(1)
    
    logger.info(f"Loading messages from {messages_file}")
    with open(messages_file, "r", encoding="utf-8") as f:
        messages = json.load(f)
    
    logger.info(f"Loaded {len(messages)} messages")
    
    # Collect all attachments (only from learn.redhat.com domain)
    # Deduplicate by URL since same attachment may appear in multiple messages
    attachments_by_url = {}
    skipped_external = 0
    
    for msg in messages:
        for att in msg.get("attachments", []):
            url = att.get("url", "")
            # Skip external URLs (not from learn.redhat.com)
            if url and not url.startswith(BASE_URL):
                skipped_external += 1
                continue
            # Deduplicate by URL - keep first occurrence
            if url and url not in attachments_by_url:
                attachments_by_url[url] = att
    
    all_attachments = list(attachments_by_url.values())
    
    if skipped_external > 0:
        logger.info(f"Skipped {skipped_external} external URLs (not from {BASE_URL})")
    logger.info(f"Found {len(all_attachments)} unique attachments to process from {BASE_URL}")
    
    if not all_attachments:
        logger.info("No attachments to download")
        return
    
    # Set up authenticated session
    logger.info("Setting up authenticated session...")
    session = setup_session(args)
    
    # Create attachments directory
    attachments_dir = backup_dir / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    
    # Download attachments
    logger.info(f"Downloading attachments to {attachments_dir}")
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for i, att in enumerate(all_attachments, 1):
        url = att["url"]
        filename = att["filename"] or f"attachment_{i}"
        dest = attachments_dir / filename
        
        logger.info(f"[{i}/{len(all_attachments)}] Processing {filename}")
        
        # Let download_attachment() handle the existence check
        # It has corruption detection logic that needs to run
        result = download_attachment(session, url, filename, dest, args.force)
        if result is True:
            success_count += 1
        elif result is None:  # Skipped
            skip_count += 1
        else:  # False - failed
            fail_count += 1
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("REPROCESSING COMPLETE")
    logger.info("="*60)
    logger.info(f"Total attachments: {len(all_attachments)}")
    logger.info(f"Successfully downloaded: {success_count}")
    logger.info(f"Skipped (already exist): {skip_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info(f"Attachments directory: {attachments_dir}")
    
    if fail_count > 0:
        logger.warning(f"\n{fail_count} attachments failed to download.")
        logger.warning("This may be due to:")
        logger.warning("  - Expired authentication (try re-running with --auto)")
        logger.warning("  - Network issues (try again later)")
        logger.warning("  - Deleted or moved files on the server")


if __name__ == "__main__":
    main()

# Made with Bob
