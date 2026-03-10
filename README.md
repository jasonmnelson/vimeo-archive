# Vimeo Archive

A simple tool to bulk download your entire Vimeo video library with a live progress dashboard. Built for non-programmers who need to archive years of video content from Vimeo.

![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Why This Exists

Vimeo doesn't offer a "download all" button. If you have hundreds or thousands of videos going back years, downloading them one at a time through the web interface isn't practical. The Vimeo API can help, but it requires a paid plan (Standard or above) for download links.

This tool uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) with your browser cookies to download every video from your Vimeo account — no special API plan required. It includes a live web dashboard so you (and your team) can watch the progress.

## Features

- Downloads all videos from a Vimeo profile or account
- Tracks progress with a manifest file — fully resumable if interrupted
- Live web dashboard with progress bars, stats, and video lists
- Retry failed downloads with a single flag
- Saves videos as MP4 with date and title in the filename
- Stores metadata (JSON) alongside each video

## Quick Start

### 1. Install dependencies

```bash
pip3 install requests python-dotenv yt-dlp
```

For best results, also install [ffmpeg](https://ffmpeg.org/download.html) (needed for some video formats).

### 2. Clone this repo

```bash
git clone https://github.com/jasonmnelson/vimeo-archive.git
cd vimeo-archive
```

### 3. Export your browser cookies (one time)

Make sure you're logged into Vimeo in your browser, then:

```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt --flat-playlist "https://vimeo.com/YOUR_USERNAME" 2>/dev/null
```

This creates a `cookies.txt` file. You'll be prompted for your macOS keychain password once. Replace `chrome` with `firefox` or `safari` if needed.

### 4. Run the first download pass

This scans your Vimeo profile and starts downloading everything:

```bash
python3 download.py --skip-api --profile https://vimeo.com/YOUR_USERNAME
```

### 5. Watch the progress

In a separate terminal:

```bash
python3 dashboard.py
```

Then open **http://localhost:8090** in your browser.

### 6. Retry any failures

After the first pass completes:

```bash
python3 download.py --retry-failed --skip-api
```

## How It Works

1. **Enumeration** — Scans your Vimeo profile page to find all video URLs
2. **Manifest** — Saves the full video list to `downloads/manifest.json` so it can resume
3. **Download** — Uses yt-dlp to download each video as an MP4 at the best available quality
4. **Tracking** — Updates the manifest after each video (done/failed/pending)
5. **Dashboard** — A local web server reads the manifest and shows live progress

## Command Reference

```
python3 download.py [options]

Options:
  --profile URL        Your Vimeo profile URL (e.g. https://vimeo.com/username)
  --skip-api           Skip Vimeo API, use profile scanning only
  --from-manifest      Skip scanning, use existing video list from manifest
  --retry-failed       Reset failed videos and retry them
  --list-only          Just list videos, don't download
  --browser BROWSER    Browser for cookie export (default: chrome)
  --output-dir DIR     Download directory (default: ./downloads)
```

## Resuming After Interruption

If your computer sleeps, restarts, or the download is interrupted for any reason, just run:

```bash
python3 download.py --from-manifest --skip-api
```

It picks up right where it left off.

## File Structure

```
vimeo-archive/
  download.py          # Main downloader script
  dashboard.py         # Live progress dashboard
  test_api.py          # API token tester (optional)
  cookies.txt          # Your browser cookies (not committed)
  .env                 # API token if you have one (not committed)
  downloads/
    manifest.json      # Progress tracking
    downloaded.txt     # yt-dlp's archive file
    *.mp4              # Your videos
    *.info.json        # Video metadata
```

## macOS Keychain Note

On macOS, yt-dlp may prompt for your keychain password when extracting browser cookies. To avoid repeated prompts:

1. Export cookies to a file once (step 3 above)
2. Use `--from-manifest` on subsequent runs to avoid re-scanning
3. If prompted, click **"Always Allow"** to permanently authorize access

## Optional: Vimeo API

If you have a Vimeo Standard plan or above, you can use the API for more reliable video enumeration (including private videos):

1. Create an app at [developer.vimeo.com](https://developer.vimeo.com)
2. Generate a personal access token with scopes: `public`, `private`, `video_files`
3. Add it to `.env`: `VIMEO_ACCESS_TOKEN=your_token_here`
4. Run without `--skip-api`

## Built With

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — The engine that handles actual video downloads
- [Claude Code](https://claude.ai/claude-code) — AI pair programming assistant

## License

MIT — Use it however you'd like.
