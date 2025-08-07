#!/usr/bin/env python3
"""
Check the raw HTML content from Trek to see what we're actually getting
"""

import requests

def check_trek_html():
    """Check raw HTML content from Trek"""
    url = "https://www.trekbikes.com/de/de_DE/search?q=W322175"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        print(f"Status: {response.status_code}")
        print(f"Length: {len(response.text)} chars")
        print("\n--- FIRST 1000 CHARACTERS ---")
        print(response.text[:1000])
        print("\n--- SEARCH FOR KEYWORDS ---")
        text_lower = response.text.lower()
        keywords = ['w322175', 'no results', 'keine ergebnisse', 'search', 'product', 'react', 'app', 'javascript']
        
        for keyword in keywords:
            if keyword in text_lower:
                print(f"✓ Found '{keyword}'")
                # Show context
                index = text_lower.find(keyword)
                start = max(0, index - 50)
                end = min(len(response.text), index + 50)
                context = response.text[start:end].replace('\n', ' ')
                print(f"  Context: ...{context}...")
            else:
                print(f"✗ Not found: '{keyword}'")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_trek_html()