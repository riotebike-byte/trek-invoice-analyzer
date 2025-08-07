# Trek SKU veritabanı - bilinen ürünler (gerçek fatura verilerinden)
# Enhanced with caching and performance optimizations

import time
from functools import lru_cache
from typing import Dict, Optional

# Global cache for web scraping results
_WEB_CACHE = {}
_CACHE_EXPIRY = 3600  # 1 hour cache
TREK_SKU_DATABASE = {
    # Fuel EXe Series - Elektrikli Dağ Bisikletleri
    "41476": {
        "name": "Fuel EXe 5",
        "category": "Elektrikli Dağ Bisikleti",
        "product_type": "Elektrikli Bisiklet",
        "subcategory": "Dağ Bisikleti",
        "turkish": "Trek Fuel EXe 5 - Elektrikli Dağ Bisikleti",
        "series": "Fuel EXe"
    },
    "41571": {
        "name": "Fuel EXe 9.8",
        "category": "Elektrikli Dağ Bisikleti",
        "product_type": "Elektrikli Bisiklet",
        "subcategory": "Dağ Bisikleti", 
        "turkish": "Trek Fuel EXe 9.8 - Elektrikli Dağ Bisikleti",
        "series": "Fuel EXe"
    },
    "41526": {
        "name": "Fuel EXe 9.7",
        "category": "Elektrikli Dağ Bisikleti",
        "product_type": "Elektrikli Bisiklet",
        "subcategory": "Dağ Bisikleti",
        "turkish": "Trek Fuel EXe 9.7 - Elektrikli Dağ Bisikleti", 
        "series": "Fuel EXe"
    },
    "41554": {
        "name": "Fuel EXe 8 XT",
        "category": "Elektrikli Dağ Bisikleti",
        "product_type": "Elektrikli Bisiklet",
        "subcategory": "Dağ Bisikleti",
        "turkish": "Trek Fuel EXe 8 XT - Elektrikli Dağ Bisikleti",
        "series": "Fuel EXe"
    },
    "47285": {
        "name": "Fuel EXe 9.9 X0 AXS T-Type",
        "category": "Elektrikli Dağ Bisikleti",
        "product_type": "Elektrikli Bisiklet",
        "subcategory": "Dağ Bisikleti",
        "turkish": "Trek Fuel EXe 9.9 X0 AXS T-Type - Elektrikli Dağ Bisikleti",
        "series": "Fuel EXe"
    },
    "5329018": {
        "name": "Trek Elektrikli Bisiklet",
        "category": "Elektrikli Bisiklet", 
        "product_type": "Elektrikli Bisiklet",
        "subcategory": "Şehir/Hibrit Bisiklet",
        "turkish": "Elektrikli bisiklet, elektrik motorlu, pedal çevirmeli",
        "gtip_description": "Elektrikli bisiklet (elektrik motorlu, pedal çevirmeli)",
        "series": "Elektrikli"
    },
    "5320011": {
        "name": "Trek Bisiklet",
        "category": "Bisiklet",
        "product_type": "Bisiklet", 
        "subcategory": "Genel Bisiklet",
        "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "series": "Bisiklet"
    },
    
    # Aksesuar ve Parçalar - GTİP uyumlu tanımlamalar
    "7001": {
        "name": "Trek İç Lastik",
        "category": "İç Lastik",
        "product_type": "İç Lastik",
        "subcategory": "Bisiklet Parçası",
        "turkish": "Bisiklet iç lastiği, kauçuk",
        "gtip_description": "Bisiklet iç lastiği (kauçuk)",
        "series": "Parça"
    },
    "8001": {
        "name": "Trek Anahtar Takımı",
        "category": "Anahtar Takımı",
        "product_type": "Anahtar Takımı",
        "subcategory": "Bisiklet Aleti",
        "turkish": "El aletleri takımı, bisiklet bakım ve onarım için",
        "gtip_description": "El aletleri takımı (bisiklet bakım için)",
        "series": "Alet"
    },
    "9001": {
        "name": "Trek Bisiklet Kask",
        "category": "Bisiklet Kask",
        "product_type": "Kask",
        "subcategory": "Güvenlik Ekipmanı",
        "turkish": "Koruyucu kask, bisiklet için, plastik/polikarbon",
        "gtip_description": "Koruyucu kask (bisiklet için)",
        "series": "Güvenlik"
    },
    "6001": {
        "name": "Trek Zincir",
        "category": "Zincir",
        "product_type": "Zincir",
        "subcategory": "Bisiklet Parçası",
        "turkish": "Bisiklet zinciri, çelik, güç aktarım parçası",
        "gtip_description": "Bisiklet zinciri (çelik)",
        "series": "Parça"
    },
    "5001": {
        "name": "Trek Fren Balata",
        "category": "Fren Balata",
        "product_type": "Fren Balata",
        "subcategory": "Bisiklet Parçası",
        "turkish": "Bisiklet fren balata, fren sistemi parçası",
        "gtip_description": "Bisiklet fren balata",
        "series": "Parça"
    },
    "5283888": {
        "name": "Bontrager Blendr Sattel Zubehörhalterung",
        "category": "Bisiklet Aksesuarı",
        "product_type": "Bisiklet Aksesuarı",
        "subcategory": "Aksesuar Tutucusu",
        "turkish": "Bisiklet aksesuar tutucusu, plastik/metal, sele altı montaj",
        "gtip_description": "Bisiklet aksesuar tutucusu",
        "series": "Bontrager"
    },
    "5328107": {
        "name": "Trek Bisiklet Kadrosu",
        "category": "Bisiklet Kadrosu",
        "product_type": "Bisiklet Kadrosu",
        "subcategory": "Çerçeve",
        "turkish": "Bisiklet kadrosu/çerçevesi, alüminyum/karbon",
        "gtip_description": "Bisiklet kadrosu (çerçeve)",
        "series": "Trek"
    },
    
    # Fatura verilerinden ek SKU'lar
    "5328106": {
        "name": "Trek Bisiklet Kadrosu",
        "category": "Bisiklet Kadrosu",
        "product_type": "Bisiklet Kadrosu",
        "subcategory": "Çerçeve",
        "turkish": "Bisiklet kadrosu/çerçevesi",
        "gtip_description": "Bisiklet kadrosu (çerçeve)",
        "series": "Trek"
    },
    "5323998": {
        "name": "Trek Bisiklet",
        "category": "Bisiklet",
        "product_type": "Bisiklet",
        "subcategory": "Dağ Bisikleti",
        "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "series": "Trek"
    },
    "5320014": {
        "name": "Trek Bisiklet",
        "category": "Bisiklet",
        "product_type": "Bisiklet",
        "subcategory": "Genel Bisiklet",
        "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "series": "Trek"
    },
    "5320013": {
        "name": "Trek Bisiklet",
        "category": "Bisiklet", 
        "product_type": "Bisiklet",
        "subcategory": "Genel Bisiklet",
        "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "series": "Trek"
    },
    "5320313": {
        "name": "Trek Bisiklet",
        "category": "Bisiklet",
        "product_type": "Bisiklet", 
        "subcategory": "Genel Bisiklet",
        "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "series": "Trek"
    },
    "5320733": {
        "name": "Trek Bisiklet",
        "category": "Bisiklet",
        "product_type": "Bisiklet",
        "subcategory": "Genel Bisiklet", 
        "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "series": "Trek"
    },
    "5323525": {
        "name": "Trek Bisiklet",
        "category": "Bisiklet",
        "product_type": "Bisiklet",
        "subcategory": "Dağ Bisikleti",
        "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)", 
        "series": "Trek"
    },
    "5323529": {
        "name": "Trek Bisiklet",
        "category": "Bisiklet",
        "product_type": "Bisiklet",
        "subcategory": "Dağ Bisikleti",
        "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "series": "Trek"
    },
    "5323524": {
        "name": "Trek Bisiklet", 
        "category": "Bisiklet",
        "product_type": "Bisiklet",
        "subcategory": "Dağ Bisikleti",
        "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "series": "Trek"
    },
    "5323523": {
        "name": "Trek Bisiklet",
        "category": "Bisiklet",
        "product_type": "Bisiklet",
        "subcategory": "Dağ Bisikleti",
        "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "series": "Trek"
    },
    "5336210": {
        "name": "Trek Özel Bisiklet",
        "category": "Trek Özel Ürün", 
        "product_type": "Bisiklet",
        "subcategory": "Özel Seri",
        "turkish": "Trek özel seri bisiklet",
        "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
        "series": "Trek"
    },
    
    # Bontrager Aksesuarları - W serisi
    "W5271067": {
        "name": "Bontrager Aksesuar",
        "category": "Bisiklet Aksesuarı",
        "product_type": "Bisiklet Aksesuarı",
        "subcategory": "Bontrager Aksesuar",
        "turkish": "Bontrager marka bisiklet aksesuarı",
        "gtip_description": "Bisiklet aksesuarı",
        "series": "Bontrager"
    },
    "W5256074": {
        "name": "Bontrager Aksesuar",
        "category": "Bisiklet Aksesuarı",
        "product_type": "Bisiklet Aksesuarı", 
        "subcategory": "Bontrager Aksesuar",
        "turkish": "Bontrager marka bisiklet aksesuarı",
        "gtip_description": "Bisiklet aksesuarı",
        "series": "Bontrager"
    },
    "W5284217": {
        "name": "Bontrager Aksesuar",
        "category": "Bisiklet Aksesuarı",
        "product_type": "Bisiklet Aksesuarı",
        "subcategory": "Bontrager Aksesuar", 
        "turkish": "Bontrager marka bisiklet aksesuarı",
        "gtip_description": "Bisiklet aksesuarı",
        "series": "Bontrager"
    },
    "W524900": {
        "name": "Bontrager Parça",
        "category": "Bisiklet Parçası",
        "product_type": "Bisiklet Parçası",
        "subcategory": "Bontrager Parça",
        "turkish": "Bontrager marka bisiklet parçası",
        "gtip_description": "Bisiklet yedek parçası",
        "series": "Bontrager"
    },
    "W524901": {
        "name": "Bontrager Parça",
        "category": "Bisiklet Parçası", 
        "product_type": "Bisiklet Parçası",
        "subcategory": "Bontrager Parça",
        "turkish": "Bontrager marka bisiklet parçası",
        "gtip_description": "Bisiklet yedek parçası",
        "series": "Bontrager"
    },
    
    # Bisiklet Parçaları - 52xx, 56xx, 58xx serileri
    "5298292": {
        "name": "Trek Bisiklet Işığı",
        "category": "Bisiklet Aydınlatması",
        "product_type": "Bisiklet Işığı",
        "subcategory": "Aydınlatma",
        "turkish": "Bisiklet ışığı/aydınlatma sistemi",
        "gtip_description": "Bisiklet ışığı (aydınlatma ekipmanı)",
        "series": "Trek"
    },
    "5274583": {
        "name": "Trek Bisiklet Parçası",
        "category": "Bisiklet Parçası",
        "product_type": "Bisiklet Parçası", 
        "subcategory": "Yedek Parça",
        "turkish": "Bisiklet yedek parçası/bileşeni",
        "gtip_description": "Bisiklet yedek parçası",
        "series": "Trek"
    },
    "5266373": {
        "name": "Trek Bisiklet Parçası",
        "category": "Bisiklet Parçası",
        "product_type": "Bisiklet Parçası",
        "subcategory": "Yedek Parça",
        "turkish": "Bisiklet yedek parçası/bileşeni",
        "gtip_description": "Bisiklet yedek parçası", 
        "series": "Trek"
    },
    
    # 6 haneli parça kodları
    "601257": {
        "name": "Trek/Bontrager Parça",
        "category": "Bisiklet Parçası",
        "product_type": "Bisiklet Parçası",
        "subcategory": "Yedek Parça",
        "turkish": "Bisiklet yedek parçası",
        "gtip_description": "Bisiklet yedek parçası",
        "series": "Trek"
    },
    "563711": {
        "name": "Trek/Bontrager Parça",
        "category": "Bisiklet Parçası",
        "product_type": "Bisiklet Parçası",
        "subcategory": "Yedek Parça",
        "turkish": "Bisiklet yedek parçası",
        "gtip_description": "Bisiklet yedek parçası",
        "series": "Trek"
    },
    "581633": {
        "name": "Bontrager Aeolus Comp Sele 145mm Siyah",
        "category": "Bisiklet Selesi",
        "product_type": "Bisiklet Selesi",
        "subcategory": "Sele",
        "turkish": "Bisiklet selesi, 145mm genişlik, siyah renk",
        "gtip_description": "Bisiklet selesi (oturma yeri)",
        "series": "Bontrager"
    },
    "W322175": {
        "name": "Trek Schaltauge MTB - Vites Kulağı",
        "category": "Bisiklet Parçası",
        "product_type": "Vites Kulağı",
        "subcategory": "MTB Parçası",
        "turkish": "Trek dağ bisikleti vites kulağı (schaltauge)",
        "gtip_description": "Bisiklet vites sistemi parçası",
        "series": "Trek"
    },
    "W5271424": {
        "name": "Trek Universal Derailleur Hanger - Vites Kulağı",
        "category": "Bisiklet Parçası",
        "product_type": "Vites Kulağı",
        "subcategory": "Derailleur Hanger",
        "turkish": "Trek universal vites kulağı (derailleur hanger)",
        "gtip_description": "Bisiklet vites sistemi parçası",
        "series": "Trek"
    }
}

