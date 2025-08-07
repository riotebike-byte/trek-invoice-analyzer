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
    """PDF dosyasından item number'ları çıkar - Optimized with memory management"""
    all_text = []
    tables_data = []
    pdf = None
    
    try:
        # Use context manager for proper resource cleanup
        pdf = pdfplumber.open(file_path)
        
        # Process pages in batches to manage memory
        total_pages = len(pdf.pages)
        batch_size = min(5, total_pages)  # Process max 5 pages at a time
        
        for batch_start in range(0, total_pages, batch_size):
            batch_end = min(batch_start + batch_size, total_pages)
            
            for page_num in range(batch_start, batch_end):
                page = pdf.pages[page_num]
                
                # Extract text with timeout protection
                try:
                    text = page.extract_text()
                    if text and len(text.strip()) > 0:
                        all_text.append(text)
                except Exception as page_error:
                    print(f"Page {page_num + 1} text extraction error: {page_error}")
                    continue
                
                # Extract tables with error handling
                try:
                    tables = page.extract_tables()
                    for table in tables:
                        if table and len(table) > 0:
                            tables_data.append({
                                'page': page_num + 1,
                                'data': table
                            })
                except Exception as table_error:
                    print(f"Page {page_num + 1} table extraction error: {table_error}")
                    continue
                
                # Force garbage collection between pages for large PDFs
                if page_num % 10 == 0:
                    import gc
                    gc.collect()
                    
    except Exception as e:
        print(f"PDF okuma hatası: {e}")
        return []
    finally:
        # Ensure PDF is properly closed
        if pdf:
            try:
                pdf.close()
            except:
                pass
    
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
            r'(?:Item\s*(?:Number|#|No\.?)?[:]\s*)([A-Z0-9]{4,8})',
            r'(?:SKU[:]\s*)([A-Z0-9]{4,8})',
            r'(?:Code[:]\s*)([A-Z0-9]{4,8})',
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
    """Fatura ürün isminden otomatik kategori belirle - Enhanced detection"""
    if not product_name:
        return None
        
    name_upper = product_name.upper()
    
    # Multiple analysis approaches for better accuracy
    # 1. First 3 characters
    first_3 = name_upper[:3] if len(name_upper) >= 3 else name_upper
    
    # 2. Find 3-letter abbreviations anywhere in the name
    three_letter_matches = re.findall(r'\b[A-Z]{3}\b', name_upper)
    
    # 3. Common bike part keywords
    keywords_in_name = [word.upper() for word in name_upper.split() if len(word) >= 3]
    
    # Enhanced 3-letter abbreviation detection
    all_candidates = [first_3] + three_letter_matches + [word[:3] for word in keywords_in_name if len(word) >= 3]
    
    # Check all candidates for matches
    for candidate in all_candidates:
        if candidate == 'SAD':  # SADDLE
            return {
                "name": f"Bontrager Sele - {product_name}",
                "category": "Bisiklet Selesi",
                "product_type": "Bisiklet Selesi", 
                "subcategory": "Sele",
                "turkish": "Bisiklet selesi",
                "gtip_description": "Bisiklet selesi (oturma yeri)",
                "series": "Bontrager"
            }
    
        elif candidate == 'CHN':  # CHAIN
            return {
                "name": f"Trek Zincir - {product_name}",
                "category": "Bisiklet Vites Sistemi",
                "product_type": "Bisiklet Zinciri",
                "subcategory": "Zincir",
                "turkish": "Bisiklet zinciri",
                "gtip_description": "Bisiklet zinciri",
                "series": "Trek"
            }
    
        elif candidate == 'PED':  # PEDAL
            return {
                "name": f"Trek Pedal - {product_name}",
                "category": "Bisiklet Pedalı",
                "product_type": "Bisiklet Pedalı",
                "subcategory": "Pedal",
                "turkish": "Bisiklet pedalı",
                "gtip_description": "Bisiklet pedalı",
                "series": "Trek"
            }
    
        elif candidate == 'GRP':  # GRIP
            return {
                "name": f"Bontrager Tutacak - {product_name}",
                "category": "Bisiklet Aksesuarı",
                "product_type": "Gidon Tutacağı",
                "subcategory": "Grip/Tutacak",
                "turkish": "Gidon tutacağı/grip",
                "gtip_description": "Bisiklet gidon tutacağı",
                "series": "Bontrager"
            }
    
        elif candidate == 'HAN' or candidate == 'HBR':  # HANDLEBAR
            return {
                "name": f"Trek Gidon - {product_name}",
                "category": "Bisiklet Gidon",
                "product_type": "Bisiklet Gidon",
                "subcategory": "Gidon",
                "turkish": "Bisiklet gidonu",
                "gtip_description": "Bisiklet gidonu",
                "series": "Trek"
            }
    
        elif candidate == 'STE':  # STEM
            return {
                "name": f"Trek Potans - {product_name}",
                "category": "Bisiklet Potansı",
                "product_type": "Bisiklet Potansı",
                "subcategory": "Potans",
                "turkish": "Bisiklet potansı/stem",
                "gtip_description": "Bisiklet potansı",
                "series": "Trek"
            }
    
        elif candidate == 'TIR':  # TIRE
            return {
                "name": f"Trek Lastik - {product_name}",
                "category": "Bisiklet Tekerlek/Lastik",
                "product_type": "Bisiklet Lastiği",
                "subcategory": "Lastik",
                "turkish": "Bisiklet lastiği",
                "gtip_description": "Bisiklet lastiği",
                "series": "Trek"
            }
    
        elif candidate == 'WHL':  # WHEEL
            return {
                "name": f"Trek Tekerlek - {product_name}",
                "category": "Bisiklet Tekerlek/Lastik",
                "product_type": "Bisiklet Tekerleği",
                "subcategory": "Tekerlek",
                "turkish": "Bisiklet tekerleği",
                "gtip_description": "Bisiklet tekerleği",
                "series": "Trek"
            }
    
        elif candidate == 'BRK':  # BRAKE
            return {
                "name": f"Trek Fren - {product_name}",
                "category": "Bisiklet Fren Sistemi",
                "product_type": "Bisiklet Fren",
                "subcategory": "Fren",
                "turkish": "Bisiklet fren sistemi",
                "gtip_description": "Bisiklet fren sistemi",
                "series": "Trek"
            }
    
        elif candidate == 'LCK':  # LOCK
            return {
                "name": f"Bontrager Kilit - {product_name}",
                "category": "Bisiklet Güvenlik",
                "product_type": "Bisiklet Kilidi",
                "subcategory": "Kilit",
                "turkish": "Bisiklet kilidi",
                "gtip_description": "Bisiklet kilidi (güvenlik ekipmanı)",
                "series": "Bontrager"
            }
    
        elif candidate == 'LIT' or candidate == 'LED' or candidate == 'LMP':  # LIGHT
            return {
            "name": f"Trek Işık - {product_name}",
            "category": "Bisiklet Aydınlatması",
            "product_type": "Bisiklet Işığı",
            "subcategory": "Aydınlatma",
            "turkish": "Bisiklet ışığı/aydınlatma sistemi",
            "gtip_description": "Bisiklet ışığı (aydınlatma ekipmanı)",
            "series": "Trek"
        }
    
    # Enhanced bottle cage detection
    elif (candidate == 'BTL' or candidate == 'CGE' or candidate == 'WAT' or candidate == 'BOT' or
          any(word in name_upper for word in ['BOTTLE', 'BTL', 'CAGE', 'WATER', 'HOLDER'])):
        return {
            "name": f"Bontrager Şişe Tutucu - {product_name}",
            "category": "Bisiklet Aksesuarı",
            "product_type": "Şişe Tutucusu",
            "subcategory": "Su Şişesi Tutucusu",
            "turkish": "Bisiklet su şişesi tutucusu",
            "gtip_description": "Bisiklet su şişesi tutucusu",
            "series": "Bontrager"
        }
        
        # Additional 3-letter patterns for common bike parts
        bike_part_patterns = {
            'CHN': {'category': 'Bisiklet Vites Sistemi', 'type': 'Bisiklet Zinciri', 'turkish': 'Bisiklet zinciri'},
            'GER': {'category': 'Bisiklet Vites Sistemi', 'type': 'Vites Sistemi', 'turkish': 'Bisiklet vites sistemi'},
            'DER': {'category': 'Bisiklet Vites Sistemi', 'type': 'Derailleur', 'turkish': 'Bisiklet derailleur'},
            'CAS': {'category': 'Bisiklet Vites Sistemi', 'type': 'Kaset', 'turkish': 'Bisiklet kaset'},
            'SPK': {'category': 'Bisiklet Tekerlek', 'type': 'Jant Teli', 'turkish': 'Bisiklet jant teli'},
            'VAL': {'category': 'Bisiklet Parçası', 'type': 'Valf', 'turkish': 'Bisiklet valf'},
            'CAP': {'category': 'Bisiklet Parçası', 'type': 'Kapak', 'turkish': 'Bisiklet kapak'},
            'BAR': {'category': 'Bisiklet Gidon', 'type': 'Gidon', 'turkish': 'Bisiklet gidonu'},
            'STP': {'category': 'Bisiklet Parçası', 'type': 'Stop', 'turkish': 'Bisiklet durdurucu'},
            'MTB': {'category': 'Bisiklet Parçası', 'type': 'Dağ Bisikleti Parçası', 'turkish': 'Dağ bisikleti parçası'}
        }
        
        if candidate in bike_part_patterns:
            pattern = bike_part_patterns[candidate]
            return {
                "name": f"Trek {pattern['type']} - {product_name}",
                "category": pattern['category'],
                "product_type": pattern['type'],
                "subcategory": pattern['type'],
                "turkish": pattern['turkish'],
                "gtip_description": pattern['turkish'],
                "series": "Trek"
            }
    
    # No match found, return None to try other methods
    return None

