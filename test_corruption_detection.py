#!/usr/bin/env python3
"""Test script to verify SAML corruption detection."""

from pathlib import Path

def check_file(filepath):
    """Check if a file is corrupted SAML redirect."""
    file_size = filepath.stat().st_size
    print(f"\nChecking: {filepath.name}")
    print(f"  Size: {file_size} bytes")
    
    if file_size < 10000:
        try:
            with open(filepath, 'rb') as f:
                content = f.read(1000)
                has_saml_request = b'SAMLRequest' in content
                has_saml_authn = b'saml2p:AuthnRequest' in content
                
                print(f"  SAMLRequest found: {has_saml_request}")
                print(f"  AuthnRequest found: {has_saml_authn}")
                
                if has_saml_request or has_saml_authn:
                    print(f"  ✗ CORRUPTED - SAML redirect detected")
                    return True
                else:
                    print(f"  ✓ OK - No SAML markers")
                    return False
        except Exception as e:
            print(f"  Error: {e}")
            return False
    else:
        print(f"  ✓ OK - File size > 10KB")
        return False

# Test on a few files
attachments_dir = Path("backup_20260314_094400/attachments")

test_files = [
    "RELEASE_NOTES_V2.2.5.pdf",
    "Part 2 of 2 RHA - OpenShift, Containers & Kubernetes Workshop.pdf",
    "Instructor Global All-Hands _ December 2025.pdf",
]

print("=" * 60)
print("Testing SAML Corruption Detection")
print("=" * 60)

corrupted_count = 0
for filename in test_files:
    filepath = attachments_dir / filename
    if filepath.exists():
        if check_file(filepath):
            corrupted_count += 1
    else:
        print(f"\n{filename}: NOT FOUND")

print("\n" + "=" * 60)
print(f"Total corrupted files found: {corrupted_count}/{len(test_files)}")
print("=" * 60)

# Made with Bob
