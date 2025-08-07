#!/usr/bin/env python3
"""
Debug the actual Trek response content
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_trek_response(url, sku):
    """Debug what we actually get from Trek"""
    print(f"\nDEBUGGING: {url}")
    print("=" * 60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content Length: {len(response.content)}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = soup.get_text().lower()
            
            print(f"\nSKU '{sku}' in page text: {sku.lower() in text_content}")
            
            # Check for "no results" patterns
            no_results_patterns = [
                'no results', 'keine ergebnisse', 'no products found', 
                'sorry, we couldn\'t find', 'leider konnten wir keine',
                'try broadening your search', 'check spelling'
            ]
            
            for pattern in no_results_patterns:
                if pattern in text_content:
                    print(f"Found 'No Results' pattern: '{pattern}'")
            
            # Look for product-related elements
            product_elements = soup.find_all(['h1', 'h2', 'h3', 'h4'], 
                                           class_=re.compile(r'title|name|product|heading', re.I))
            print(f"\nFound {len(product_elements)} potential product title elements")
            
            for i, elem in enumerate(product_elements[:5]):  # Show first 5
                text = elem.get_text(strip=True)
                if text and len(text) > 3:
                    print(f"  {i+1}. {text[:100]}")
            
            # Check if this is a search results page or product page
            search_indicators = soup.find_all(text=re.compile(r'search.*results?|suchergebnisse', re.I))
            product_indicators = soup.find_all(['script'], text=re.compile(r'product.*data|pdp|product.*page', re.I))
            
            print(f"\nSearch page indicators: {len(search_indicators)}")
            print(f"Product page indicators: {len(product_indicators)}")
            
            # Look for specific Trek product schemas or data
            scripts = soup.find_all('script', type='application/ld+json')
            print(f"JSON-LD scripts found: {len(scripts)}")
            
            for script in scripts[:2]:  # Check first 2 scripts
                script_text = script.get_text()
                if 'product' in script_text.lower():
                    print("Found product-related JSON-LD")
                    print(script_text[:200] + "...")
        
        else:
            print(f"Non-200 status code: {response.status_code}")
            print("Response headers:", dict(response.headers))
            
    except Exception as e:
        print(f"Error: {e}")

def test_trek_urls():
    """Test various Trek URLs"""
    test_cases = [
        ("https://www.trekbikes.com/de/de_DE/search?q=W322175", "W322175"),
        ("https://www.trekbikes.com/us/en_US/search?q=581633", "581633"),
        ("https://www.trekbikes.com/de/de_DE/equipment/fahrradkomponenten/fahrradzughalter--ausfallenden/trek-schaltauge-mtb/freizeitr%C3%A4der/p/W322175/", "W322175")
    ]
    
    for url, sku in test_cases:
        debug_trek_response(url, sku)
        print("\n" + "-" * 80 + "\n")

if __name__ == "__main__":
    test_trek_urls()