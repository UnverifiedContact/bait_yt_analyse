# YouTube Alterantive Title Processor

A Python tool for downloading YouTube video metadata and subtitles, then generating consolidated files ready for LLM processing to create non-clickbait titles.

## Features

- Download YouTube video metadata (title, uploader, channel, description)
- Extract and process subtitles (preferring human-uploaded over auto-generated)
- Flatten and deduplicate subtitle text
- Generate consolidated `final.txt` files for LLM input
- Caching system to avoid re-downloading
- Both CLI and library interfaces

## Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Get a Gemini API key:
   - Visit https://aistudio.google.com/app/api-keys
   - Create a new API key
   - Set it as an environment variable:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```
   Or add it to your shell profile (`.bashrc`, `.zshrc`, etc.) for persistence.

## Usage

### CLI Usage

```bash
# Process a YouTube video
python ytprep_cli.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Force re-download (overwrite cache)
python ytprep_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" --force
```

### Library Usage

```python
from ytprep import process_youtube

result = process_youtube(
    url="https://www.youtube.com/watch?v=VIDEO_ID",
    prompt=None,  # Optional custom prompt
    force=False   # Force re-download
)

print(f"Status: {result['status']}")
print(f"Video ID: {result['video_id']}")
print(f"Files: {result['files']}")
```

## Output Structure

For each processed video, files are saved in `cache/<video_id>/`:

- `title.txt` - Video title
- `uploader.txt` - Video uploader (if available)
- `channel.txt` - Channel name (if available)  
- `description.txt` - Video description
- `subtitles_raw.vtt` - Raw subtitle file
- `subtitles_flat.txt` - Flattened, deduplicated subtitles
- `prompt.txt` - Processing prompt
- `final.txt` - Consolidated file for LLM input

## Exit Codes

- `0` - Success
- `1` - General error (bad URL, network failure, etc.)
- `2` - No English subtitles available

## Environment Variables

- `GEMINI_API_KEY` - Required. Your Gemini API key from https://aistudio.google.com/app/api-keys

## Requirements

- Python 3.7+
- yt-dlp
- webvtt-py
- requests