def extract_product_names_from_pdf(file_path, item_numbers):
    """PDF'den item number'lara karşılık gelen ürün adlarını çıkar - Optimized"""
    product_names = {}
    pdf = None
    
    # Early return for empty item_numbers
    if not item_numbers:
        return product_names
    
    # Convert item_numbers to set for faster lookups
    item_set = set(str(item).strip() for item in item_numbers)
    
    try:
        pdf = pdfplumber.open(file_path)
        
        # Process only first 3 pages for product names (performance optimization)
        max_pages = min(3, len(pdf.pages))
        
        for page_idx in range(max_pages):
            page = pdf.pages[page_idx]
            
            # Text processing with error handling
            try:
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    
                    # Optimized line processing
                    for line in lines:
                        line_clean = line.strip()
                        if len(line_clean) < 5:  # Skip very short lines
                            continue
                            
                        # Check if any item number is in this line
                        for item_num in item_set:
                            if item_num in line_clean and item_num not in product_names:
                                # Extract product name more efficiently
                                parts = line_clean.split(item_num, 1)
                                if len(parts) > 1:
                                    product_name = parts[1].strip()
                                    # Clean and validate product name
                                    product_name = re.sub(r'^[^\w\s]+', '', product_name)
                                    words = product_name.split()[:5]  # First 5 words only
                                    product_name = ' '.join(words).strip()
                                    
                                    if len(product_name) > 3 and not product_name.isdigit():
                                        product_names[item_num] = product_name
                                        
                                        # Auto-categorize with logging
                                        auto_category = analyze_product_name_for_category(item_num, product_name)
                                        if auto_category:
                                            print(f"Auto-categorized: {item_num} - {product_name[:30]}...")
            except Exception as text_error:
                print(f"Text extraction error on page {page_idx + 1}: {text_error}")
                continue
                
            # Table processing with optimization
            try:
                tables = page.extract_tables()
                if tables:
                    for table in tables[:2]:  # Process only first 2 tables per page
                        if table:
                            for row in table[:20]:  # Process only first 20 rows
                                if row:
                                    # Vectorized search in row
                                    for i, cell in enumerate(row):
                                        if cell and any(item in str(cell) for item in item_set):
                                            # Find corresponding product name in same row
                                            for j, other_cell in enumerate(row):
                                                if (j != i and other_cell and 
                                                    len(str(other_cell)) > 5 and 
                                                    not str(other_cell).isdigit()):
                                                    
                                                    # Match item with product name
                                                    for item_num in item_set:
                                                        if (item_num in str(cell) and 
                                                            item_num not in str(other_cell) and
                                                            item_num not in product_names):
                                                            product_names[item_num] = str(other_cell).strip()
                                                            break
                                                    break
                                            break
            except Exception as table_error:
                print(f"Table extraction error on page {page_idx + 1}: {table_error}")
                continue
                
    except Exception as e:
        print(f"Ürün adı çıkarma hatası: {e}")
    finally:
        # Proper cleanup
        if pdf:
            try:
                pdf.close()
            except:
                pass
    
    print(f"Extracted {len(product_names)} product names from PDF")
    return product_names

