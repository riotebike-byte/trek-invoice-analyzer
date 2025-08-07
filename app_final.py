from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime
import pdfplumber
import re
import time
from trek_sku_database import get_trek_product_info

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Klasörleri oluştur
os.makedirs('uploads', exist_ok=True)
os.makedirs('templates', exist_ok=True)

def extract_item_numbers_from_pdf(file_path):
    """PDF dosyasından item number'ları çıkar - gelişmiş algoritma"""
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
                        tables_data.append({
                            'page': page_num,
                            'data': table
                        })
    except Exception as e:
        print(f"PDF okuma hatası: {e}")
        return []
    
    item_numbers = []
    
    # 1. Tablolarda item number sütunu ara
    for table_info in tables_data:
        table = table_info['data']
        if not table:
            continue
            
        # Başlık satırını ve item sütununu bul
        item_col_idx = -1
        for row_idx, row in enumerate(table):
            if not row:
                continue
            for col_idx, cell in enumerate(row):
                if cell:
                    cell_lower = str(cell).lower()
                    # Item number başlığı ara
                    if any(keyword in cell_lower for keyword in [
                        'item number', 'item #', 'item#', 'item no', 'item code',
                        'product code', 'sku', 'code', 'model', 'part number'
                    ]):
                        item_col_idx = col_idx
                        # Bu satırdan sonraki satırları işle
                        for data_row_idx in range(row_idx + 1, len(table)):
                            data_row = table[data_row_idx]
                            if data_row and len(data_row) > item_col_idx and data_row[item_col_idx]:
                                item_candidate = str(data_row[item_col_idx]).strip()
                                if is_valid_item_number(item_candidate):
                                    item_numbers.append(item_candidate)
                        break
            if item_col_idx >= 0:
                break
    
    # 2. Tablolarda sayısal değerleri kontrol et (sütun başlığı yoksa)
    if not item_numbers:
        for table_info in tables_data:
            table = table_info['data']
            for row in table:
                if row:
                    for cell in row:
                        if cell:
                            cell_str = str(cell).strip()
                            if is_valid_item_number(cell_str):
                                item_numbers.append(cell_str)
    
    # 3. Düz metinde item pattern'leri ara
    if not item_numbers:
        full_text = '\n'.join(all_text)
        patterns = [
            r'(?:Item\s*(?:Number|#|No\.?)?[:]?\s*)([A-Z0-9]{4,8})',
            r'(?:SKU[:]?\s*)([A-Z0-9]{4,8})',
            r'(?:Code[:]?\s*)([A-Z0-9]{4,8})',
            r'\b([A-Z0-9]{5,7})\b',  # 5-7 karakter alfanümerik
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                if is_valid_item_number(match):
                    item_numbers.append(match)
    
    # Benzersiz item'ları döndür
    unique_items = []
    seen = set()
    for item in item_numbers:
        if item not in seen and len(item) >= 4:
            seen.add(item)
            unique_items.append(item)
    
    return unique_items  # Tüm itemler

def is_valid_item_number(candidate):
    """Geçerli bir item number olup olmadığını kontrol et"""
    if not candidate or len(candidate) < 4 or len(candidate) > 10:
        return False
    
    # Yaygın kelimeler değil
    invalid_words = [
        'SEARCH', 'ITEM', 'TOTAL', 'DISCOUNT', 'TAX', 'SHIPPING', 'INVOICE',
        'DATE', 'CUSTOMER', 'ADDRESS', 'PHONE', 'EMAIL', 'QUANTITY', 'PRICE',
        'AMOUNT', 'SUBTOTAL', 'PAYMENT', 'DESCRIPTION', 'UNIT', 'QTY',
        'AUTHORIZED', 'REGULATIONS', 'CONTROLLED', 'PERCENTAGE', 'BISIKLET',
        'ISTANBUL', 'TREKBIKES', 'AQUAMARINE', 'COMPANY', 'STREET', 'CITY',
        'STATE', 'ORDER', 'BILL', 'SHIP', 'FROM', 'NAME', 'LINE'
    ]
    
    if candidate.upper() in invalid_words:
        return False
    
    # En az bir rakam içermeli
    if not any(c.isdigit() for c in candidate):
        return False
    
    # Sadece harf ve rakam içermeli
    if not re.match(r'^[A-Z0-9]+$', candidate, re.IGNORECASE):
        return False
    
    # Çok yaygın pattern'leri filtrele
    if re.match(r'^\d{1,3}$', candidate):  # 1-3 rakam (muhtemelen miktar)
        return False
    
    if re.match(r'^\d{4}$', candidate) and int(candidate) > 2000 and int(candidate) < 2030:  # Yıl
        return False
    
    return True

def analyze_product_name_for_category(sku, product_name):
    """Fatura ürün isminden otomatik kategori belirle"""
    if not product_name:
        return None
        
    name_upper = product_name.upper()
    
    # İlk 3 harfi al
    first_3 = name_upper[:3] if len(name_upper) >= 3 else name_upper
    
    # 3 harflik kısaltmalara odaklan
    if first_3 == 'SAD':  # SADDLE
        return {
            "name": f"Bontrager Sele - {product_name}",
            "category": "Bisiklet Selesi",
            "product_type": "Bisiklet Selesi", 
            "subcategory": "Sele",
            "turkish": "Bisiklet selesi",
            "gtip_description": "Bisiklet selesi (oturma yeri)",
            "series": "Bontrager"
        }
    
    elif first_3 == 'CHN':  # CHAIN
        return {
            "name": f"Trek Zincir - {product_name}",
            "category": "Bisiklet Vites Sistemi",
            "product_type": "Bisiklet Zinciri",
            "subcategory": "Zincir",
            "turkish": "Bisiklet zinciri",
            "gtip_description": "Bisiklet zinciri",
            "series": "Trek"
        }
    
    elif first_3 == 'PED':  # PEDAL
        return {
            "name": f"Trek Pedal - {product_name}",
            "category": "Bisiklet Pedalı",
            "product_type": "Bisiklet Pedalı",
            "subcategory": "Pedal",
            "turkish": "Bisiklet pedalı",
            "gtip_description": "Bisiklet pedalı",
            "series": "Trek"
        }
    
    elif first_3 == 'GRP':  # GRIP
        return {
            "name": f"Bontrager Tutacak - {product_name}",
            "category": "Bisiklet Aksesuarı",
            "product_type": "Gidon Tutacağı",
            "subcategory": "Grip/Tutacak",
            "turkish": "Gidon tutacağı/grip",
            "gtip_description": "Bisiklet gidon tutacağı",
            "series": "Bontrager"
        }
    
    elif first_3 == 'HAN' or first_3 == 'HBR':  # HANDLEBAR
        return {
            "name": f"Trek Gidon - {product_name}",
            "category": "Bisiklet Gidon",
            "product_type": "Bisiklet Gidon",
            "subcategory": "Gidon",
            "turkish": "Bisiklet gidonu",
            "gtip_description": "Bisiklet gidonu",
            "series": "Trek"
        }
    
    elif first_3 == 'STE':  # STEM
        return {
            "name": f"Trek Potans - {product_name}",
            "category": "Bisiklet Potansı",
            "product_type": "Bisiklet Potansı",
            "subcategory": "Potans",
            "turkish": "Bisiklet potansı/stem",
            "gtip_description": "Bisiklet potansı",
            "series": "Trek"
        }
    
    elif first_3 == 'TIR':  # TIRE
        return {
            "name": f"Trek Lastik - {product_name}",
            "category": "Bisiklet Tekerlek/Lastik",
            "product_type": "Bisiklet Lastiği",
            "subcategory": "Lastik",
            "turkish": "Bisiklet lastiği",
            "gtip_description": "Bisiklet lastiği",
            "series": "Trek"
        }
    
    elif first_3 == 'WHL':  # WHEEL
        return {
            "name": f"Trek Tekerlek - {product_name}",
            "category": "Bisiklet Tekerlek/Lastik",
            "product_type": "Bisiklet Tekerleği",
            "subcategory": "Tekerlek",
            "turkish": "Bisiklet tekerleği",
            "gtip_description": "Bisiklet tekerleği",
            "series": "Trek"
        }
    
    elif first_3 == 'BRK':  # BRAKE
        return {
            "name": f"Trek Fren - {product_name}",
            "category": "Bisiklet Fren Sistemi",
            "product_type": "Bisiklet Fren",
            "subcategory": "Fren",
            "turkish": "Bisiklet fren sistemi",
            "gtip_description": "Bisiklet fren sistemi",
            "series": "Trek"
        }
    
    elif first_3 == 'LCK':  # LOCK
        return {
            "name": f"Bontrager Kilit - {product_name}",
            "category": "Bisiklet Güvenlik",
            "product_type": "Bisiklet Kilidi",
            "subcategory": "Kilit",
            "turkish": "Bisiklet kilidi",
            "gtip_description": "Bisiklet kilidi (güvenlik ekipmanı)",
            "series": "Bontrager"
        }
    
    # Aydınlatma (LIT = LIGHT)
    elif first_3 == 'LIT' or any(word in name_upper for word in ['LIGHT', 'LED', 'LAMP']):
        return {
            "name": f"Trek Işık - {product_name}",
            "category": "Bisiklet Aydınlatması",
            "product_type": "Bisiklet Işığı",
            "subcategory": "Aydınlatma",
            "turkish": "Bisiklet ışığı/aydınlatma sistemi",
            "gtip_description": "Bisiklet ışığı (aydınlatma ekipmanı)",
            "series": "Trek"
        }
    
    return None

def extract_product_names_from_pdf(file_path, item_numbers):
    """PDF'den item number'lara karşılık gelen ürün adlarını çıkar - Geliştirilmiş"""
    product_names = {}
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Hem text hem de tablolardan al
                text = page.extract_text()
                tables = page.extract_tables()
                
                # Tablolardan ürün adı ara
                for table in tables:
                    if table:
                        for row in table:
                            if row:
                                row_text = ' '.join([str(cell) if cell else '' for cell in row])
                                for item_num in item_numbers:
                                    if item_num in row_text:
                                        # SKU'dan sonra gelen hücreleri kontrol et
                                        for i, cell in enumerate(row):
                                            if cell and item_num in str(cell):
                                                # Sonraki hücrelerde açıklama ara
                                                for j in range(i+1, len(row)):
                                                    if row[j] and len(str(row[j])) > 3:
                                                        desc = str(row[j]).strip()
                                                        # Sayı değilse ve makul uzunluktaysa
                                                        if not desc.replace('.','').replace(',','').isdigit() and len(desc) < 100:
                                                            product_names[item_num] = desc
                                                            break
                                                break
                
                # Text'ten de ara (tablo bulunamazsa)
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        line_clean = line.strip()
                        for item_num in item_numbers:
                            if item_num in line_clean and item_num not in product_names:
                                # Satırı boşluklarla böl
                                parts = line_clean.split()
                                # SKU'nun pozisyonunu bul
                                try:
                                    sku_index = parts.index(item_num)
                                    # SKU'dan sonraki parçaları al
                                    if sku_index < len(parts) - 1:
                                        # Sonraki parçaları birleştir (sayısal olmayan ilk 5 kelime)
                                        desc_parts = []
                                        for part in parts[sku_index + 1:]:
                                            # Sayısal değilse ekle
                                            if not part.replace('.','').replace(',','').isdigit():
                                                desc_parts.append(part)
                                                if len(desc_parts) >= 5:  # Max 5 kelime
                                                    break
                                        
                                        if desc_parts:
                                            product_name = ' '.join(desc_parts)
                                            if len(product_name) > 3:
                                                product_names[item_num] = product_name
                                except ValueError:
                                    continue
                                    
    except Exception as e:
        print(f"Ürün adı çıkarma hatası: {e}")
    
    return product_names

def extract_invoice_number(file_path):
    """Dosya adından veya PDF içeriğinden fatura numarasını çıkar"""
    # Önce dosya adından dene
    filename = os.path.basename(file_path)
    
    # Dosya adındaki timestamp'i kaldır
    filename_clean = re.sub(r'^\d{8}_\d{6}_', '', filename)
    filename_clean = re.sub(r'\.(pdf|PDF)$', '', filename_clean)
    
    # Yaygın fatura numarası pattern'leri
    invoice_patterns = [
        r'Invoice[_\s#-]*(\d+)',
        r'INV[_\s#-]*(\d+)',
        r'Fatura[_\s#-]*(\d+)',
        r'(\d{6,})',  # 6+ haneli rakam
    ]
    
    for pattern in invoice_patterns:
        match = re.search(pattern, filename_clean, re.IGNORECASE)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    
    # PDF içeriğinden dene
    try:
        with pdfplumber.open(file_path) as pdf:
            first_page_text = pdf.pages[0].extract_text()
            if first_page_text:
                for pattern in invoice_patterns:
                    match = re.search(pattern, first_page_text, re.IGNORECASE)
                    if match:
                        return match.group(1) if match.groups() else match.group(0)
    except:
        pass
    
    # Son çare olarak dosya adını kullan
    return filename_clean

def process_pdf_invoice(file_path):
    """PDF faturayı işle ve 5 sütun halinde sonuç döndür"""
    # PDF'den item number'ları çıkar
    item_numbers = extract_item_numbers_from_pdf(file_path)
    
    if not item_numbers:
        return None, "Faturada geçerli item number bulunamadı"
    
    print(f"Bulunan item number'lar: {item_numbers}")
    
    # Fatura numarasını çıkar
    invoice_number = extract_invoice_number(file_path)
    
    # Ürün adlarını çıkar
    product_names = extract_product_names_from_pdf(file_path, item_numbers)
    
    # Her item number için ürün bilgisi al
    products = []
    for item_num in item_numbers:
        # Önce fatura isminden analiz dene
        invoice_name = product_names.get(item_num, '')
        auto_category = analyze_product_name_for_category(item_num, invoice_name)
        
        if auto_category:
            # Fatura isminden belirlendi
            product_info = auto_category
            is_defined = True
        else:
            # Trek veritabanından bilgi al - FAT URA İSMİNİ DE GÖNDER
            product_info = get_trek_product_info(item_num, invoice_name)
            
            # Tanımlanabilir mi kontrol et
            is_defined = False
            if product_info:
                # Eğer gerçek bilgi varsa (genel "Trek Ürünü" değilse)
                if (product_info.get('name', '').startswith('Trek Ürünü #') == False and 
                    product_info.get('category', '') != 'Trek Ürünü'):
                    is_defined = True
        
        products.append({
            'Fatura Numarası': invoice_number,
            'SKU': item_num,
            'Faturadaki İsmi': invoice_name,
            'Türkçe Tanım': product_info.get('turkish', '') if product_info else 'Tanımlanamadı',
            'GTİP Tanımı': product_info.get('gtip_description', product_info.get('turkish', '')) if product_info else 'Tanımlanamadı',
            'Tanımlandı': is_defined
        })
        
        time.sleep(0.05)  # Daha kısa bekleme
    
    if products:
        df = pd.DataFrame(products)
        return df, None
    else:
        return None, "Faturada tanımlanabilir ürün bulunamadı"

def process_invoice(file_path):
    """Invoice dosyasını işle (PDF, CSV veya Excel)"""
    try:
        if file_path.endswith('.pdf'):
            return process_pdf_invoice(file_path)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            return df, None
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
            return df, None
        else:
            return None, "Desteklenmeyen dosya formatı"
    except Exception as e:
        return None, str(e)

@app.route('/')
def index():
    return render_template('index_final.html')

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
    product_name = data.get('product_name', '')  # Fatura ismini al
    
    if not item_num:
        return jsonify({'error': 'Item number boş olamaz'}), 400
    
    product_info = get_trek_product_info(item_num, product_name)
    
    if product_info:
        return jsonify({
            'success': True,
            'product': {
                'sku': item_num,
                'name': product_info.get('name', ''),
                'turkish': product_info.get('turkish', ''),
                'gtip_description': product_info.get('gtip_description', product_info.get('turkish', ''))
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Ürün tanımlanamadı'
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)