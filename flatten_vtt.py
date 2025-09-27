import sys
import webvtt
import html  # For unescaping HTML entities

def flatten_vtt(file_path):
    try:
        flattened_lines = []
        prev_line = None

        # Iterate over each caption
        for caption in webvtt.read(file_path):
            # Split caption text into lines
            for line in caption.text.splitlines():
                stripped_line = line.strip()
                if stripped_line:
                    # Decode HTML entities
                    decoded_line = html.unescape(stripped_line)
                    # Skip consecutive duplicates
                    if decoded_line != prev_line:
                        flattened_lines.append(decoded_line)
                        prev_line = decoded_line

        # Output the flattened lines
        for line in flattened_lines:
            print(line)

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python flatten_vtt.py <file.vtt>")
        sys.exit(1)

    vtt_file = sys.argv[1]
    flatten_vtt(vtt_file)

