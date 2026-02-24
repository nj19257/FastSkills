---
name: duckduckgo-search
description: Search the web using DuckDuckGo — no API key required. Supports web/text search, news, images, and videos. Use when the user wants to search the internet, find current news, look up information online, or perform any web search task. Triggers on requests like "search the web for...", "find news about...", "look up...", or "what is the latest on...".
---

# DuckDuckGo Search

Search the web for free using DuckDuckGo. No API key needed.

## Setup

Install the `ddgs` package if not present:

```bash
pip install ddgs
```

## Quick Start

```bash
# Web search (default)
python3 {baseDir}/scripts/search.py "your query" --num 10

# News search
python3 {baseDir}/scripts/search.py "AI breakthroughs" --type news --num 5

# Image search
python3 {baseDir}/scripts/search.py "mountain landscape" --type images --num 5

# Video search
python3 {baseDir}/scripts/search.py "python tutorial" --type videos --num 5

# Raw JSON output
python3 {baseDir}/scripts/search.py "climate change" --json
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--type` | `text`, `news`, `images`, `videos` | `text` |
| `--region` | Region code (e.g. `us-en`, `uk-en`, `de-de`, `fr-fr`) | `us-en` |
| `--safe` | Safesearch: `on`, `moderate`, `off` | `moderate` |
| `--time` | Time filter: `d` (day), `w` (week), `m` (month), `y` (year) | none |
| `--num` | Max results to return | `10` |
| `--json` | Output raw JSON | off |

## Result Fields

| Type | Key fields |
|------|-----------|
| `text` | `title`, `href`, `body` |
| `news` | `title`, `url`, `source`, `date`, `body` |
| `images` | `title`, `image`, `url`, `thumbnail` |
| `videos` | `title`, `content`, `publisher`, `duration` |

## Notes

- No API key or account needed — DuckDuckGo is free to use.
- For JSON output, pipe to `python3 -c "import json,sys; ..."` to process programmatically.
- Images and videos may occasionally return 403 errors due to DuckDuckGo rate limiting; retry or fall back to text search.
- Use `--region` to get localized results (e.g. `fr-fr` for French results, `jp-jp` for Japanese).
