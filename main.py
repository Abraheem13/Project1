# main.py
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.scanner import FileScanner
from utils import (
    filter_by_extensions,
    filter_larger_than,
    only_text_files,
    brief_view,
    count_by_extension,
    sort_by
)
import argparse
import json


def run(root: str, show: int):
    scanner = FileScanner(root, include_hidden=False, follow_symlinks=False)
    files = list(scanner.scan())

    print(f"Scanned: {len(files)} files under {Path(root).resolve()}")
    print("\nTop extensions:", count_by_extension(files))

    text_files = only_text_files(files)
    big_files = filter_larger_than(files, min_kb=512)
    doc_files = filter_by_extensions(files, ["txt", "md", "pdf", "docx"])

    largest_n = sort_by(files, key_func=lambda m: m.size_bytes, reverse=True)[:show]
    preview_data = brief_view(largest_n)

    print("\nLargest files:")
    print(json.dumps(preview_data, indent=2))

    print("\nSummary:")
    print(f"  Text files: {len(text_files)}")
    print(f"  >= 512KB  : {len(big_files)}")
    print(f"  Doc files : {len(doc_files)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-threaded File Tagger - Day 1 Demo")
    parser.add_argument("root", help="Folder to scan")
    parser.add_argument("--show", type=int, default=10, help="Number of largest files to display")
    args = parser.parse_args()

    run(args.root, args.show)
# Test Code
## New changes
