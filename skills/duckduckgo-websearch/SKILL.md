---
name: duckduckgo-websearch
description: Search the web using DuckDuckGo. Use when the user wants to search the internet, find current information, look up facts, search for news, or find websites about specific topics. Triggers include requests like "search for X", "look up Y", "find information about Z", "what is X" (when X may be recent, niche, or unknown), "tell me about Y", "what's the latest on", "news about", or any query requiring up-to-date web information. Also use when the user asks about a specific named entity (product, company, tool, person, event) that might not be in the training data.
---

# DuckDuckGo Web Search

Search the web using DuckDuckGo's search engine. Returns results in JSON format for easy parsing.

## Quick Start

This skill uses [uv](https://docs.astral.sh/uv/) to manage dependencies. The `ddgs` package is automatically installed when you run the script.

```bash
# Basic web search
uv run --directory /path/to/duckduckgo-websearch python scripts/search.py "your query here"

# Search with options
uv run --directory /path/to/duckduckgo-websearch python scripts/search.py "query" --num 5 --time w

# Search for news
uv run --directory /path/to/duckduckgo-websearch python scripts/search.py "query" --type news --num 5
```

**Tip:** When calling from the skills directory, `{baseDir}` refers to `/Users/leekayiu/Documents/workspace/fastskills/skills/duckduckgo-websearch`.

## When to Use This Skill

Use web search when the user asks:
- **"What is X?"** or **"Tell me about Y"** (especially if X/Y might be recent or niche)
- **"Search for..."** or **"Look up..."**
- **"What's the latest on..."** or **"News about..."**
- About a specific named entity you're unsure about (new tools, recent events, obscure topics)
- For current information that may have changed since training data

## Search Script Usage

The `search.py` script provides web and news search capabilities.

### Basic Search

```bash
uv run --directory {baseDir} python scripts/search.py "python programming tips"
```

### Search Options

| Option | Description | Default |
|--------|-------------|---------|
| `--num N` | Number of results | 10 |
| `--type {web,news}` | Search type | web |
| `--region CODE` | Region (e.g., us-en, uk-en) | wt-wt (worldwide) |
| `--safesearch {on,moderate,off}` | SafeSearch level | moderate |
| `--time {d,w,m,y}` | Time filter | none |

### Examples

**Search recent news:**
```bash
uv run --directory {baseDir} python scripts/search.py "AI breakthroughs" --type news --time d --num 5
```

**Search for past week:**
```bash
uv run --directory {baseDir} python scripts/search.py "climate summit" --time w --num 8
```

**Region-specific search:**
```bash
uv run --directory {baseDir} python scripts/search.py "local restaurants" --region us-en --num 5
```

### Result Format

Results are returned as JSON:

```json
{
  "query": "python programming",
  "total_results": 10,
  "results": [
    {
      "title": "Python Programming Language",
      "href": "https://www.python.org/",
      "body": "The official home of the Python Programming Language..."
    },
    ...
  ]
}
```

## Python API

Use the search functions directly in Python code:

```python
import sys
sys.path.insert(0, "{baseDir}/scripts")
from search import search_web, search_news

# Web search
results = search_web("machine learning", max_results=5)
for r in results["results"]:
    print(f"{r['title']}: {r['href']}")

# News search
news = search_news("technology", max_results=5, time_range="d")
```

## Requirements

This skill requires [uv](https://docs.astral.sh/uv/) to be installed. The `ddgs` dependency is automatically managed via the `pyproject.toml` file.

## Troubleshooting

### No Results Returned

- Check your internet connection
- DuckDuckGo may rate-limit excessive queries
- Try a different query or wait a moment before retrying

## Notes

- DuckDuckGo does not require an API key
- Rate limits apply; avoid excessive queries
- Results may vary slightly between calls
- Some regions may have different result availability
