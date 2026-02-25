#!/usr/bin/env python3
"""
DuckDuckGo Web Search Script

Searches the web using DuckDuckGo and returns results in JSON format.
"""

import argparse
import json
import sys
from typing import List, Dict, Any

try:
    from ddgs import DDGS
except ImportError:
    print(json.dumps({
        "error": "ddgs package not installed. Install with: pip install ddgs"
    }))
    sys.exit(1)


def search_web(query: str, max_results: int = 10, region: str = "wt-wt", 
               safesearch: str = "moderate", time_range: str = None) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo.
    
    Args:
        query: The search query
        max_results: Maximum number of results (default: 10)
        region: Region code (default: wt-wt for worldwide)
        safesearch: SafeSearch setting - "on", "moderate", or "off"
        time_range: Time filter - "d" (day), "w" (week), "m" (month), "y" (year)
    
    Returns:
        Dictionary with search results or error
    """
    try:
        ddgs = DDGS()
        results = list(ddgs.text(
            query=query,
            region=region,
            safesearch=safesearch,
            timelimit=time_range,
            max_results=max_results
        ))
            
        return {
            "query": query,
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        return {"error": str(e)}


def search_news(query: str, max_results: int = 10, region: str = "wt-wt",
                safesearch: str = "moderate", time_range: str = None) -> Dict[str, Any]:
    """
    Search for news using DuckDuckGo.
    
    Args:
        query: The search query
        max_results: Maximum number of results (default: 10)
        region: Region code (default: wt-wt for worldwide)
        safesearch: SafeSearch setting
        time_range: Time filter - "d" (day), "w" (week), "m" (month), "y" (year)
    
    Returns:
        Dictionary with news results or error
    """
    try:
        ddgs = DDGS()
        results = list(ddgs.news(
            query=query,
            region=region,
            safesearch=safesearch,
            timelimit=time_range,
            max_results=max_results
        ))
            
        return {
            "query": query,
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Search the web using DuckDuckGo")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--num", "-n", type=int, default=10, 
                       help="Maximum number of results (default: 10)")
    parser.add_argument("--type", "-t", choices=["web", "news"], default="web",
                       help="Type of search: web or news (default: web)")
    parser.add_argument("--region", "-r", default="wt-wt",
                       help="Region code (default: wt-wt for worldwide)")
    parser.add_argument("--safesearch", "-s", choices=["on", "moderate", "off"], 
                       default="moderate", help="SafeSearch setting (default: moderate)")
    parser.add_argument("--time", choices=["d", "w", "m", "y"],
                       help="Time range: d (day), w (week), m (month), y (year)")
    
    args = parser.parse_args()
    
    if args.type == "news":
        result = search_news(
            query=args.query,
            max_results=args.num,
            region=args.region,
            safesearch=args.safesearch,
            time_range=args.time
        )
    else:
        result = search_web(
            query=args.query,
            max_results=args.num,
            region=args.region,
            safesearch=args.safesearch,
            time_range=args.time
        )
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
