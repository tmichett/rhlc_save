#!/usr/bin/env python3
"""
discover_api.py - Discover Khoros API endpoints on learn.redhat.com

This script helps identify the correct API paths and structure.
"""

import argparse
import json
import requests
from pathlib import Path

BASE_URL = "https://learn.redhat.com"

def load_cookies(session, cookies_file="cookies.txt"):
    """Load cookies from file."""
    import http.cookiejar
    jar = http.cookiejar.MozillaCookieJar(cookies_file)
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(jar)
        print(f"✓ Loaded {sum(1 for _ in jar)} cookies")
        return True
    except Exception as e:
        print(f"✗ Failed to load cookies: {e}")
        return False

def test_endpoint(session, path, params=None):
    """Test an API endpoint."""
    url = f"{BASE_URL}{path}"
    try:
        response = session.get(url, params=params, timeout=10)
        status = response.status_code
        
        if status == 200:
            try:
                data = response.json()
                return status, "JSON", len(json.dumps(data))
            except:
                return status, "HTML/Text", len(response.text)
        else:
            return status, response.reason, 0
    except Exception as e:
        return None, str(e), 0

def main():
    parser = argparse.ArgumentParser(description="Discover Khoros API endpoints")
    parser.add_argument("--cookies", default="cookies.txt", help="Cookies file")
    args = parser.parse_args()
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
    })
    
    if not load_cookies(session, args.cookies):
        print("\nPlease run with --auto first to get cookies, or provide cookies.txt")
        return
    
    print("\n" + "="*60)
    print("Testing API Endpoints")
    print("="*60)
    
    # Test various API paths
    endpoints = [
        # API v2
        "/api/2.0/search",
        "/api/2.0/categories",
        "/api/2.0/boards",
        "/api/2.0/messages",
        "/api/2.0/users",
        
        # API v1
        "/api/1.0/categories",
        "/api/1.0/boards",
        
        # REST API
        "/restapi/vc/categories",
        "/restapi/vc/boards",
        "/restapi/vc/messages",
        
        # Community API
        "/t5/api/core/v2/categories",
        "/t5/api/core/v2/boards",
        
        # Search
        "/api/2.0/search/messages",
        "/t5/api/search/messages",
        
        # Other patterns
        "/api/core/v2/categories",
        "/api/core/v2/boards",
    ]
    
    results = []
    for endpoint in endpoints:
        status, content_type, size = test_endpoint(session, endpoint)
        results.append((endpoint, status, content_type, size))
        
        if status == 200:
            print(f"✓ {endpoint:40} [{status}] {content_type} ({size} bytes)")
        elif status == 404:
            print(f"✗ {endpoint:40} [404] Not Found")
        elif status == 401:
            print(f"⚠ {endpoint:40} [401] Unauthorized")
        elif status == 403:
            print(f"⚠ {endpoint:40} [403] Forbidden")
        else:
            print(f"? {endpoint:40} [{status}] {content_type}")
    
    print("\n" + "="*60)
    print("Working Endpoints:")
    print("="*60)
    
    working = [r for r in results if r[1] == 200]
    if working:
        for endpoint, status, content_type, size in working:
            print(f"  {endpoint}")
            
            # Try to fetch and show sample data
            if content_type == "JSON":
                url = f"{BASE_URL}{endpoint}"
                try:
                    resp = session.get(url, timeout=10)
                    data = resp.json()
                    print(f"    Sample keys: {list(data.keys())[:5]}")
                except:
                    pass
    else:
        print("  No working endpoints found!")
        print("\n  Possible reasons:")
        print("  - API requires different authentication")
        print("  - API uses different base path")
        print("  - Site uses custom API structure")
        print("\n  Try checking the browser Network tab while browsing the site")
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    print("1. Open learn.redhat.com in browser with DevTools (F12)")
    print("2. Go to Network tab")
    print("3. Browse to community boards/messages")
    print("4. Look for API calls (filter by 'api' or 'json')")
    print("5. Note the actual endpoint paths used")
    print("="*60)

if __name__ == "__main__":
    main()

# Made with Bob
