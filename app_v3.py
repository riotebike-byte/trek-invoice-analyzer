from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime
import pdfplumber
import re
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Klasörleri oluştur
os.makedirs('uploads', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Trek ürün kategorileri ve Türkçe karşılıkları
TREK_CATEGORIES = {
    'bikes': 'Bisikletler',
    'bike': 'Bisiklet',
    'e-bike': 'Elektrikli Bisiklet',
    'ebike': 'Elektrikli Bisiklet',
    'mountain': 'Dağ Bisikleti',
    'road': 'Yol Bisikleti',
    'hybrid': 'Hibrit Bisiklet',
    'gravel': 'Gravel Bisiklet',
    'city': 'Şehir Bisikleti',
    'kids': 'Çocuk Bisikleti',
    
    # Parça ve Aksesuarlar
    'helmet': 'Kask',
    'helmets': 'Kasklar',
    'light': 'Işık',
    'lights': 'Işıklar',
    'lock': 'Kilit',
    'locks': 'Kilitler',
    'pump': 'Pompa',
    'pumps': 'Pompalar',
    'bottle': 'Matara/Suluk',
    'bottles': 'Mataralar/Suluklar',
    'cage': 'Matara Kafesi',
    'pedal': 'Pedal',
    'pedals': 'Pedallar',
    'saddle': 'Sele',
    'seat': 'Sele/Oturma Yeri',
    'handlebar': 'Gidon',
    'stem': 'Gidon Boğazı',
    'grip': 'Gidon Gribi',
    'grips': 'Gidon Gripleri',
    'tire': 'Lastik',
    'tires': 'Lastikler',
    'tyre': 'Lastik',
    'tyres': 'Lastikler',
    'tube': 'İç Lastik',
    'tubes': 'İç Lastikler',
    'wheel': 'Tekerlek',
    'wheels': 'Tekerlekler',
    'chain': 'Zincir',
    'cassette': 'Kaset/Dişli',
    'derailleur': 'Vites',
    'brake': 'Fren',
    'brakes': 'Frenler',
    'disc': 'Disk',
    'rotor': 'Disk Rotor',
    
    # Giyim
    'jersey': 'Forma',
    'short': 'Şort',
    'shorts': 'Şortlar',
    'bib': 'Askılı Şort',
    'jacket': 'Ceket',
    'vest': 'Yelek',
    'glove': 'Eldiven',
    'gloves': 'Eldivenler',
    'shoe': 'Ayakkabı',
    'shoes': 'Ayakkabılar',
    'sock': 'Çorap',
    'socks': 'Çoraplar',
    
    # Çanta ve Taşıyıcılar
    'bag': 'Çanta',
    'bags': 'Çantalar',
    'pannier': 'Heybe',
    'rack': 'Portbagaj',
    'carrier': 'Taşıyıcı',
    
    # Servis ve Yedek Parça
    'service': 'Servis',
    'maintenance': 'Bakım',
    'repair': 'Onarım',
    'tool': 'Alet',
    'tools': 'Aletler',
    'lubricant': 'Yağ/Gres',
    'cleaner': 'Temizleyici',
    'kit': 'Set/Kit',
    'spare': 'Yedek Parça',
    'parts': 'Parçalar',
    
    # Elektronik
    'computer': 'Kilometre Saati',
    'sensor': 'Sensör',
    'battery': 'Batarya/Pil',
    'charger': 'Şarj Cihazı',
    'display': 'Ekran/Gösterge',
    
    # Model İsimleri (özel isimler - sadece kategori ekle)
    'fuel': 'Fuel Serisi',
    'madone': 'Madone Serisi',
    'domane': 'Domane Serisi',
    'checkpoint': 'Checkpoint Serisi',
    'marlin': 'Marlin Serisi',
    'slash': 'Slash Serisi',
    'remedy': 'Remedy Serisi',
    'procaliber': 'Procaliber Serisi',
    'top fuel': 'Top Fuel Serisi',
    'powerfly': 'Powerfly Serisi',
    'rail': 'Rail Serisi',
    'verve': 'Verve Serisi',
    'fx': 'FX Serisi',
    'dual sport': 'Dual Sport Serisi'
}

def extract_item_numbers_from_pdf(file_path):
    """PDF dosyasından sadece item number'ları çıkar"""
    all_text = []
    tables_data = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Sayfa metnini al
                text = page.extract_text()
                if text:
                    all_text.append(text)
                
                # Tabloları çıkar
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        tables_data.append(table)
    except Exception as e:
        print(f"PDF okuma hatası: {e}")
        return []
    
    # Item number'ları bulmak için pattern'ler
    item_numbers = []
    
    # Tablolarda item number sütunu ara
    for table in tables_data:
        if not table:
            continue
            
        # Başlık satırını bul
        header_row = None
        item_col_idx = -1
        
        for idx, row in enumerate(table):
            if row:
                # Item Number, Item #, Item, Product Code vb. başlıkları ara
                for col_idx, cell in enumerate(row):
                    if cell and any(keyword in str(cell).lower() for keyword in ['item number', 'item #', 'item#', 'item no', 'product code', 'sku', 'code']):
                        header_row = idx
                        item_col_idx = col_idx
                        break
                if item_col_idx >= 0:
                    break
        
        # Item number'ları topla
        if item_col_idx >= 0:
            for idx, row in enumerate(table):
                if idx <= header_row:  # Başlık satırını atla
                    continue
                if row and len(row) > item_col_idx and row[item_col_idx]:
                    item = str(row[item_col_idx]).strip()
                    # Sadece sayısal veya sayı-harf karışımı item'ları al
                    # En az 5 karakter ve en fazla 10 karakter
                    if item and 5 <= len(item) <= 10:
                        # Sadece sayı veya sayı+harf kombinasyonu
                        if re.match(r'^[A-Z0-9]+$', item, re.IGNORECASE):
                            # Yaygın kelimeler değilse ekle
                            common_words = ['SEARCH', 'ITEM', 'TOTAL', 'DISCOUNT', 'TAX', 'SHIPPING', 'INVOICE', 
                                          'DATE', 'CUSTOMER', 'ADDRESS', 'PHONE', 'EMAIL', 'QUANTITY', 'PRICE',
                                          'AMOUNT', 'SUBTOTAL', 'PAYMENT', 'DESCRIPTION', 'UNIT', 'QTY',
                                          'authorized', 'regulations', 'controlled', 'percentage', 'Bisiklet',
                                          'Istanbul', 'trekbikes', 'AQUAMARINE']
                            if not any(word.upper() == item.upper() for word in common_words):
                                # En az 1 sayı içermeli
                                if any(c.isdigit() for c in item):
                                    item_numbers.append(item)
    
    # Eğer tablolardan bulamadıysa, metinde item number pattern'i ara
    if not item_numbers:
        full_text = '\n'.join(all_text)
        # Item Number: 1234567 formatını ara
        pattern = r'(?:Item\s*(?:Number|#|No\.?)?[:]\s*)([0-9]{5,10})'
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        item_numbers.extend(matches)
    
    # Tekrar edenleri kaldır
    unique_items = []
    seen = set()
    for item in item_numbers:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    
    return unique_items

def search_trek_product_by_item(item_number):
    """Trek Bikes sitesinde item number ile ürün ara ve fiyat kontrolü yap"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # Trek'in arama URL'leri - güncellenmiş format
    search_urls = [
        f"https://www.trekbikes.com/us/en_US/search/?q={item_number}",
        f"https://www.trekbikes.com/de/de_DE/search/?q={item_number}",
        f"https://www.trekbikes.com/tr/tr_TR/search/?q={item_number}"
    ]
    
    for url in search_urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Ürün başlığını bul
                product_title = None
                price = None
                category = None
                
                # Ürün kartlarını ara - daha geniş selector
                product_selectors = [
                    '.product-tile', '.product-item', '.product-card', '.search-result',
                    '[data-product]', '.tile', '.result-item'
                ]
                
                product_cards = []
                for selector in product_selectors:
                    cards = soup.select(selector)
                    if cards:
                        product_cards.extend(cards)
                        break
                
                # Eğer spesifik kart bulunamadıysa genel div arama yap
                if not product_cards:
                    product_cards = soup.find_all(['div', 'article'], class_=re.compile(r'product|item|tile', re.I))
                
                for card in product_cards:
                    # Başlığı bul
                    title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|heading', re.I))
                    if not title_elem:
                        # Link'te başlık arayabilir
                        link_elem = card.find('a')
                        if link_elem and link_elem.get('title'):
                            product_title = link_elem.get('title')
                        elif link_elem:
                            product_title = link_elem.get_text(strip=True)
                    else:
                        product_title = title_elem.get_text(strip=True)
                    
                    # Fiyatı bul
                    price_elem = card.find(['span', 'div', 'p'], string=re.compile(r'\$|\€|TL|USD|EUR'))
                    if not price_elem:
                        price_elem = card.find(['span', 'div', 'p'], class_=re.compile(r'price|cost', re.I))
                    
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        # Para birimi kontrolü
                        if any(curr in price_text for curr in ['$', '€', 'TL', 'USD', 'EUR']):
                            price = price_text
                    
                    # Eğer başlık ve fiyat bulunduysa, bu bir ürün kartıdır
                    if product_title and len(product_title) > 3:
                        if price:
                            break
                        # Fiyat yoksa da ürünü kaydet, sonra fiyat aramaya devam et
                        elif not price:
                            continue
                
                # Eğer ürün kartlarında bulamadıysa, sayfa genelinde ara
                if not product_title:
                    # Doğrudan ürün sayfasına yönlendirilmiş olabilir
                    title_selectors = [
                        'h1.product-title',
                        'h1.product-name', 
                        'h1[itemprop="name"]',
                        '.product-detail h1',
                        '.pdp-title',
                        'h1'
                    ]
                    
                    for selector in title_selectors:
                        element = soup.select_one(selector)
                        if element:
                            product_title = element.text.strip()
                            break
                    
                    # Fiyat ara
                    price_selectors = [
                        '.product-price',
                        '.price-now',
                        '[itemprop="price"]',
                        '.pdp-price',
                        '.price'
                    ]
                    
                    for selector in price_selectors:
                        element = soup.select_one(selector)
                        if element:
                            price_text = element.text.strip()
                            if '$' in price_text or '€' in price_text:
                                price = price_text
                                break
                
                # Kategori bilgisini bul
                breadcrumb = soup.find('nav', class_='breadcrumb')
                if breadcrumb:
                    category = breadcrumb.get_text(strip=True)
                
                # Sadece fiyatı olan ürünleri döndür
                if product_title and price:
                    return {
                        'item_number': item_number,
                        'title': product_title,
                        'price': price,
                        'category': category,
                        'url': response.url
                    }
                    
        except Exception as e:
            print(f"Trek arama hatası {item_number}: {e}")
            continue
    
    return None

def translate_trek_product(product_info):
    """Trek ürün bilgisini Türkçe'ye çevir"""
    if not product_info:
        return None
    
    title = product_info.get('title', '')
    category = product_info.get('category', '')
    price = product_info.get('price', '')
    
    # Başlıktan Türkçe tanım oluştur
    turkish_parts = []
    
    # Model ismini koru ama kategori ekle
    title_lower = title.lower()
    
    # Özel model isimlerini kontrol et
    model_found = False
    for model, tr_model in TREK_CATEGORIES.items():
        if model in title_lower:
            turkish_parts.append(tr_model)
            model_found = True
            break
    
    # Genel kategorileri ekle
    for eng, tr in TREK_CATEGORIES.items():
        if eng in title_lower and tr not in turkish_parts:
            turkish_parts.append(tr)
    
    # Eğer hiç çeviri bulunamadıysa
    if not turkish_parts:
        # En azından bisiklet mi aksesuar mı belirle
        if any(word in title_lower for word in ['bike', 'bicycle', 'ebike', 'e-bike']):
            turkish_parts.append('Bisiklet')
        elif any(word in title_lower for word in ['helmet', 'light', 'lock', 'pump', 'bottle', 'bag', 'tool']):
            turkish_parts.append('Aksesuar')
        elif any(word in title_lower for word in ['jersey', 'short', 'jacket', 'glove', 'shoe']):
            turkish_parts.append('Giyim')
        else:
            turkish_parts.append('Trek Ürünü')
    
    # Yıl bilgisi varsa ekle
    year_match = re.search(r'20\d{2}', title)
    if year_match:
        turkish_parts.append(f"{year_match.group()} Model")
    
    # Renk bilgisi
    colors = {
        'black': 'Siyah',
        'white': 'Beyaz',
        'red': 'Kırmızı',
        'blue': 'Mavi',
        'green': 'Yeşil',
        'grey': 'Gri',
        'gray': 'Gri',
        'silver': 'Gümüş',
        'gold': 'Altın',
        'yellow': 'Sarı',
        'orange': 'Turuncu',
        'purple': 'Mor',
        'pink': 'Pembe',
        'carbon': 'Karbon'
    }
    
    for eng_color, tr_color in colors.items():
        if eng_color in title_lower:
            turkish_parts.append(tr_color)
            break
    
    # Boyut bilgisi
    size_match = re.search(r'\b(XS|S|M|L|XL|XXL|\d{2})\b', title)
    if size_match:
        turkish_parts.append(f"Beden: {size_match.group()}")
    
    # Türkçe tanımı oluştur
    turkish_description = ' - '.join(turkish_parts)
    
    # Fiyat bilgisini ekle
    if price:
        turkish_description += f" (Fiyat: {price})"
    
    return turkish_description

def process_pdf_invoice(file_path):
    """PDF faturayı işle ve item number'lardan ürün bilgilerini al"""
    # PDF'den item number'ları çıkar
    item_numbers = extract_item_numbers_from_pdf(file_path)
    
    if not item_numbers:
        return None, "Faturada item number bulunamadı"
    
    # Her item number için ürün bilgisi al
    products = []
    for item_num in item_numbers[:20]:  # İlk 20 item ile sınırla
        print(f"Item number aranıyor: {item_num}")
        
        # Trek'te ara
        product_info = search_trek_product_by_item(item_num)
        
        if product_info:
            turkish_desc = translate_trek_product(product_info)
            if turkish_desc:  # Sadece Türkçe tanım oluşturulanları ekle
                products.append({
                    'Item Number': item_num,
                    'Ürün Adı': product_info.get('title', ''),
                    'Fiyat': product_info.get('price', ''),
                    'Kategori': product_info.get('category', ''),
                    'Türkçe Tanım': turkish_desc,
                    'URL': product_info.get('url', '')
                })
        
        # Rate limiting
        time.sleep(1)
    
    if products:
        df = pd.DataFrame(products)
        return df, None
    else:
        return None, "Faturada fiyatlı Trek ürünü bulunamadı"

def process_invoice(file_path):
    """Invoice dosyasını işle (PDF, CSV veya Excel)"""
    try:
        if file_path.endswith('.pdf'):
            return process_pdf_invoice(file_path)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            # CSV için mevcut işleme mantığı
            return df, None
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
            # Excel için mevcut işleme mantığı
            return df, None
        else:
            return None, "Desteklenmeyen dosya formatı"
    except Exception as e:
        return None, str(e)

@app.route('/')
def index():
    return render_template('index_v2.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Dosya bulunamadı'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Dosya seçilmedi'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Invoice'i işle
        df, error = process_invoice(filepath)
        
        if error:
            return jsonify({'error': f'Dosya işlenirken hata: {error}'}), 500
        
        if df is None or df.empty:
            return jsonify({'error': 'Faturada işlenebilir ürün bulunamadı'}), 404
        
        # Sonuçları hazırla
        result = {
            'filename': filename,
            'total_rows': len(df),
            'columns': list(df.columns),
            'data': df.to_dict('records'),
            'file_type': 'PDF' if filename.endswith('.pdf') else 'Excel/CSV'
        }
        
        # İşlenmiş dosyayı kaydet
        output_filename = f"translated_{filename.split('.')[-2]}.xlsx"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        df.to_excel(output_path, index=False)
        result['output_file'] = output_filename
        
        return jsonify(result)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/search_sku', methods=['POST'])
def search_sku():
    """Tek bir item number için arama yap"""
    data = request.json
    item_num = data.get('sku', '')
    
    if not item_num:
        return jsonify({'error': 'Item number boş olamaz'}), 400
    
    product_info = search_trek_product_by_item(item_num)
    
    if product_info:
        turkish_desc = translate_trek_product(product_info)
        return jsonify({
            'success': True,
            'product': {
                'item_number': item_num,
                'title': product_info.get('title', ''),
                'price': product_info.get('price', ''),
                'category': product_info.get('category', ''),
                'turkish': turkish_desc,
                'url': product_info.get('url', '')
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Ürün bulunamadı veya fiyat bilgisi yok'
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)