import os
import re
import json
import webvtt
import html
import yt_dlp
import requests
from pathlib import Path
from typing import Dict, Optional, Any
from urllib.parse import urlparse, parse_qs

def query_gemini(content: str, model_name: str = "gemini-2.0-flash") -> str:
    """
    Query Gemini LLM using REST API.
    
    Args:
        content: The text content to send to Gemini
        model_name: The Gemini model to use (default: gemini-2.0-flash)
    
    Returns:
        The response from Gemini
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required. Please set it with your API key from https://aistudio.google.com/app/api-keys")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': api_key
    }
    
    data = {
        "contents": [{
            "parts": [{
                "text": content
            }]
        }]
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    result = response.json()
    
    if 'candidates' in result and len(result['candidates']) > 0:
        return result['candidates'][0]['content']['parts'][0]['text']
    else:
        return "No response generated from Gemini"


def extract_youtube_id(value: str) -> str | None:
    """Extract YouTube video ID from URL or return the ID if already provided."""
    if not value:
        return None
    value = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    parsed = urlparse(value)
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        m = re.match(r"^/(embed|shorts)/([^/?#&]+)", parsed.path)
        if m:
            return m.group(2)
    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")
    return None


def download_metadata_and_subtitles(video_id: str, force: bool = False, cache_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Download video metadata and subtitles using yt-dlp."""
    if cache_dir is None:
        cache_dir = Path("cache") / video_id
    else:
        cache_dir = cache_dir / video_id
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we already have cached data (unless force is True)
    if not force and (cache_dir / "metadata.json").exists():
        with open(cache_dir / "metadata.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_id, download=False)
            
            # Extract metadata
            metadata = {
                'video_id': video_id,
                'title': info.get('title', ''),
                'uploader': info.get('uploader', ''),
                'channel': info.get('channel', ''),
                'description': info.get('description', ''),
                'subtitles': {}
            }
            
            # Process subtitles
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            # Prefer human-uploaded English subtitles
            if 'en' in subtitles:
                subtitle_info = subtitles['en']
                if isinstance(subtitle_info, list) and len(subtitle_info) > 0:
                    # Get the best quality subtitle
                    best_sub = max(subtitle_info, key=lambda x: x.get('ext', 'vtt') == 'vtt')
                    metadata['subtitles'] = {
                        'url': best_sub['url'],
                        'ext': best_sub.get('ext', 'vtt'),
                        'type': 'human'
                    }
            elif 'en' in automatic_captions:
                caption_info = automatic_captions['en']
                if isinstance(caption_info, list) and len(caption_info) > 0:
                    # Get the best quality auto caption
                    best_caption = max(caption_info, key=lambda x: x.get('ext', 'vtt') == 'vtt')
                    metadata['subtitles'] = {
                        'url': best_caption['url'],
                        'ext': best_caption.get('ext', 'vtt'),
                        'type': 'auto'
                    }
            
            # Save metadata to cache
            with open(cache_dir / "metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            return metadata
            
        except Exception as e:
            raise Exception(f"Failed to extract video information: {str(e)}")


def download_subtitles(subtitle_info: Dict[str, Any], cache_dir: Path) -> str:
    """Download subtitles from URL and save to cache directory."""
    import requests
    
    response = requests.get(subtitle_info['url'])
    response.raise_for_status()
    
    subtitle_file = cache_dir / "subtitles_raw.vtt"
    with open(subtitle_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    return str(subtitle_file)


def flatten_subtitles(vtt_file: str) -> str:
    """Flatten VTT subtitles into plain text, removing duplicates."""
    flattened_lines = []
    prev_line = None
    
    try:
        for caption in webvtt.read(vtt_file):
            for line in caption.text.splitlines():
                stripped_line = line.strip()
                if stripped_line:
                    decoded_line = html.unescape(stripped_line)
                    if decoded_line != prev_line:
                        flattened_lines.append(decoded_line)
                        prev_line = decoded_line
    except Exception as e:
        raise Exception(f"Failed to process subtitles: {str(e)}")
    
    return '\n'.join(flattened_lines)


def save_text_file(content: str, file_path: Path) -> None:
    """Save content to a text file with UTF-8 encoding."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def generate_final_txt(metadata: Dict[str, Any], flattened_subtitles: str, 
                      subtitle_type: str, prompt_content: str, cache_dir: Path) -> str:
    """Generate the final.txt file with all consolidated content."""
    lines = [prompt_content, ""]
    
    # Add title
    lines.append(f"Title: {metadata['title']}")
    
    # Add uploader if available
    if metadata.get('uploader'):
        lines.append(f"Uploader: {metadata['uploader']}")
    
    # Add channel if available
    if metadata.get('channel'):
        lines.append(f"Channel: {metadata['channel']}")
    
    # Add description
    lines.append("Description:")
    lines.append(metadata.get('description', ''))
    lines.append("")
    
    # Add subtitles
    lines.append(f"Subtitles ({subtitle_type}):")
    lines.append(flattened_subtitles)
    
    return '\n'.join(lines)


def process_youtube(url: str, prompt: Optional[str] = None, force: bool = False, query_gemini_llm: bool = True, cache_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a YouTube video URL and generate consolidated files.
    
    Args:
        url: YouTube video URL
        prompt: Optional prompt to override default
        force: Whether to force re-download of cached data
        query_gemini_llm: Whether to query Gemini LLM with the final content
        cache_dir: Optional cache directory path. Defaults to TMP env var or script directory/cache
    
    Returns:
        Dictionary with status, file paths, and Gemini response
    """
    try:
        # Extract video ID
        video_id = extract_youtube_id(url)
        if video_id is None:
            raise ValueError(f"Could not extract video ID from URL or ID: {url}")
        
        # Set up cache directory
        if cache_dir is None:
            # Default to TMP environment variable, fallback to script directory/cache
            base_cache_dir = os.getenv('TMP', str(Path(__file__).parent / "cache"))
        else:
            base_cache_dir = cache_dir
        
        cache_dir = Path(base_cache_dir) / video_id
        
        # If force is True, delete entire cache directory to ensure complete regeneration
        if force and cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or download metadata
        metadata = download_metadata_and_subtitles(video_id, force, Path(base_cache_dir))
        
        # Check if subtitles are available
        if not metadata.get('subtitles'):
            return {
                "status": "no_subtitles",
                "video_id": video_id,
                "cache_dir": str(cache_dir),
                "files": {}
            }
        
        # Download subtitles (always download since cache is cleared if force=True)
        subtitle_file = download_subtitles(metadata['subtitles'], cache_dir)
        
        # Flatten subtitles
        flattened_subtitles = flatten_subtitles(str(subtitle_file))
        save_text_file(flattened_subtitles, cache_dir / "subtitles_flat.txt")
        
        # Load or copy prompt
        if prompt is None:
            script_dir = Path(__file__).parent
            prompt_file = script_dir / "prompt.txt"
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_content = f.read()
            else:
                prompt_content = "You are given the transcript, title, uploader, channel, and description of a YouTube video.\nYour task is to suggest three alternative titles for this video that are accurate, descriptive, and non-clickbait. The titles should reflect the actual content of the video without exaggeration. Each title should be a single sentence and under 100 characters."
        else:
            prompt_content = prompt
        
        save_text_file(prompt_content, cache_dir / "prompt.txt")
        
        # Save individual metadata files
        save_text_file(metadata['title'], cache_dir / "title.txt")
        
        if metadata.get('uploader'):
            save_text_file(metadata['uploader'], cache_dir / "uploader.txt")
        
        if metadata.get('channel'):
            save_text_file(metadata['channel'], cache_dir / "channel.txt")
        
        save_text_file(metadata.get('description', ''), cache_dir / "description.txt")
        
        # Generate final.txt
        subtitle_type = "Human" if metadata['subtitles']['type'] == 'human' else "Auto-generated"
        final_content = generate_final_txt(
            metadata, flattened_subtitles, subtitle_type, prompt_content, cache_dir
        )
        save_text_file(final_content, cache_dir / "final.txt")
        
        # Query Gemini LLM if requested
        gemini_response = ""
        if query_gemini_llm:
            try:
                gemini_response = query_gemini(final_content)
                # Save Gemini response to a separate file
                save_text_file(gemini_response, cache_dir / "gemini_response.txt")
            except Exception as e:
                gemini_response = f"Error querying Gemini: {str(e)}"
                save_text_file(gemini_response, cache_dir / "gemini_response.txt")
        
        # Return result
        files = {
            "title": str(cache_dir / "title.txt"),
            "description": str(cache_dir / "description.txt"),
            "subtitles_raw": str(cache_dir / "subtitles_raw.vtt"),
            "subtitles_flat": str(cache_dir / "subtitles_flat.txt"),
            "final": str(cache_dir / "final.txt"),
            "prompt": str(cache_dir / "prompt.txt")
        }
        
        if query_gemini_llm:
            files["gemini_response"] = str(cache_dir / "gemini_response.txt")
        
        if metadata.get('uploader'):
            files["uploader"] = str(cache_dir / "uploader.txt")
        
        if metadata.get('channel'):
            files["channel"] = str(cache_dir / "channel.txt")
        
        result = {
            "status": "success",
            "video_id": video_id,
            "cache_dir": str(cache_dir),
            "files": files
        }
        
        if query_gemini_llm:
            result["gemini_response"] = gemini_response
        
        return result
        
    except ValueError as e:
        return {
            "status": "error",
            "video_id": "",
            "cache_dir": "",
            "files": {},
            "error": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "video_id": "",
            "cache_dir": "",
            "files": {},
            "error": str(e)
        }
