#!/usr/bin/env python3
"""
Fixed Trek SKU Database with improved web scraping
"""

# Import the existing database
from trek_sku_database import TREK_SKU_DATABASE, extract_category_from_sku_pattern, extract_category_from_text, extract_series_from_name

import requests
from bs4 import BeautifulSoup
import time
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from functools import lru_cache
from typing import Dict, Optional

# Global cache for web scraping results
_WEB_CACHE = {}
_CACHE_EXPIRY = 3600  # 1 hour cache

def get_trek_product_info_from_web_fixed(sku):
    """FIXED: SKU'yu Trek web sitesinden canlı olarak ara - Now with proper Brotli support"""
    
    # Ensure brotli is available
    try:
        import brotli
    except ImportError:
        print("Warning: brotli not available, compression handling may fail")
    
    sku = str(sku).strip()
    
    # Try direct product URLs first for known patterns
    direct_urls = []
    
    # For W-series SKUs, try common product categories
    if sku.startswith('W'):
        if sku.startswith('W32'):  # Often derailleur hangers
            direct_urls.append(f"https://www.trekbikes.com/de/de_DE/equipment/fahrradkomponenten/fahrradzughalter--ausfallenden/trek-schaltauge-mtb/freizeitr%C3%A4der/p/{sku}/")
        direct_urls.extend([
            f"https://www.trekbikes.com/de/de_DE/equipment/?search={sku}",
            f"https://www.trekbikes.com/us/en_US/equipment/?search={sku}"
        ])
    
    # Search URLs with better targeting
    search_urls = [
        f"https://www.trekbikes.com/de/de_DE/search?q={sku}",
        f"https://www.trekbikes.com/us/en_US/search?q={sku}",
        f"https://www.trekbikes.com/de/de_DE/equipment/?prefn1=itemNumber&prefv1={sku}",
        f"https://www.trekbikes.com/us/en_US/equipment/?prefn1=itemNumber&prefv1={sku}"
    ]
    
    # Combine direct and search URLs
    all_urls = direct_urls + search_urls
    
    # Enhanced headers with German locale preference
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',  # Prefer German
        'Accept-Encoding': 'gzip, deflate, br',  # This should now work with brotli installed
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate', 
        'Sec-Fetch-Site': 'cross-site',
        'Cache-Control': 'max-age=0',
        'DNT': '1'
    }
    
    # Create session with retry strategy
    session = requests.Session()
    retry_strategy = Retry(
        total=2,  # Reduced retries
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    for attempt, url in enumerate(all_urls, 1):
        try:
            print(f"Trek web sitesi aranıyor ({attempt}/{len(all_urls)}): {sku} -> {url}")
            
            # Use session with retry logic
            response = session.get(url, headers=headers, timeout=15)
            
            if response.status_code == 429:
                print(f"Rate limited, waiting 3 seconds...")
                time.sleep(3)
                continue
            elif response.status_code >= 500:
                print(f"Server error {response.status_code}, trying next URL...")
                continue
            elif response.status_code != 200:
                print(f"HTTP {response.status_code}, trying next URL...")
                continue
            
            # Parse the response - should now be properly decoded
            try:
                soup = BeautifulSoup(response.text, 'html.parser')  # Use .text instead of .content
            except Exception as parse_error:
                print(f"Parse error: {parse_error}, trying next URL...")
                continue
            
            # Check for "No Results" pages first
            page_text = soup.get_text().lower()
            
            no_results_indicators = [
                'keine ergebnisse', 'no results', 'no products found', 
                'sorry, we couldn\'t find', 'leider konnten wir keine',
                'did not match any products'
            ]
            
            is_no_results = any(indicator in page_text for indicator in no_results_indicators)
            
            if is_no_results:
                print(f"No results page detected for {sku} at {url}")
                continue
            
            # Check if SKU is mentioned on the page
            sku_found = sku.lower() in page_text
            
            if sku_found:
                print(f"SKU {sku} found on page, extracting product info...")
                
                # Try to extract product information
                product_info = extract_product_info_from_page(soup, sku, url)
                
                if product_info:
                    print(f"✓ Trek web sitesinde bulundu: {product_info['name']}")
                    session.close()
                    return product_info
            
            # For direct product URLs, even if SKU not in text, check if it's a valid product page
            if url in direct_urls:
                title = soup.find('title')
                if title and title.get_text():
                    title_text = title.get_text().strip()
                    # Check if it's a real product page (not 404 or error)
                    if ('trek' in title_text.lower() and 
                        '404' not in title_text.lower() and 
                        'error' not in title_text.lower() and
                        len(title_text) > 10):
                        
                        print(f"Valid product page found: {title_text}")
                        product_info = extract_product_info_from_page(soup, sku, url)
                        if product_info:
                            print(f"✓ Trek product page bulundu: {product_info['name']}")
                            session.close()
                            return product_info
            
            # Small delay between requests
            time.sleep(0.5)
            
        except requests.exceptions.Timeout:
            print(f"Timeout on URL {url}, trying next...")
            continue
        except requests.exceptions.ConnectionError:
            print(f"Connection error on URL {url}, trying next...")
            time.sleep(1)
            continue
        except requests.exceptions.RequestException as e:
            print(f"Request exception for URL {url}: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error for URL {url}: {e}")
            continue
    
    # Clean up session
    session.close()
    
    print(f"Trek web sitesinde {sku} bulunamadı")
    return None


def extract_product_info_from_page(soup, sku, url):
    """Extract product information from a Trek page"""
    import re  # Ensure re is available in this function
    
    # Try to get the page title first
    title_elem = soup.find('title')
    page_title = title_elem.get_text().strip() if title_elem else ""
    
    product_name = None
    
    # Method 1: Use page title if it looks like a product
    if page_title and 'trek' in page_title.lower():
        # Clean up the title
        cleaned_title = page_title.replace(' - Trek Bikes (DE)', '').replace(' - Trek Bikes', '').strip()
        if len(cleaned_title) > 5 and len(cleaned_title) < 100:
            product_name = cleaned_title
    
    # Method 2: Look for common product name selectors
    if not product_name:
        product_selectors = [
            'h1.product-name', 
            'h1[data-testid*="product"]',
            '.product-title',
            '.pdp-product-name',
            'h1.pdp-product-name',
            '.product-info h1',
            '[class*="ProductName"]',
            'h1', 'h2.product'
        ]
        
        for selector in product_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and len(text) > 5 and len(text) < 150:
                    product_name = text
                    break
            if product_name:
                break
    
    # Method 3: Look for SKU and surrounding context
    if not product_name:
        # Find elements containing the SKU
        sku_pattern = re.compile(re.escape(sku), re.I)
        sku_elements = soup.find_all(string=sku_pattern)
        
        for sku_elem in sku_elements:
            # Look at parent elements
            parent = sku_elem.parent if sku_elem.parent else None
            for _ in range(3):  # Go up 3 levels
                if not parent:
                    break
                    
                # Check siblings and nearby elements for product names
                for sibling in parent.find_all(['h1', 'h2', 'h3', 'h4', 'span', 'div']):
                    text = sibling.get_text(strip=True)
                    if (text and 
                        len(text) > 10 and 
                        len(text) < 150 and 
                        sku.lower() not in text.lower() and
                        'trek' in text.lower()):
                        product_name = text
                        break
                        
                if product_name:
                    break
                parent = parent.parent
            
            if product_name:
                break
    
    # Fallback: Use a generic name based on URL patterns
    if not product_name:
        if 'schaltauge' in url.lower():
            product_name = f"Trek Schaltauge/Derailleur Hanger #{sku}"
        elif 'equipment' in url.lower():
            product_name = f"Trek Equipment #{sku}"
        elif 'component' in url.lower():
            product_name = f"Trek Component #{sku}"
        else:
            return None  # Give up if we can't determine a name
    
    # Extract category information
    page_context = soup.get_text()
    category_info = extract_category_from_text(product_name, page_context)
    
    return {
        "name": product_name,
        "category": category_info["category"],
        "product_type": category_info["product_type"],
        "subcategory": category_info["subcategory"],
        "turkish": category_info["turkish"],
        "gtip_description": category_info["gtip_description"],
        "series": extract_series_from_name(product_name),
        "source_url": url
    }


def get_trek_product_info_fixed(sku: str) -> Optional[Dict]:
    """FIXED: Main entry point for Trek product info lookup with improved web scraping"""
    sku = str(sku).strip()
    
    # 1. Local database lookup first
    if sku in TREK_SKU_DATABASE:
        print(f"Database hit: {sku}")
        return TREK_SKU_DATABASE[sku]
    
    # 2. Check web cache before scraping
    cache_key = f"web_{sku}"
    current_time = time.time()
    
    if cache_key in _WEB_CACHE:
        cached_result, timestamp = _WEB_CACHE[cache_key]
        if current_time - timestamp < _CACHE_EXPIRY:
            print(f"Web cache hit: {sku}")
            return cached_result
        else:
            # Remove expired cache entry
            del _WEB_CACHE[cache_key]
    
    # 3. Try web scraping FIRST for unknown SKUs
    print(f"Web scraping with fixed function: {sku}")
    web_result = get_trek_product_info_from_web_fixed(sku)
    
    if web_result:
        # Cache successful result
        _WEB_CACHE[cache_key] = (web_result, current_time)
        return web_result
    
    # 4. Pattern-based categorization if web fails
    pattern_result = extract_category_from_sku_pattern(sku, "")
    if pattern_result:
        print(f"Pattern match after web fail: {sku}")
        _WEB_CACHE[cache_key] = (pattern_result, current_time)
        return pattern_result
    
    # 5. Fallback - generic product info
    print(f"Unidentified SKU: {sku}")
    fallback_result = {
        "name": f"Trek Ürünü #{sku}",
        "category": "Trek Ürünü",
        "product_type": "Trek Ürünü", 
        "subcategory": "Belirlenmemiş",
        "turkish": f"Trek bisiklet ürünü (kategori belirlenemedi)",
        "gtip_description": f"Bisiklet ile ilgili ürün",
        "series": "Trek"
    }
    
    # Cache the fallback result too
    _WEB_CACHE[cache_key] = (fallback_result, current_time)
    return fallback_result


if __name__ == "__main__":
    """Test the fixed functions"""
    print("Testing Fixed Trek SKU Database")
    print("=" * 40)
    
    # Test cases
    test_skus = [
        "W322175",  # Known derailleur hanger
        "581633",   # Known saddle  
        "5329018",  # E-bike from database
        "W5285080", # Bontrager accessory pattern
        "TESTSKU123"  # Invalid for fallback testing
    ]
    
    for sku in test_skus:
        print(f"\n--- Testing {sku} ---")
        result = get_trek_product_info_fixed(sku)
        if result:
            print(f"✓ Name: {result['name']}")
            print(f"  Category: {result['category']}")
            print(f"  Series: {result.get('series', 'N/A')}")
            if 'source_url' in result:
                print(f"  Source: Web scraping")
            else:
                print(f"  Source: Database/Pattern")
        else:
            print("✗ No result found")