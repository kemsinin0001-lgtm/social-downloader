#!/usr/bin/env python3
"""Social Downloader.

A command-line tool for downloading videos and media from social media platforms.
Uses only the Python standard library, so no external packages are required.
"""

import argparse
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import unquote, urlparse


CHUNK_SIZE = 8192
DEFAULT_FILENAME = "download"


def human_readable_size(num_bytes):
    """Return a human readable file size string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"


def guess_filename(url, headers=None):
    """Guess a sensible filename from the URL or response headers."""
    # Try Content-Disposition header first.
    if headers:
        disposition = headers.get("Content-Disposition") or headers.get(
            "content-disposition"
        )
        if disposition:
            match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', disposition)
            if match:
                return unquote(match.group(1)).strip()

    # Fall back to the last segment of the URL path.
    path = urlparse(url).path
    name = os.path.basename(unquote(path))
    if name and re.search(r"\.\w{2,}$", name):
        return name

    return DEFAULT_FILENAME


def resolve_output(output, url, headers=None):
    """Resolve the final output path from the user-provided output argument."""
    if os.path.isdir(output):
        filename = guess_filename(url, headers)
        return os.path.join(output, filename)
    if output:
        return output
    return guess_filename(url, headers)


def download(url, output=".", quiet=False):
    """Download the media at ``url`` to ``output``."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; social-downloader/1.0)"
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status >= 400:
                print(f"Error: server returned status {response.status}", file=sys.stderr)
                return 1

            total = response.headers.get("Content-Length")
            total_size = int(total) if total else None
            out_path = resolve_output(output, url, response.headers)

            # Avoid clobbering an existing directory.
            if os.path.isdir(out_path):
                print(f"Error: '{out_path}' is a directory", file=sys.stderr)
                return 1

            downloaded = 0
            with open(out_path, "wb") as out_file:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)

                    if not quiet and total_size:
                        percent = downloaded * 100.0 / total_size
                        bar_len = 30
                        filled = int(bar_len * downloaded // total_size)
                        bar = "#" * filled + "-" * (bar_len - filled)
                        sys.stdout.write(
                            f"\r  |{bar}| {percent:5.1f}% "
                            f"({human_readable_size(downloaded)} / "
                            f"{human_readable_size(total_size)})"
                        )
                        sys.stdout.flush()
                    elif not quiet:
                        sys.stdout.write(
                            f"\r  Downloaded {human_readable_size(downloaded)}"
                        )
                        sys.stdout.flush()

            if not quiet:
                print()  # newline after progress bar
                print(f"Saved to: {os.path.abspath(out_path)}")
                print(f"Size: {human_readable_size(downloaded)}")
            return 0

    except urllib.error.HTTPError as exc:
        print(f"HTTP error {exc.code}: {exc.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"URL error: {exc.reason}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        return 130


def build_parser():
    parser = argparse.ArgumentParser(
        prog="social-downloader",
        description="Download videos and media from social media platforms.",
    )
    parser.add_argument("url", help="URL of the media to download")
    parser.add_argument(
        "-o",
        "--output",
        default=".",
        help="Output directory or file path (default: current directory)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return download(args.url, args.output, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
