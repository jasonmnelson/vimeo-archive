"""Quick test to verify API token works and download links are available."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("VIMEO_ACCESS_TOKEN")
if not token or token == "paste_your_token_here":
    print("ERROR: Paste your token into .env first")
    exit(1)

headers = {"Authorization": f"bearer {token}"}

# Test 1: Check authentication and account info
print("Testing authentication...")
resp = requests.get("https://api.vimeo.com/me", headers=headers)
if resp.status_code != 200:
    print(f"FAILED: HTTP {resp.status_code} — {resp.json().get('error', 'Unknown error')}")
    exit(1)

user = resp.json()
print(f"  Account: {user.get('name')}")
print(f"  Plan: {user.get('account', 'unknown')}")

# Test 2: Fetch one video and check for download links
print("\nFetching first video...")
resp = requests.get(
    "https://api.vimeo.com/me/videos",
    headers=headers,
    params={"per_page": 1, "fields": "uri,name,download,created_time"},
)
if resp.status_code != 200:
    print(f"FAILED: HTTP {resp.status_code}")
    exit(1)

data = resp.json()
print(f"  Total videos: {data.get('total')}")

if data["data"]:
    video = data["data"][0]
    print(f"  Sample video: {video.get('name')}")

    if "download" in video and video["download"]:
        print(f"  Download links: YES ({len(video['download'])} quality options)")
        for d in video["download"]:
            size_mb = d.get("size", 0) / 1024 / 1024
            print(f"    - {d.get('quality', '?')} ({d.get('width')}x{d.get('height')}) — {size_mb:.1f} MB")
        print("\n✓ Everything works! Ready to build the full downloader.")
    else:
        print("  Download links: NO")
        print("\n✗ Your plan may not support API downloads, or the 'video_files' scope is missing.")
        print("  Check your token scopes at developer.vimeo.com/apps")