# Pattern sistemi kaldırıldı - Sadece spesifik SKU tanımları kullanılıyor
# Her SKU'nun kendi özel tanımı var

def get_product_info_from_openai(sku, product_name=None):
    """OpenAI ile Trek ürün bilgisi analizi"""
    try:
        import openai
        
        # API key environment variable'dan al
        import os
        if not os.environ.get('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable gerekli!")
        
        # Prompt hazırla - fatura ismi ile daha detaylı analiz
        prompt = f"""
        Trek bisiklet SKU analizi yapın: {sku}
        {f'Faturadaki ürün ismi: "{product_name}"' if product_name else ''}
        
        ÖNEMLI: Faturadaki ürün ismi varsa, bu isme öncelik verin ve bu bilgiyi kullanarak daha doğru analiz yapın.
        
        Bu SKU için aşağıdaki bilgileri JSON formatında verin:
        {{
            "name": "Detaylı ürün adı (fatura ismini dikkate al)",
            "category": "Ana kategori", 
            "product_type": "Spesifik ürün tipi",
            "subcategory": "Alt kategori",
            "turkish": "Türkçe açıklama (fatura ismini çevir)",
            "gtip_description": "GTİP uyumlu gümrük tanımı",
            "series": "Trek/Bontrager"
        }}
        
        Analiz kuralları:
        - Faturadaki ismi varsa önce onu analiz edin ve Türkçe'ye çevirin
        - SKU pattern'ini de kullanın: W=aksesuar/parça, 5rakam=bisiklet, 532xxx=kadro
        - Türkçe açıklama GTİP (Gümrük Tarife İstatistik) uyumlu olmalı
        - Bisiklet parçalarını spesifik isimle tanımlayın (örn: "fren balata" değil "Shimano fren balata seti")
        """
        
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        # JSON parse et
        import json
        result_text = response.choices[0].message.content
        # JSON kısmını bul
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = result_text[json_start:json_end]
            result = json.loads(json_str)
            print(f"🤖 OpenAI ile analiz edildi: {sku}")
            return result
        
    except Exception as e:
        print(f"❌ OpenAI hatası: {e}")
    
    return None

def get_trek_product_info_from_web(sku, username=None, password=None):
    """SKU'yu Trek web sitesinden canlı olarak ara - B2B login destekli"""
    import requests
    from bs4 import BeautifulSoup
    import time
    import re
    import getpass
    import os
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    sku = str(sku).strip()
    
    # Session oluştur
    session = requests.Session()
    
    # B2B LOGIN - Eğer credentials verilmişse
    b2b_logged_in = False
    if username and password:
        print(f"🔐 Trek B2B'ye giriş yapılıyor...")
        try:
            # Farklı B2B login URL'leri dene
            login_urls = [
                "https://www.trekbikes.com/b2b/login",
                "https://b2b.trekbikes.com/login",
                "https://www.trekbikes.com/login",
                "https://dealer.trekbikes.com/login"
            ]
            
            for login_url in login_urls:
                print(f"  Denenen URL: {login_url}")
                try:
                    login_page = session.get(login_url, timeout=10)
                    if login_page.status_code == 200:
                        print(f"  ✅ Login sayfası bulundu: {login_url}")
                        
                        # Farklı form field kombinasyonları dene
                        login_attempts = [
                            {'email': username, 'password': password},
                            {'username': username, 'password': password},
                            {'dwfrm_login_username': username, 'dwfrm_login_password': password},
                            {'j_username': username, 'j_password': password},
                        ]
                        
                        for login_data in login_attempts:
                            login_response = session.post(login_url, data=login_data, timeout=10)
                            
                            # Başarı kontrol
                            success_indicators = ["dashboard", "welcome", "home", "profile", "b2b"]
                            if any(indicator in login_response.url.lower() for indicator in success_indicators):
                                print("✅ B2B girişi başarılı!")
                                b2b_logged_in = True
                                break
                        
                        if b2b_logged_in:
                            break
                            
                except Exception as e:
                    print(f"  ❌ {login_url} başarısız: {e}")
                    continue
            
            if not b2b_logged_in:
                print("❌ Tüm B2B giriş denemeleri başarısız, public siteden devam ediliyor...")
        except Exception as e:
            print(f"❌ B2B login hatası: {e}")
    
    # SEARCH URL'LERİ - B2B dahil
    search_urls = []
    
    # 1. Optimized country priority (most successful first)
    countries = [
        ('de', 'de_DE', 'German'),    # En başarılı
        ('us', 'en_US', 'US English'), # İkinci en başarılı
        ('gb', 'en_GB', 'UK English'), # Üçüncü seçenek
        # ('fr', 'fr_FR', 'French'),     # Performance için kısaltıldı
        # ('nl', 'nl_NL', 'Dutch'),
        # ('tr', 'tr_TR', 'Turkish'),
        # ('it', 'it_IT', 'Italian'),
        # ('es', 'es_ES', 'Spanish')
    ]
    
    # GÜNCEL strateji - B2B öncelikli!
    if sku.startswith('W'):
        search_urls = []
        
        # B2B sitesi ÖNCE (login varsa)
        if b2b_logged_in:
            search_urls.extend([
                f"https://www.trekbikes.com/b2b/international/en_IN_TL/equipment/cycling-components/bike-hangers-and-dropouts/trek-universal-derailleur-hanger/p/{sku}/",
                f"https://www.trekbikes.com/b2b/international/en_US/equipment/cycling-components/bike-hangers-and-dropouts/p/{sku}/",
                f"https://www.trekbikes.com/b2b/international/en_GB/equipment/cycling-components/p/{sku}/",
                f"https://www.trekbikes.com/b2b/search?q={sku}",
            ])
        
        # Public siteler
        search_urls.extend([
            f"https://www.trekbikes.com/de/de_DE/equipment/fahrradkomponenten/fahrradzughalter--ausfallenden/trek-schaltauge-mtb/freizeitr%C3%A4der/p/{sku}/",
            f"https://www.trekbikes.com/us/en_US/equipment/bike-accessories/components/p/{sku}/",
        ])
    elif sku.isdigit():
        search_urls = [
            f"https://www.trekbikes.com/de/de_DE/bikes/{sku}/",
            f"https://www.trekbikes.com/us/en_US/bikes/{sku}/",
            f"https://www.trekbikes.com/de/de_DE/search?q={sku}",
        ]
    else:
        search_urls = [
            f"https://www.trekbikes.com/de/de_DE/search?q={sku}",
            f"https://www.trekbikes.com/us/en_US/search?q={sku}",
        ]
    
    # Enhanced headers to reduce blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
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
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    for attempt, url in enumerate(search_urls, 1):
        try:
            print(f"Trek web sitesi aranıyor (Deneme {attempt}/3): {sku}")
            
            # Use session with retry logic (B2B login korunur)
            response = session.get(url, headers=headers, timeout=5)  # HIZLI: 5 saniye
            
            if response.status_code == 429:
                print(f"Rate limited, waiting 2 seconds...")
                time.sleep(2)  # HIZLI: 2 saniye bekle
                continue
            elif response.status_code >= 500:
                print(f"Server error {response.status_code}, trying next URL...")
                continue
            elif response.status_code != 200:
                print(f"HTTP {response.status_code} - trying next URL...")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Sayfanın tamamını kontrol et - SKU herhangi bir yerde olabilir
            page_text = soup.get_text().lower()
            if sku.lower() in page_text:
                
                # SKU bulunan bölümü daha detaylı ara
                all_elements = soup.find_all(text=re.compile(re.escape(sku), re.I))
                
                for element in all_elements:
                    parent = element.parent if element.parent else None
                    if not parent:
                        continue
                        
                    # Üst elementlerde ürün bilgisi ara
                    for level in range(5):  # 5 seviye yukarı çık
                        if not parent:
                            break
                            
                        # Ürün adı ara
                        title_candidates = parent.find_all(['h1', 'h2', 'h3', 'h4', 'a', 'span'], 
                                                         class_=re.compile(r'title|name|product|heading', re.I))
                        
                        for title_elem in title_candidates:
                            if title_elem and title_elem.get_text(strip=True):
                                product_name = title_elem.get_text(strip=True)
                                
                                # Ürün adının geçerli olup olmadığını kontrol et
                                if len(product_name) > 5 and len(product_name) < 200:
                                    category_info = extract_category_from_text(product_name, parent.get_text())
                                    
                                    print(f"Trek web sitesinde bulundu: {product_name}")
                                    
                                    return {
                                        "name": product_name,
                                        "category": category_info["category"],
                                        "product_type": category_info["product_type"],
                                        "subcategory": category_info["subcategory"],
                                        "turkish": category_info["turkish"],
                                        "gtip_description": category_info["gtip_description"],
                                        "series": extract_series_from_name(product_name)
                                    }
                        
                        parent = parent.parent
                
                # Eğer spesifik ürün bulunamazsa ama SKU varsa, genel kategori belirle
                category_info = extract_category_from_sku_pattern(sku, page_text)
                if category_info:
                    print(f"Trek web sitesinde SKU pattern'i ile bulundu: {sku}")
                    return category_info
            
            # Exponential backoff between requests
            if attempt < len(search_urls):
                time.sleep(0.5)  # HIZLI: 0.5 saniye bekle
            
        except requests.exceptions.Timeout:
            print(f"Timeout on URL {url}, trying next...")
            continue
        except requests.exceptions.ConnectionError:
            print(f"Connection error on URL {url}, trying next...")
            time.sleep(0.5)  # HIZLI: 0.5 saniye bekle
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

def extract_category_from_sku_pattern(sku, page_context):
    """SKU pattern'inden kategori tahmin et - Gerçek fatura verilerine dayalı"""
    sku_str = str(sku)
    
    # Gerçek faturalarda görülen pattern'ler
    
    # 532xxxx serisi - Bisikletler (5320011 bilinen normal bisiklet)
    if sku_str.startswith('532') and len(sku_str) == 7:
        # Elektrikli bisiklet kontrolü (5329xxx genelde elektrikli)
        if sku_str.startswith('5329') or 'electric' in page_context or 'e-bike' in page_context:
            return {
                "name": f"Trek Elektrikli Bisiklet #{sku}",
                "category": "Elektrikli Bisiklet",
                "product_type": "Elektrikli Bisiklet",
                "subcategory": "Elektrikli Bisiklet",
                "turkish": "Elektrikli bisiklet, elektrik motorlu, pedal çevirmeli",
                "gtip_description": "Elektrikli bisiklet (elektrik motorlu, pedal çevirmeli)",
                "series": "Trek"
            }
        else:
            return {
                "name": f"Trek Bisiklet #{sku}",
                "category": "Bisiklet",
                "product_type": "Bisiklet", 
                "subcategory": "Genel Bisiklet",
                "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
                "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)",
                "series": "Trek"
            }
    
    # 531xxxx serisi - Bisiklet parçaları/kadroları
    elif sku_str.startswith('531') and len(sku_str) == 7:
        return {
            "name": f"Trek Bisiklet Parçası #{sku}",
            "category": "Bisiklet Parçası",
            "product_type": "Bisiklet Parçası",
            "subcategory": "Yedek Parça",
            "turkish": "Bisiklet yedek parçası/bileşeni",
            "gtip_description": "Bisiklet yedek parçası",
            "series": "Trek"
        }
    
    # 528xxxx serisi - Aksesuarlar (5283888 bilinen aksesuar tutucusu)
    elif sku_str.startswith('528') and len(sku_str) == 7:
        return {
            "name": f"Trek Bisiklet Aksesuarı #{sku}",
            "category": "Bisiklet Aksesuarı",
            "product_type": "Bisiklet Aksesuarı",
            "subcategory": "Aksesuar Tutucusu",
            "turkish": "Bisiklet aksesuarı, montaj parçası",
            "gtip_description": "Bisiklet aksesuarı",
            "series": "Bontrager"
        }
    
    # 527xxxx serisi - Bisiklet parçaları
    elif sku_str.startswith('527') and len(sku_str) == 7:
        return {
            "name": f"Trek Bisiklet Parçası #{sku}",
            "category": "Bisiklet Parçası", 
            "product_type": "Bisiklet Parçası",
            "subcategory": "Yedek Parça",
            "turkish": "Bisiklet yedek parçası/bileşeni",
            "gtip_description": "Bisiklet yedek parçası",
            "series": "Trek"
        }
    
    # 526xxxx serisi - Bisiklet parçaları
    elif sku_str.startswith('526') and len(sku_str) == 7:
        return {
            "name": f"Trek Bisiklet Parçası #{sku}",
            "category": "Bisiklet Parçası",
            "product_type": "Bisiklet Parçası", 
            "subcategory": "Yedek Parça",
            "turkish": "Bisiklet yedek parçası/bileşeni",
            "gtip_description": "Bisiklet yedek parçası",
            "series": "Trek"
        }
    
    # 533xxxx serisi - Özel kategoriler
    elif sku_str.startswith('533') and len(sku_str) == 7:
        return {
            "name": f"Trek Özel Ürün #{sku}",
            "category": "Trek Özel Ürün",
            "product_type": "Trek Özel Ürün",
            "subcategory": "Özel Seri",
            "turkish": "Trek özel seri bisiklet ürünü",
            "gtip_description": "Bisiklet ile ilgili özel ürün",
            "series": "Trek"
        }
    
    # W5xxxxxx serisi - Bontrager aksesuarları (W5285080, W5271067, W5256074, W5284217 örnekleri)
    elif sku_str.startswith('W5') and len(sku_str) >= 7:
        return {
            "name": f"Bontrager Aksesuar #{sku}",
            "category": "Bisiklet Aksesuarı",
            "product_type": "Bisiklet Aksesuarı",
            "subcategory": "Bontrager Aksesuar",
            "turkish": "Bontrager marka bisiklet aksesuarı",
            "gtip_description": "Bisiklet aksesuarı",
            "series": "Bontrager"
        }
    
    # W524xxx serisi - Bontrager parçaları (W524900, W524901)
    elif sku_str.startswith('W524') and len(sku_str) >= 6:
        return {
            "name": f"Bontrager Parça #{sku}",
            "category": "Bisiklet Parçası",
            "product_type": "Bisiklet Parçası",
            "subcategory": "Bontrager Parça",
            "turkish": "Bontrager marka bisiklet parçası",
            "gtip_description": "Bisiklet yedek parçası",
            "series": "Bontrager"
        }
    
    # W32xxxx serisi - Trek MTB parçaları (W322175 vites kulağı gibi)
    elif sku_str.startswith('W32') and len(sku_str) >= 6:
        # Special handling for W322175 (already in database)
        if sku_str == 'W322175':
            return TREK_SKU_DATABASE.get('W322175')
        return {
            "name": f"Trek MTB Parçası #{sku}",
            "category": "Bisiklet Parçası",
            "product_type": "Bisiklet Parçası",
            "subcategory": "MTB Parçası",
            "turkish": "Trek dağ bisikleti yedek parçası",
            "gtip_description": "Bisiklet yedek parçası (dağ bisikleti için)",
            "series": "Trek"
        }
    
    # W58xxxx serisi - Bontrager aksesuarları (W583413, W584134)
    elif sku_str.startswith('W58') and len(sku_str) >= 6:
        return {
            "name": f"Bontrager Aksesuar #{sku}",
            "category": "Bisiklet Aksesuarı",
            "product_type": "Bisiklet Aksesuarı",
            "subcategory": "Bontrager Aksesuar",
            "turkish": "Bontrager marka bisiklet aksesuarı",
            "gtip_description": "Bisiklet aksesuarı",
            "series": "Bontrager"
        }
    
    # W3xxxxx serisi - Trek parçaları (W322175 vites kulağı, W301234 gibi)
    elif sku_str.startswith('W3') and len(sku_str) >= 6:
        # Priority check for specific SKUs in database
        if sku in TREK_SKU_DATABASE:
            return TREK_SKU_DATABASE[sku]
        return {
            "name": f"Trek Parça #{sku}",
            "category": "Bisiklet Parçası",
            "product_type": "Bisiklet Parçası",
            "subcategory": "Trek Parça",
            "turkish": "Trek bisiklet yedek parçası",
            "gtip_description": "Bisiklet yedek parçası",
            "series": "Trek"
        }
    
    # W4xxxxx serisi - Trek parçaları 
    elif sku_str.startswith('W4') and len(sku_str) >= 6:
        return {
            "name": f"Trek Parça #{sku}",
            "category": "Bisiklet Parçası",
            "product_type": "Bisiklet Parçası",
            "subcategory": "Trek Parça",
            "turkish": "Trek bisiklet yedek parçası",
            "gtip_description": "Bisiklet yedek parçası",
            "series": "Trek"
        }
    
    # W1xxxxx, W2xxxxx serileri - Trek/Bontrager parçaları
    elif sku_str.startswith(('W1', 'W2')) and len(sku_str) >= 6:
        return {
            "name": f"Trek/Bontrager Parça #{sku}",
            "category": "Bisiklet Parçası",
            "product_type": "Bisiklet Parçası",
            "subcategory": "Parça",
            "turkish": "Trek/Bontrager bisiklet parçası",
            "gtip_description": "Bisiklet yedek parçası",
            "series": "Trek"
        }
    
    # W6xxxxx, W7xxxxx, W8xxxxx, W9xxxxx serileri - Trek/Bontrager parçaları
    elif sku_str.startswith(('W6', 'W7', 'W8', 'W9')) and len(sku_str) >= 6:
        return {
            "name": f"Trek/Bontrager Parça #{sku}",
            "category": "Bisiklet Parçası",
            "product_type": "Bisiklet Parçası",
            "subcategory": "Parça",
            "turkish": "Trek/Bontrager bisiklet parçası",
            "gtip_description": "Bisiklet yedek parçası",
            "series": "Trek"
        }
    
    # 6 haneli rakamlar (601257, 563711, 581633 gibi) - Parçalar
    elif sku_str.isdigit() and len(sku_str) == 6:
        return {
            "name": f"Trek/Bontrager Parça #{sku}",
            "category": "Bisiklet Parçası",
            "product_type": "Bisiklet Parçası",
            "subcategory": "Yedek Parça", 
            "turkish": "Bisiklet yedek parçası",
            "gtip_description": "Bisiklet yedek parçası",
            "series": "Trek"
        }
    
    # 5 haneli kodlar (41xxx, 47xxx serileri - bilinen elektrikli bisikletler)
    elif sku_str.isdigit() and len(sku_str) == 5:
        if sku_str.startswith('41') or sku_str.startswith('47'):
            return {
                "name": f"Trek Fuel EXe Elektrikli Bisiklet #{sku}",
                "category": "Elektrikli Dağ Bisikleti",
                "product_type": "Elektrikli Bisiklet",
                "subcategory": "Elektrikli Dağ Bisikleti",
                "turkish": "Trek Fuel EXe elektrikli dağ bisikleti",
                "gtip_description": "Elektrikli bisiklet (elektrik motorlu, pedal çevirmeli)",
                "series": "Fuel EXe"
            }
        else:
            return {
                "name": f"Trek Özel Ürün #{sku}",
                "category": "Trek Ürünü",
                "product_type": "Trek Ürünü",
                "subcategory": "Özel Kod",
                "turkish": "Trek bisiklet ürünü",
                "gtip_description": "Bisiklet ile ilgili ürün",
                "series": "Trek"
            }
    
    return None

def extract_category_from_text(product_name, full_text):
    """Ürün adı ve metinden kategori bilgisini çıkar"""
    product_name_lower = product_name.lower()
    full_text_lower = full_text.lower()
    
    # Aydınlatma kontrolü
    if any(keyword in product_name_lower or keyword in full_text_lower for keyword in [
        'lit', 'light', 'lamp', 'led', 'beam', 'aydınlatma', 'ışık'
    ]):
        return {
            "category": "Bisiklet Aydınlatması",
            "product_type": "Bisiklet Işığı", 
            "subcategory": "Aydınlatma",
            "turkish": "Bisiklet ışığı/aydınlatma sistemi",
            "gtip_description": "Bisiklet ışığı (aydınlatma ekipmanı)"
        }
    
    # Kask kontrolü
    elif any(keyword in product_name_lower for keyword in [
        'helmet', 'helm', 'kask', 'hlmt'
    ]):
        return {
            "category": "Bisiklet Kask",
            "product_type": "Kask",
            "subcategory": "Güvenlik Ekipmanı",
            "turkish": "Koruyucu kask, bisiklet için",
            "gtip_description": "Koruyucu kask (bisiklet için)"
        }
    
    # Lastik/Tekerlek kontrolü
    elif any(keyword in product_name_lower for keyword in [
        'tire', 'tyre', 'wheel', 'rim', 'hub', 'spoke', 'lastik', 'tekerlek'
    ]):
        return {
            "category": "Bisiklet Tekerlek/Lastik",
            "product_type": "Bisiklet Tekerlek",
            "subcategory": "Tekerlek Sistemi", 
            "turkish": "Bisiklet tekerleği/lastiği",
            "gtip_description": "Bisiklet tekerleği veya lastiği"
        }
    
    # Fren sistemi kontrolü  
    elif any(keyword in product_name_lower for keyword in [
        'brake', 'brk', 'disc', 'pad', 'caliper', 'fren', 'balata'
    ]):
        return {
            "category": "Bisiklet Fren Sistemi",
            "product_type": "Bisiklet Fren",
            "subcategory": "Fren Sistemi",
            "turkish": "Bisiklet fren sistemi/balata",
            "gtip_description": "Bisiklet fren sistemi"
        }
    
    # Vites/Şanzıman kontrolü
    elif any(keyword in product_name_lower for keyword in [
        'gear', 'shift', 'derailleur', 'cassette', 'chain', 'cog', 'vites', 'zincir'
    ]):
        return {
            "category": "Bisiklet Vites Sistemi", 
            "product_type": "Bisiklet Vites",
            "subcategory": "Vites Sistemi",
            "turkish": "Bisiklet vites sistemi/zincir",
            "gtip_description": "Bisiklet vites sistemi"
        }
    
    # Sele/Oturma kontrolü
    elif any(keyword in product_name_lower for keyword in [
        'saddle', 'seat', 'post', 'clamp', 'sele', 'oturma'
    ]):
        return {
            "category": "Bisiklet Selesi",
            "product_type": "Bisiklet Selesi",
            "subcategory": "Sele Sistemi",
            "turkish": "Bisiklet selesi/oturma yeri",
            "gtip_description": "Bisiklet selesi"
        }
    
    # Elektrikli bisiklet kontrolü
    if any(keyword in product_name_lower or keyword in full_text_lower for keyword in [
        'e-bike', 'electric', 'elektrik', 'exe', 'powerfly', 'verve+', 'allant+', 'domane+', 'rail'
    ]):
        return {
            "category": "Elektrikli Bisiklet",
            "product_type": "Elektrikli Bisiklet",
            "subcategory": determine_bike_subcategory(product_name),
            "turkish": "Elektrikli bisiklet, elektrik motorlu, pedal çevirmeli",
            "gtip_description": "Elektrikli bisiklet (elektrik motorlu, pedal çevirmeli)"
        }
    
    # Normal bisiklet kontrolü  
    elif any(keyword in product_name_lower for keyword in [
        'bike', 'bisiklet', 'domane', 'madone', 'emonda', 'checkpoint', 'crockett', 'boone'
    ]) and 'frame' not in product_name_lower:
        return {
            "category": "Bisiklet",
            "product_type": "Bisiklet",
            "subcategory": determine_bike_subcategory(product_name),
            "turkish": "Bisiklet (motor olmayan, pedal çevirmeli)",
            "gtip_description": "Bisiklet (motor olmayan, pedal çevirmeli)"
        }
    
    # Kadro/Çerçeve
    elif any(keyword in product_name_lower for keyword in ['frame', 'frameset', 'kadro', 'çerçeve']):
        return {
            "category": "Bisiklet Kadrosu",
            "product_type": "Bisiklet Kadrosu", 
            "subcategory": "Çerçeve",
            "turkish": "Bisiklet kadrosu/çerçevesi, alüminyum/karbon",
            "gtip_description": "Bisiklet kadrosu (çerçeve)"
        }
    
    # Aksesuar kontrolü
    elif any(keyword in product_name_lower for keyword in [
        'mount', 'holder', 'bracket', 'adapter', 'blendr', 'tutuc', 'aksesuar'
    ]):
        return {
            "category": "Bisiklet Aksesuarı",
            "product_type": "Bisiklet Aksesuarı",
            "subcategory": "Aksesuar Tutucusu",
            "turkish": "Bisiklet aksesuar tutucusu, plastik/metal",
            "gtip_description": "Bisiklet aksesuar tutucusu"
        }
    
    # Parça kontrolü
    elif any(keyword in product_name_lower for keyword in [
        'chain', 'brake', 'gear', 'derailleur', 'cassette', 'tire', 'tube', 'zincir', 'fren'
    ]):
        return {
            "category": "Bisiklet Parçası",
            "product_type": "Bisiklet Parçası",
            "subcategory": "Yedek Parça",
            "turkish": "Bisiklet yedek parçası",
            "gtip_description": "Bisiklet yedek parçası"
        }
    
    # Genel Trek ürünü
    else:
        return {
            "category": "Trek Ürünü",
            "product_type": "Trek Ürünü", 
            "subcategory": "Belirlenmemiş",
            "turkish": "Trek bisiklet ürünü",
            "gtip_description": "Bisiklet ile ilgili ürün"
        }

def determine_bike_subcategory(product_name):
    """Bisiklet alt kategorisini belirle"""
    name_lower = product_name.lower()
    
    if any(keyword in name_lower for keyword in ['mountain', 'mtb', 'fuel', 'remedy', 'slash']):
        return "Dağ Bisikleti"
    elif any(keyword in name_lower for keyword in ['road', 'domane', 'madone', 'emonda']):
        return "Yol Bisikleti"  
    elif any(keyword in name_lower for keyword in ['hybrid', 'fx', 'verve', 'dual']):
        return "Hibrit Bisiklet"
    elif any(keyword in name_lower for keyword in ['city', 'urban', 'district']):
        return "Şehir Bisikleti"
    else:
        return "Genel Bisiklet"

def extract_series_from_name(product_name):
    """Ürün adından seri bilgisini çıkar"""
    # Bilinen Trek serileri
    series_patterns = [
        r'fuel\s*exe?', r'domane', r'madone', r'emonda', r'fx', r'verve', 
        r'remedy', r'slash', r'powerfly', r'rail', r'allant', r'checkpoint'
    ]
    
    for pattern in series_patterns:
        match = re.search(pattern, product_name, re.IGNORECASE)
        if match:
            return match.group().title()
    
    return "Trek"

@lru_cache(maxsize=1000)
def get_trek_product_info_cached(sku: str, product_name: str = None) -> Optional[Dict]:
    """Cached version of product info lookup"""
    return _get_trek_product_info_internal(sku, product_name)

def _get_trek_product_info_internal(sku: str, product_name: str = None) -> Optional[Dict]:
    """Internal product info lookup - %90 WEB SCRAPING PRIORITY"""
    sku = str(sku).strip()
    
    # 1. Local database lookup - sadece bilinen kesin SKU'lar
    if sku in TREK_SKU_DATABASE:
        print(f"Database hit: {sku}")
        return TREK_SKU_DATABASE[sku]
    
    # 2. WEB SCRAPING ÖNCE! - %90 öncelik
    print(f"🌐 Trek sitesinden AGGRESSIVE araştırma başlatılıyor: {sku}")
    cache_key = f"web_{sku}_{product_name}" if product_name else f"web_{sku}"
    current_time = time.time()
    
    if cache_key in _WEB_CACHE:
        cached_result, timestamp = _WEB_CACHE[cache_key]
        if current_time - timestamp < _CACHE_EXPIRY:
            print(f"Web cache hit: {sku}")
            return cached_result
        else:
            # Remove expired cache entry
            del _WEB_CACHE[cache_key]
    
    # 3. Try OPENAI FIRST for intelligent analysis WITH PRODUCT NAME
    print(f"🤖 OpenAI analizi: {sku} {f'(Fatura ismi: {product_name})' if product_name else ''}")
    openai_result = get_product_info_from_openai(sku, product_name)
    
    if openai_result and openai_result.get('name') != f"Trek Ürünü #{sku}":
        # Cache successful result
        _WEB_CACHE[cache_key] = (openai_result, current_time)
        return openai_result
    
    # 4. Try web scraping as backup
    print(f"Web scraping: {sku}")
    
    # B2B credentials için environment variables kontrol et
    import os
    trek_username = os.getenv('TREK_B2B_USERNAME')
    trek_password = os.getenv('TREK_B2B_PASSWORD')
    
    web_result = get_trek_product_info_from_web(sku, trek_username, trek_password)
    
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

def get_trek_product_info(sku: str, product_name: str = None) -> Optional[Dict]:
    """Main entry point for Trek product info lookup - Optimized with caching"""
    return get_trek_product_info_cached(sku, product_name)

def clear_cache():
    """Clear all caches - useful for testing or memory management"""
    global _WEB_CACHE
    _WEB_CACHE.clear()
    get_trek_product_info_cached.cache_clear()
    print("All caches cleared")

def get_cache_stats():
    """Get cache statistics"""
    return {
        'web_cache_size': len(_WEB_CACHE),
        'lru_cache_info': get_trek_product_info_cached.cache_info()._asdict()
    }