def extract_invoice_number(file_path):
    """Dosya adından veya PDF içeriğinden fatura numarasını çıkar - Optimized"""
    # First try filename (faster)
    filename = os.path.basename(file_path)
    
    # Remove timestamp from filename
    filename_clean = re.sub(r'^\d{8}_\d{6}_', '', filename)
    filename_clean = re.sub(r'\.(pdf|PDF)$', '', filename_clean)
    
    # Enhanced invoice number patterns
    invoice_patterns = [
        r'Invoice[_\s#-]*(\d+)',
        r'INV[_\s#-]*(\d+)',
        r'Fatura[_\s#-]*(\d+)',
        r'Bill[_\s#-]*(\d+)',
        r'(\d{6,})',  # 6+ digit numbers
        r'([A-Z]{2,}\d{4,})',  # Alpha-numeric invoice numbers
    ]
    
    # Try filename patterns first
    for pattern in invoice_patterns:
        match = re.search(pattern, filename_clean, re.IGNORECASE)
        if match:
            invoice_num = match.group(1) if match.groups() else match.group(0)
            if len(invoice_num) >= 4:  # Minimum length validation
                return invoice_num
    
    # Try PDF content only if filename doesn't work
    pdf = None
    try:
        pdf = pdfplumber.open(file_path)
        if pdf.pages:
            # Only check first page for invoice number
            first_page_text = pdf.pages[0].extract_text()
            if first_page_text:
                # Search in first 500 characters only (header area)
                header_text = first_page_text[:500]
                for pattern in invoice_patterns:
                    match = re.search(pattern, header_text, re.IGNORECASE)
                    if match:
                        invoice_num = match.group(1) if match.groups() else match.group(0)
                        if len(invoice_num) >= 4:
                            return invoice_num
    except Exception as e:
        print(f"Error extracting invoice number from PDF: {e}")
    finally:
        if pdf:
            try:
                pdf.close()
            except:
                pass
    
    # Fallback to cleaned filename
    return filename_clean[:50]  # Limit length

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
            # Trek veritabanından bilgi al
            product_info = get_trek_product_info(item_num)
            
            # Enhanced identification logic - more precise detection
            is_defined = False
            if product_info:
                # Check multiple criteria for proper identification
                name = product_info.get('name', '')
                category = product_info.get('category', '')
                
                # Considered properly defined if:
                # 1. It's in the main database (starts with specific product names)
                # 2. Has a specific category (not generic "Trek Ürünü")
                # 3. Has detailed Turkish description
                if (item_num in TREK_SKU_DATABASE or
                    not name.startswith('Trek Ürünü #') or
                    category not in ['Trek Ürünü', ''] or
                    product_info.get('series', '') != 'Trek'):
                    is_defined = True
                
                # Additional check: if it has specific subcategory info
                subcategory = product_info.get('subcategory', '')
                if subcategory and subcategory not in ['Belirlenmemiş', 'Genel Bisiklet']:
                    is_defined = True
        
        products.append({
            'Fatura Numarası': invoice_number,
            'SKU': item_num,
            'Faturadaki İsmi': invoice_name,
            'Türkçe Tanım': product_info.get('turkish', '') if product_info else 'Tanımlanamadı',
            'GTİP Tanımı': product_info.get('gtip_description', product_info.get('turkish', '')) if product_info else 'Tanımlanamadı',
            'Tanımlandı': is_defined,
            'Kategori': product_info.get('category', '') if product_info else '',
            'Seri': product_info.get('series', '') if product_info else ''
        })
        
        # Reduced sleep time for better performance
        time.sleep(0.01)
    
    if products:
        df = pd.DataFrame(products)
        return df, None
    else:
        return None, "Faturada tanımlanabilir ürün bulunamadı"

