#!/usr/bin/env python3
"""DuckDuckGo search script. No API key required.

Usage:
    search.py <query> [options]

Options:
    --type      text (default), news, images, videos
    --region    Region code (e.g. us-en, uk-en, de-de). Default: us-en
    --safe      Safesearch: on, moderate, off. Default: moderate
    --time      Timelimit: d (day), w (week), m (month), y (year)
    --num       Max results (default: 10)
    --json      Output raw JSON
"""
import sys
import json
import argparse

def main():
    parser = argparse.ArgumentParser(description="DuckDuckGo search")
    parser.add_argument("query", nargs="+", help="Search query")
    parser.add_argument("--type", default="text", choices=["text", "news", "images", "videos"])
    parser.add_argument("--region", default="us-en")
    parser.add_argument("--safe", default="moderate", choices=["on", "moderate", "off"])
    parser.add_argument("--time", default=None, choices=["d", "w", "m", "y"])
    parser.add_argument("--num", type=int, default=10)
    parser.add_argument("--json", action="store_true", dest="raw_json")
    args = parser.parse_args()

    query = " ".join(args.query)

    try:
        from ddgs import DDGS
    except ImportError:
        print("Error: 'ddgs' package not found. Install with: pip install ddgs", file=sys.stderr)
        sys.exit(1)

    ddgs = DDGS()
    search_kwargs = dict(
        region=args.region,
        safesearch=args.safe,
        timelimit=args.time,
        max_results=args.num,
    )

    try:
        if args.type == "text":
            results = ddgs.text(query, **search_kwargs)
        elif args.type == "news":
            results = ddgs.news(query, **search_kwargs)
        elif args.type == "images":
            results = ddgs.images(query, **search_kwargs)
        elif args.type == "videos":
            results = ddgs.videos(query, **search_kwargs)
        else:
            results = []
    except Exception as e:
        print(f"Search error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.raw_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    if not results:
        print("No results found.")
        return

    format_results(results, args.type)


def format_results(results, search_type):
    if search_type == "text":
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.get('title', 'No title')}")
            print(f"   {r.get('href', '')}")
            body = r.get("body", "")
            if body:
                print(f"   {body[:150]}")
            print()

    elif search_type == "news":
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.get('title', 'No title')}")
            source = r.get("source", "")
            date = r.get("date", "")
            if source or date:
                print(f"   {source} · {date}")
            print(f"   {r.get('url', '')}")
            body = r.get("body", "")
            if body:
                print(f"   {body[:150]}")
            print()

    elif search_type == "images":
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.get('title', 'No title')}")
            print(f"   Image: {r.get('image', '')}")
            print(f"   Source: {r.get('url', '')}")
            print()

    elif search_type == "videos":
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.get('title', 'No title')}")
            print(f"   {r.get('content', r.get('embed_url', ''))}")
            publisher = r.get("publisher", "")
            duration = r.get("duration", "")
            if publisher or duration:
                print(f"   {publisher} · {duration}")
            print()


if __name__ == "__main__":
    main()
