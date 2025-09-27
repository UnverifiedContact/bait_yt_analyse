#!/usr/bin/env python3
"""
YouTube Preprocessing CLI Tool

Usage: python ytprep_cli.py <youtube_url> [--force]
"""

import sys
import argparse
from ytprep import process_youtube


def main():
    parser = argparse.ArgumentParser(
        description="Process YouTube video for subtitle analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ytprep_cli.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  python ytprep_cli.py "https://youtu.be/dQw4w9WgXcQ" --force
        """
    )
    
    parser.add_argument(
        'url',
        help='YouTube video URL to process'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download and overwrite cached data'
    )
    
    args = parser.parse_args()
    
    # Process the video
    result = process_youtube(args.url, force=args.force)
    
    if result['status'] == 'success':
        # Print the contents of final.txt
        try:
            with open(result['files']['final'], 'r', encoding='utf-8') as f:
                print(f.read())
            sys.exit(0)
        except FileNotFoundError:
            print(f"Error: final.txt not found at {result['files']['final']}")
            sys.exit(1)
    
    elif result['status'] == 'no_subtitles':
        print("Error: No English subtitles available for this video")
        sys.exit(2)
    
    else:  # error
        error_msg = result.get('error', 'Unknown error occurred')
        print(f"Error: {error_msg}")
        sys.exit(1)


if __name__ == '__main__':
    main()