def process_invoice(file_path):
    """Invoice dosyasını işle (PDF, CSV veya Excel) - Enhanced error handling"""
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            return None, "Dosya bulunamadı"
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return None, "Dosya boş"
        
        if file_size > 50 * 1024 * 1024:  # 50MB
            return None, "Dosya boyutu çok büyük"
        
        # Process based on file type
        if file_path.lower().endswith('.pdf'):
            return process_pdf_invoice(file_path)
        elif file_path.lower().endswith('.csv'):
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='latin-1')
            return df, None
        elif file_path.lower().endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(file_path)
            except Exception as excel_error:
                return None, f"Excel dosyası okuma hatası: {str(excel_error)}"
            return df, None
        else:
            return None, "Desteklenmeyen dosya formatı (.pdf, .csv, .xlsx, .xls desteklenmektedir)"
            
    except MemoryError:
        return None, "Yetersiz bellek. Daha küçük dosya deneyin."
    except PermissionError:
        return None, "Dosya erişim izni sorunu"
    except Exception as e:
        return None, f"Dosya işleme hatası: {str(e)}"

@app.route('/')
def index():
    return render_template('index_final.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    filepath = None
    output_path = None
    
    try:
        # Validate request
        if 'file' not in request.files:
            return jsonify({'error': 'Dosya bulunamadı'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Dosya seçilmedi'}), 400
        
        # Validate file size
        if request.content_length and request.content_length > app.config['MAX_CONTENT_LENGTH']:
            return jsonify({'error': 'Dosya boyutu çok büyük (max 50MB)'}), 413
        
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.csv', '.xlsx', '.xls')):
            return jsonify({'error': 'Desteklenmeyen dosya formatı. PDF, CSV veya Excel dosyası yükleyin.'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
        except Exception as save_error:
            return jsonify({'error': f'Dosya kaydedilirken hata: {str(save_error)}'}), 500
        
        # Process invoice with timeout protection
        try:
            df, error = process_invoice(filepath)
        except Exception as process_error:
            return jsonify({'error': f'Dosya işleme hatası: {str(process_error)}'}), 500
        
        if error:
            return jsonify({'error': f'Dosya işlenirken hata: {error}'}), 500
        
        if df is None or df.empty:
            return jsonify({'error': 'Faturada işlenebilir ürün bulunamadı. PDF formatını kontrol edin.'}), 404
        
        # Enhanced result preparation
        defined_count = df['Tanımlandı'].sum() if 'Tanımlandı' in df.columns else 0
        undefined_count = len(df) - defined_count
        
        result = {
            'filename': filename,
            'total_rows': len(df),
            'defined_skus': int(defined_count),
            'undefined_skus': int(undefined_count),
            'columns': list(df.columns),
            'data': df.to_dict('records'),
            'file_type': 'PDF' if filename.endswith('.pdf') else 'Excel/CSV',
            'success_rate': f"{(defined_count/len(df)*100):.1f}%" if len(df) > 0 else "0%"
        }
        
        # Save processed file with error handling
        try:
            output_filename = f"translated_{filename.split('.')[-2]}.xlsx"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            
            # Use engine='openpyxl' for better compatibility
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Trek Products')
                
            result['output_file'] = output_filename
        except Exception as excel_error:
            print(f"Excel kaydetme hatası: {excel_error}")
            # Continue without Excel file
            result['excel_error'] = "Excel dosyası oluşturulamadı"
        
        return jsonify(result)
        
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500
    
    finally:
        # Cleanup temporary files if there was an error
        import gc
        gc.collect()  # Force garbage collection

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
    
    product_info = get_trek_product_info(item_num)
    
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