#!/usr/bin/env python3
"""Count all corrupted SAML redirect files."""

from pathlib import Path

attachments_dir = Path("backup_20260314_094400/attachments")

corrupted = []
valid = []

for filepath in sorted(attachments_dir.glob("*")):
    if not filepath.is_file():
        continue
        
    file_size = filepath.stat().st_size
    
    if file_size < 10000:
        try:
            with open(filepath, 'rb') as f:
                content = f.read(1000)
                if b'SAMLRequest' in content or b'saml2p:AuthnRequest' in content:
                    corrupted.append((filepath.name, file_size))
                else:
                    valid.append((filepath.name, file_size))
        except:
            pass
    else:
        valid.append((filepath.name, file_size))

print("=" * 60)
print(f"CORRUPTED FILES ({len(corrupted)}):")
print("=" * 60)
for name, size in corrupted[:10]:  # Show first 10
    print(f"  {name} ({size} bytes)")
if len(corrupted) > 10:
    print(f"  ... and {len(corrupted) - 10} more")

print("\n" + "=" * 60)
print(f"VALID FILES ({len(valid)}):")
print("=" * 60)
for name, size in valid[:5]:  # Show first 5
    print(f"  {name} ({size} bytes)")
if len(valid) > 5:
    print(f"  ... and {len(valid) - 5} more")

print("\n" + "=" * 60)
print(f"SUMMARY:")
print(f"  Total files: {len(corrupted) + len(valid)}")
print(f"  Corrupted: {len(corrupted)}")
print(f"  Valid: {len(valid)}")
print("=" * 60)

# Made with Bob
