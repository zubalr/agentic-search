#!/usr/bin/env python3
"""
Extract and print all unique top-level and nested keys/tags from a JSONL or JSON file, without showing values.
Usage:
    python scripts/extract_tags.py <input_file>
"""
import sys
import json
from collections import defaultdict
from pathlib import Path

def collect_keys(obj, prefix=None, keys=None):
    if keys is None:
        keys = set()
    if prefix is None:
        prefix = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = '.'.join(prefix + [k]) if prefix else k
            keys.add(full_key)
            collect_keys(v, prefix + [k], keys)
    elif isinstance(obj, list):
        for item in obj:
            collect_keys(item, prefix, keys)
    return keys

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_tags.py <input_file>")
        sys.exit(1)
    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)
    # Try to load as JSONL or JSON
    all_keys = set()
    with open(input_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        f.seek(0)
        if first_line.startswith('['):
            # JSON array
            data = json.load(f)
            for obj in data:
                all_keys.update(collect_keys(obj))
        else:
            # JSONL
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    all_keys.update(collect_keys(obj))
                except Exception:
                    continue
    print("Unique tags/keys found:")
    for key in sorted(all_keys):
        print(key)

if __name__ == "__main__":
    main()
