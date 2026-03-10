"""
Vimeo Archive Downloader
========================
Downloads all videos from a Vimeo account using yt-dlp with cookie auth.
Uses the Vimeo API to enumerate videos (including private ones), then
yt-dlp to download them.

Usage:
  1. Make sure you're logged into Vimeo in your browser
  2. Run: python3 download.py

Options:
  --browser BROWSER   Browser to extract cookies from (default: chrome)
  --list-only         Just list videos, don't download
  --skip-api          Skip API enumeration, only use profile scraping
  --profile URL       Your Vimeo profile URL (e.g. https://vimeo.com/username)
  --output-dir DIR    Download directory (default: ./downloads)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    requests = None

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MANIFEST_FILE = "manifest.json"
ARCHIVE_FILE = "downloaded.txt"  # yt-dlp's own tracking file
DEFAULT_OUTPUT_DIR = "downloads"
DEFAULT_BROWSER = "chrome"

# Find yt-dlp binary
YT_DLP = shutil.which("yt-dlp") or os.path.expanduser("~/Library/Python/3.9/bin/yt-dlp")

# ---------------------------------------------------------------------------
# API enumeration (lists all videos including private/unlisted)
# ---------------------------------------------------------------------------

def list_videos_via_api(token):
    """Use Vimeo API to get full video list. Needs public+private scopes."""
    if not requests:
        print("  requests library not available, skipping API")
        return None

    headers = {"Authorization": f"bearer {token}"}

    # Quick auth check
    resp = requests.get("https://api.vimeo.com/me", headers=headers)
    if resp.status_code != 200:
        print(f"  API auth failed (HTTP {resp.status_code}), skipping API enumeration")
        return None

    user = resp.json()
    print(f"  Account: {user.get('name')}")
    print(f"  Plan: {user.get('account', 'unknown')}")

    videos = []
    page = 1
    per_page = 100

    while True:
        resp = requests.get(
            "https://api.vimeo.com/me/videos",
            headers=headers,
            params={
                "per_page": per_page,
                "page": page,
                "fields": "uri,name,created_time,privacy,duration,link",
                "sort": "date",
                "direction": "asc",
            },
        )

        if resp.status_code != 200:
            print(f"  API error on page {page} (HTTP {resp.status_code})")
            break

        data = resp.json()
        total = data.get("total", 0)
        batch = data.get("data", [])
        videos.extend(batch)

        print(f"  Fetched page {page} — {len(videos)}/{total} videos")

        if not data.get("paging", {}).get("next"):
            break
        page += 1
        time.sleep(0.5)  # Be polite

    if videos:
        print(f"  Found {len(videos)} videos via API")
    return videos


# ---------------------------------------------------------------------------
# Profile scraping via yt-dlp (public videos only)
# ---------------------------------------------------------------------------

def list_videos_via_profile(profile_url, browser):
    """Use yt-dlp to enumerate videos from public profile."""
    print(f"  Scanning {profile_url} ...")

    cmd = [
        YT_DLP,
        "--cookies", "cookies.txt",
        "--flat-playlist",
        "--dump-json",
        profile_url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  yt-dlp error: {result.stderr[:500]}")
        return []

    videos = []
    for line in result.stdout.strip().split("\n"):
        if line:
            try:
                info = json.loads(line)
                videos.append({
                    "link": info.get("url") or info.get("webpage_url") or f"https://vimeo.com/{info.get('id', '')}",
                    "name": info.get("title", "Unknown"),
                    "uri": f"/videos/{info.get('id', '')}",
                })
            except json.JSONDecodeError:
                continue

    print(f"  Found {len(videos)} videos from profile")
    return videos


# ---------------------------------------------------------------------------
# Manifest management
# ---------------------------------------------------------------------------

def load_manifest(output_dir):
    path = Path(output_dir) / MANIFEST_FILE
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"videos": {}, "downloaded": [], "failed": [], "skipped": []}


def save_manifest(output_dir, manifest):
    path = Path(output_dir) / MANIFEST_FILE
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_video(video_url, output_dir, browser):
    """Download a single video using yt-dlp."""
    archive_path = Path(output_dir) / ARCHIVE_FILE

    cmd = [
        YT_DLP,
        "--cookies", "cookies.txt",
        # Disable impersonation to avoid keychain prompts
        "--no-check-certificates",
        # Quality: best video+audio, merge to mp4
        "-S", "res,ext",
        "--merge-output-format", "mp4",
        # Output template: date - title [id].ext
        "-o", os.path.join(output_dir, "%(upload_date>%Y-%m-%d)s - %(title).100s [%(id)s].%(ext)s"),
        # Resume support
        "--download-archive", str(archive_path),
        # Rate limiting — be polite
        "--sleep-interval", "2",
        "--max-sleep-interval", "5",
        # Retry on failure
        "--retries", "5",
        "--fragment-retries", "5",
        # Write metadata sidecar
        "--write-info-json",
        # No overwrites
        "--no-overwrites",
        video_url,
    ]

    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode == 0


def run_downloads(videos, output_dir, browser):
    """Download all videos with progress tracking."""
    manifest = load_manifest(output_dir)
    total = len(videos)

    # Store video list in manifest
    for v in videos:
        vid_id = v.get("uri", "").split("/")[-1] or v.get("link", "")
        if vid_id not in manifest["videos"]:
            manifest["videos"][vid_id] = {
                "name": v.get("name", "Unknown"),
                "link": v.get("link", ""),
                "status": "pending",
            }
    save_manifest(output_dir, manifest)

    already_done = len([v for v in manifest["videos"].values() if v["status"] == "done"])
    if already_done > 0:
        print(f"\nResuming: {already_done}/{total} already downloaded")

    pending = [
        (vid_id, info)
        for vid_id, info in manifest["videos"].items()
        if info["status"] != "done"
    ]

    print(f"Downloading {len(pending)} videos to {output_dir}/\n")

    for i, (vid_id, info) in enumerate(pending, 1):
        url = info["link"]
        name = info["name"]
        progress = already_done + i
        print(f"[{progress}/{total}] {name}")
        print(f"  URL: {url}")

        success = download_video(url, output_dir, browser)

        if success:
            manifest["videos"][vid_id]["status"] = "done"
            print(f"  Done\n")
        else:
            manifest["videos"][vid_id]["status"] = "failed"
            manifest["failed"].append(vid_id)
            print(f"  FAILED\n")

        save_manifest(output_dir, manifest)

    # Summary
    done = len([v for v in manifest["videos"].values() if v["status"] == "done"])
    failed = len([v for v in manifest["videos"].values() if v["status"] == "failed"])
    print(f"\n{'='*50}")
    print(f"Complete: {done}/{total} downloaded, {failed} failed")
    if failed:
        print("Re-run this script to retry failed downloads.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Download all Vimeo videos")
    parser.add_argument("--browser", default=DEFAULT_BROWSER,
                        help=f"Browser for cookie auth (default: {DEFAULT_BROWSER})")
    parser.add_argument("--list-only", action="store_true",
                        help="Just list videos, don't download")
    parser.add_argument("--skip-api", action="store_true",
                        help="Skip API, only use profile scraping")
    parser.add_argument("--profile", default=None,
                        help="Vimeo profile URL (e.g. https://vimeo.com/username)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"Download directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--from-manifest", action="store_true",
                        help="Skip enumeration, use existing manifest.json")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Reset failed videos to pending and retry them")

    args = parser.parse_args()

    # Handle --retry-failed
    if args.retry_failed:
        manifest = load_manifest(args.output_dir)
        reset = 0
        for v in manifest["videos"].values():
            if v["status"] == "failed":
                v["status"] = "pending"
                reset += 1
        manifest["failed"] = []
        save_manifest(args.output_dir, manifest)
        if reset:
            print(f"Reset {reset} failed videos to pending")
        else:
            print("No failed videos to retry")
        if not args.from_manifest:
            args.from_manifest = True

    # Check yt-dlp is installed
    if not Path(YT_DLP).exists() and not shutil.which("yt-dlp"):
        print("ERROR: yt-dlp not found. Install with: pip3 install yt-dlp")
        sys.exit(1)

    print("Vimeo Archive Downloader")
    print("=" * 50)

    # Create output dir
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Step 1: Enumerate videos
    videos = None

    if args.from_manifest:
        manifest = load_manifest(args.output_dir)
        if manifest["videos"]:
            videos = [
                {"name": info["name"], "link": info["link"], "uri": f"/videos/{vid_id}"}
                for vid_id, info in manifest["videos"].items()
            ]
            print(f"\n[1] Loaded {len(videos)} videos from existing manifest")
        else:
            print("\nERROR: No videos in manifest. Run without --from-manifest first.")
            sys.exit(1)

    if videos is None and not args.skip_api:
        token = os.getenv("VIMEO_ACCESS_TOKEN")
        if token and token != "paste_your_token_here":
            print("\n[1] Enumerating videos via API...")
            api_videos = list_videos_via_api(token)
            if api_videos:
                videos = api_videos

    if videos is None and args.profile:
        print("\n[1] Enumerating videos from profile...")
        videos = list_videos_via_profile(args.profile, args.browser)

    if videos is None:
        print("\nERROR: No videos found. Provide either:")
        print("  - --from-manifest (if you've already run once)")
        print("  - A valid API token in .env (for private + public videos)")
        print("  - --profile https://vimeo.com/yourusername (public videos only)")
        sys.exit(1)

    if not videos:
        print("\nNo videos found!")
        sys.exit(0)

    # Ensure all videos have a link
    for v in videos:
        if not v.get("link"):
            vid_id = v.get("uri", "").split("/")[-1]
            if vid_id:
                v["link"] = f"https://vimeo.com/{vid_id}"

    print(f"\nTotal videos to process: {len(videos)}")

    if args.list_only:
        print("\nVideo list:")
        for i, v in enumerate(videos, 1):
            privacy = v.get("privacy", {}).get("view", "?") if isinstance(v.get("privacy"), dict) else "?"
            print(f"  {i:4d}. [{privacy:8s}] {v.get('name', 'Unknown')}")
            print(f"        {v.get('link', 'no link')}")
        return

    # Step 2: Download
    print(f"\n[2] Downloading videos...")
    print(f"  Browser: {args.browser}")
    print(f"  Output:  {args.output_dir}/")
    print(f"  Make sure you're logged into Vimeo in {args.browser}!\n")

    run_downloads(videos, args.output_dir, args.browser)


if __name__ == "__main__":
    main()
