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

def extract_text_from_pdf(file_path):
    """PDF dosyasından metin çıkar"""
    text_content = []
    tables_data = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Sayfa metnini al
                text = page.extract_text()
                if text:
                    text_content.append(f"Sayfa {page_num}:\n{text}")
                
                # Tabloları çıkar
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        tables_data.append({
                            'page': page_num,
                            'data': table
                        })
    except Exception as e:
        print(f"PDF okuma hatası: {e}")
        return None, None
    
    return '\n'.join(text_content), tables_data

def extract_sku_from_text(text):
    """Metinden SKU kodlarını çıkar"""
    sku_patterns = [
        r'\b\d{6,10}\b',  # 6-10 haneli sayılar
        r'\b[A-Z]{2,4}[-\s]?\d{4,8}\b',  # Harf-sayı kombinasyonları
        r'\bSKU[:\s]+([A-Z0-9-]+)\b',  # SKU: ile başlayanlar
        r'\bItem[:\s]+([A-Z0-9-]+)\b',  # Item: ile başlayanlar
        r'\bCode[:\s]+([A-Z0-9-]+)\b',  # Code: ile başlayanlar
        r'\b[A-Z0-9]{8,12}\b',  # Büyük harf ve sayı karışımı
    ]
    
    skus = []
    for pattern in sku_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        skus.extend(matches)
    
    # Tekrar edenleri kaldır ve temizle
    unique_skus = []
    for sku in skus:
        if isinstance(sku, tuple):
            sku = sku[0]
        sku = sku.strip()
        if sku and sku not in unique_skus and len(sku) >= 5:
            # Sadece sayı olan ve 5 haneden küçük olanları filtele (fiyat olabilir)
            if not (sku.isdigit() and len(sku) < 6):
                unique_skus.append(sku)
    
    return unique_skus

def search_trek_product(sku):
    """Trek Bikes sitesinde SKU ile ürün ara"""
    # Önce basit bir API denemesi
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Trek'in olası arama URL'leri
    search_urls = [
        f"https://www.trekbikes.com/us/en_US/search/?text={sku}",
        f"https://www.trekbikes.com/search?q={sku}",
    ]
    
    for url in search_urls:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Ürün başlığını bul
                product_title = None
                title_selectors = [
                    'h1.product-title',
                    'h1.product-name',
                    'div.product-info h1',
                    'h1[itemprop="name"]',
                    '.product-detail h1',
                    'h1'
                ]
                
                for selector in title_selectors:
                    element = soup.select_one(selector)
                    if element:
                        product_title = element.text.strip()
                        break
                
                # Kategori bilgisini bul
                category = None
                category_selectors = [
                    'nav.breadcrumb',
                    '.breadcrumbs',
                    'div.category-name',
                    'span.product-category'
                ]
                
                for selector in category_selectors:
                    element = soup.select_one(selector)
                    if element:
                        category = element.text.strip()
                        break
                
                if product_title:
                    return {
                        'sku': sku,
                        'title': product_title,
                        'category': category,
                        'url': url
                    }
                    
        except Exception as e:
            print(f"Trek arama hatası {sku}: {e}")
            continue
    
    return None

def translate_trek_product(product_info):
    """Trek ürün bilgisini Türkçe'ye çevir"""
    if not product_info:
        return "Ürün bulunamadı"
    
    title = product_info.get('title', '')
    category = product_info.get('category', '')
    
    # Başlıktan Türkçe tanım oluştur
    turkish_parts = []
    
    # Model ismini koru ama kategori ekle
    title_lower = title.lower()
    
    # Özel model isimlerini kontrol et
    for model, tr_model in TREK_CATEGORIES.items():
        if model in title_lower:
            turkish_parts.append(tr_model)
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
        elif any(word in title_lower for word in ['helmet', 'light', 'lock', 'pump', 'bottle']):
            turkish_parts.append('Aksesuar')
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
        'pink': 'Pembe'
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
    
    # Orijinal başlığı da ekle
    return f"{turkish_description} [{title}]"

def process_pdf_invoice(file_path):
    """PDF faturayı işle ve SKU'lardan ürün bilgilerini al"""
    # PDF'den metin ve tabloları çıkar
    text, tables = extract_text_from_pdf(file_path)
    
    if not text and not tables:
        return None, "PDF okunamadı"
    
    # SKU'ları çıkar
    skus = extract_sku_from_text(text)
    
    # Tablolardan da SKU ara
    if tables:
        for table_info in tables:
            for row in table_info['data']:
                for cell in row:
                    if cell:
                        cell_skus = extract_sku_from_text(str(cell))
                        skus.extend(cell_skus)
    
    # Tekrar edenleri kaldır
    unique_skus = list(set(skus))
    
    # Her SKU için ürün bilgisi al
    products = []
    for sku in unique_skus[:20]:  # İlk 20 SKU ile sınırla
        print(f"SKU aranıyor: {sku}")
        
        # Önce Trek'te ara
        product_info = search_trek_product(sku)
        
        if product_info:
            turkish_desc = translate_trek_product(product_info)
            products.append({
                'SKU': sku,
                'Ürün Adı': product_info.get('title', ''),
                'Kategori': product_info.get('category', ''),
                'Türkçe Tanım': turkish_desc,
                'URL': product_info.get('url', '')
            })
        else:
            # Ürün bulunamazsa sadece SKU'yu ekle
            products.append({
                'SKU': sku,
                'Ürün Adı': 'Bulunamadı',
                'Kategori': '',
                'Türkçe Tanım': f'Trek Ürünü (SKU: {sku})',
                'URL': ''
            })
        
        # Rate limiting
        time.sleep(0.5)
    
    if products:
        df = pd.DataFrame(products)
        return df, None
    else:
        return None, "Faturada SKU bulunamadı"

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
    """Tek bir SKU için arama yap"""
    data = request.json
    sku = data.get('sku', '')
    
    if not sku:
        return jsonify({'error': 'SKU boş olamaz'}), 400
    
    product_info = search_trek_product(sku)
    
    if product_info:
        turkish_desc = translate_trek_product(product_info)
        return jsonify({
            'success': True,
            'product': {
                'sku': sku,
                'title': product_info.get('title', ''),
                'category': product_info.get('category', ''),
                'turkish': turkish_desc,
                'url': product_info.get('url', '')
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Ürün bulunamadı'
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)