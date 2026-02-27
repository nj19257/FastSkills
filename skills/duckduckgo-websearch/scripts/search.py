#!/usr/bin/env python3
"""
DuckDuckGo Web Search Script

Searches the web using DuckDuckGo and returns results in JSON format.
"""

import argparse
import json
import sys
import subprocess
import os
import shutil
from typing import List, Dict, Any

# Try to import ddgs, with fallback instructions
try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False


def get_python_info() -> Dict[str, str]:
    """Get information about the current Python interpreter."""
    return {
        "executable": sys.executable,
        "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform
    }


def find_python_with_ddgs() -> List[str]:
    """
    Find Python interpreters that have ddgs installed.
    Returns a list of Python executable paths.
    """
    candidates = []
    checked_paths = set()
    
    # Common Python executable names to try
    python_names = ["python3", "python", "python3.13", "python3.12", "python3.11", "python3.10"]
    
    for name in python_names:
        path = shutil.which(name)
        if path and path not in checked_paths:
            checked_paths.add(path)
            try:
                result = subprocess.run(
                    [path, "-c", "from ddgs import DDGS; print('OK')"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and "OK" in result.stdout:
                    candidates.append(path)
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass
    
    # Also check common installation paths that might not be in PATH
    common_paths = [
        "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
        "/usr/local/bin/python3",
        "/usr/bin/python3",
        "/opt/homebrew/bin/python3",
        "/opt/homebrew/opt/python@3.13/bin/python3",
        "/opt/homebrew/opt/python@3.12/bin/python3",
        "/opt/homebrew/opt/python@3.11/bin/python3",
        os.path.expanduser("~/.pyenv/shims/python3"),
        os.path.expanduser("~/.local/bin/python3"),
    ]
    
    for path in common_paths:
        if path and os.path.isfile(path) and path not in checked_paths:
            checked_paths.add(path)
            try:
                result = subprocess.run(
                    [path, "-c", "from ddgs import DDGS; print('OK')"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and "OK" in result.stdout:
                    candidates.append(path)
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass
    
    return candidates


def check_ddgs_available() -> Dict[str, Any]:
    """Check if ddgs is available and return error info if not."""
    if DDGS_AVAILABLE:
        return None
    
    # Find alternative Python interpreters with ddgs
    alt_pythons = find_python_with_ddgs()
    python_info = get_python_info()
    
    error_response = {
        "error": f"ddgs package not installed in current Python ({python_info['executable']}).",
        "python_info": python_info,
        "install_commands": [
            f"{python_info['executable']} -m pip install ddgs",
            f"pip install ddgs",
            f"pip3 install ddgs",
            f"uv pip install ddgs"
        ]
    }
    
    if alt_pythons:
        error_response["alternatives"] = alt_pythons
        error_response["suggested_command"] = f"{alt_pythons[0]} {' '.join(sys.argv[1:])}"
    
    return error_response


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
    # Check if ddgs is available
    missing = check_ddgs_available()
    if missing:
        return missing
    
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
    # Check if ddgs is available
    missing = check_ddgs_available()
    if missing:
        return missing
    
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
