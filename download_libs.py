#!/usr/bin/env python3
"""
Download vendor libraries for offline use.
Run this script to download all CDN dependencies locally.
"""

import os
import urllib.request
import ssl
from pathlib import Path

# Create SSL context that doesn't verify certificates (for reliability)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Base directory for vendor libraries
LIBS_DIR = Path(__file__).parent / "assets" / "libs"
LIBS_DIR.mkdir(parents=True, exist_ok=True)

# Vendor files to download
VENDOR_FILES = {
    # Tailwind CSS - we'll use the standalone CLI or browser build
    "tailwindcss.js": "https://cdn.tailwindcss.com",
    
    # TOAST UI Editor
    "toastui-editor.min.css": "https://uicdn.toast.com/editor/latest/toastui-editor.min.css",
    "toastui-editor-all.min.js": "https://uicdn.toast.com/editor/latest/toastui-editor-all.min.js",
    
    # Lucide Icons
    "lucide.min.js": "https://unpkg.com/lucide@0.263.1/dist/umd/lucide.js",
}

def download_file(url: str, dest_path: Path) -> bool:
    """Download a file from URL to destination path."""
    try:
        print(f"Downloading {url}...")
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
            content = response.read()
            dest_path.write_bytes(content)
            print(f"  ✓ Saved to {dest_path} ({len(content)} bytes)")
            return True
            
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def main():
    """Download all vendor files."""
    print("=" * 60)
    print("Downloading vendor libraries for offline use")
    print("=" * 60)
    print(f"Target directory: {LIBS_DIR}")
    print()
    
    success_count = 0
    failed_files = []
    
    for filename, url in VENDOR_FILES.items():
        dest_path = LIBS_DIR / filename
        if download_file(url, dest_path):
            success_count += 1
        else:
            failed_files.append((filename, url))
        print()
    
    # Summary
    print("=" * 60)
    print(f"Downloaded: {success_count}/{len(VENDOR_FILES)} files")
    
    if failed_files:
        print("\nFailed downloads:")
        for filename, url in failed_files:
            print(f"  - {filename}")
        print("\nYou may need to manually download these files.")
        return 1
    else:
        print("\n✓ All vendor libraries downloaded successfully!")
        print("\nNext steps:")
        print("  1. Update index.html to use local paths")
        print("  2. Update Python backend to serve static files")
        return 0

if __name__ == "__main__":
    exit(main())
