#!/usr/bin/env python3
"""Test script to check attachment extraction from a rendered page."""

import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

TEST_URL = "https://learn.redhat.com/t5/Lab-Engineer-Updates/RHTLC-Release-3-4-3/m-p/57651"

def main():
    print(f"Fetching {TEST_URL} with Playwright...")
    print("\n" + "=" * 60)
    print("  Browser Login Test")
    print("=" * 60)
    print("  A browser window will open.")
    print("  1. Log in if needed")
    print("  2. Wait for the page to fully load")
    print("  3. Return here and press Enter")
    print("=" * 60)
    
    with sync_playwright() as p:
        # Launch in NON-headless mode so user can log in
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("\nOpening browser and navigating to page...")
        page.goto(TEST_URL, timeout=60000)
        
        print("\nBrowser opened. Please log in if needed and wait for page to load...")
        input("Press Enter after the page has fully loaded: ")
        
        # Wait for dynamic content
        page.wait_for_timeout(3000)
        
        html_content = page.content()
        browser.close()
    
    print(f"Got HTML content: {len(html_content)} bytes")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, "lxml")
    
    # Look for PDF links
    print("\n=== Looking for PDF links ===")
    pdf_links = soup.find_all("a", href=lambda x: x and ".pdf" in x.lower())
    print(f"Found {len(pdf_links)} PDF links")
    for link in pdf_links:
        print(f"  href: {link.get('href')}")
        print(f"  class: {link.get('class')}")
        print(f"  text: {link.get_text(strip=True)}")
        print()
    
    # Look for attachment-related classes
    print("\n=== Looking for attachment classes ===")
    att_links = soup.find_all("a", class_=lambda x: x and "attachment" in str(x).lower())
    print(f"Found {len(att_links)} links with 'attachment' in class")
    for link in att_links[:5]:
        print(f"  href: {link.get('href')}")
        print(f"  class: {link.get('class')}")
        print(f"  text: {link.get_text(strip=True)}")
        print()
    
    # Look for any download-related elements
    print("\n=== Looking for download-related elements ===")
    download_elems = soup.find_all(lambda tag: tag.name == "a" and (
        "download" in str(tag.get("class", "")).lower() or
        "download" in str(tag.get("href", "")).lower()
    ))
    print(f"Found {len(download_elems)} download-related elements")
    for elem in download_elems[:5]:
        print(f"  href: {elem.get('href')}")
        print(f"  class: {elem.get('class')}")
        print(f"  text: {elem.get_text(strip=True)[:50]}")
        print()
    
    # Save HTML for manual inspection
    with open("/tmp/rendered_page.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\nFull HTML saved to /tmp/rendered_page.html")

if __name__ == "__main__":
    main()

# Made with Bob
