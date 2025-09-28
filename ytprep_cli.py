#!/usr/bin/env python3
"""
YouTube Preprocessing CLI Tool

Usage: python ytprep_cli.py <youtube_url> [--force] [--verbose]
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
  python ytprep_cli.py "https://youtu.be/dQw4w9WgXcQ" --verbose
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
    
    parser.add_argument(
        '--no-gemini',
        action='store_true',
        help='Skip querying Gemini LLM'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output including original content'
    )
    
    args = parser.parse_args()
    
    # Process the video
    result = process_youtube(args.url, force=args.force, query_gemini_llm=not args.no_gemini)
    
    if result['status'] == 'success':
        try:
            if args.verbose:
                # Show detailed output (current behavior)
                print("=" * 80)
                print("YOUTUBE VIDEO PROCESSING RESULTS")
                print("=" * 80)
                print()
                
                with open(result['files']['final'], 'r', encoding='utf-8') as f:
                    print("ORIGINAL CONTENT:")
                    print("-" * 40)
                    print(f.read())
                
                # Print Gemini response if available
                if 'gemini_response' in result and result['gemini_response']:
                    print()
                    print("=" * 80)
                    print("GEMINI LLM RESPONSE")
                    print("=" * 80)
                    print()
                    print(result['gemini_response'])
                    print()
                    print("=" * 80)
            else:
                # Default behavior: show debug info and Gemini response
                print(f"Debug: Using final.txt at: {result['files']['final']}")
                if 'gemini_response' in result and result['gemini_response']:
                    print(result['gemini_response'].rstrip())
                else:
                    print("No Gemini response available. Use --verbose to see full output.")
            
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
