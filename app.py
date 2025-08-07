from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Klasörleri oluştur
os.makedirs('uploads', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Ürün tanımlamaları sözlüğü (genişletilebilir)
PRODUCT_TRANSLATIONS = {
    # Elektronik
    'laptop': 'Dizüstü Bilgisayar',
    'computer': 'Bilgisayar',
    'mouse': 'Fare',
    'keyboard': 'Klavye',
    'monitor': 'Monitör',
    'printer': 'Yazıcı',
    'scanner': 'Tarayıcı',
    'headphones': 'Kulaklık',
    'speaker': 'Hoparlör',
    'cable': 'Kablo',
    'charger': 'Şarj Cihazı',
    'battery': 'Batarya/Pil',
    'power bank': 'Taşınabilir Şarj Cihazı',
    'usb': 'USB',
    'hdmi': 'HDMI Kablosu',
    
    # Ofis Malzemeleri
    'paper': 'Kağıt',
    'pen': 'Kalem',
    'pencil': 'Kurşun Kalem',
    'notebook': 'Defter',
    'folder': 'Klasör',
    'stapler': 'Zımba',
    'scissors': 'Makas',
    'tape': 'Bant',
    'glue': 'Yapıştırıcı',
    'envelope': 'Zarf',
    
    # Mobilya
    'desk': 'Masa',
    'chair': 'Sandalye',
    'table': 'Masa',
    'shelf': 'Raf',
    'cabinet': 'Dolap',
    'drawer': 'Çekmece',
    
    # Temizlik
    'cleaning': 'Temizlik Malzemesi',
    'detergent': 'Deterjan',
    'soap': 'Sabun',
    'tissue': 'Kağıt Mendil',
    'towel': 'Havlu',
    
    # Yiyecek/İçecek
    'coffee': 'Kahve',
    'tea': 'Çay',
    'water': 'Su',
    'sugar': 'Şeker',
    'milk': 'Süt',
    'snack': 'Atıştırmalık',
    
    # Hizmetler
    'service': 'Hizmet',
    'maintenance': 'Bakım',
    'repair': 'Onarım',
    'shipping': 'Kargo/Nakliye',
    'delivery': 'Teslimat',
    'consultation': 'Danışmanlık',
    'training': 'Eğitim',
    'support': 'Destek',
    'license': 'Lisans',
    'subscription': 'Abonelik',
    
    # Genel
    'product': 'Ürün',
    'item': 'Kalem/Ürün',
    'unit': 'Adet',
    'piece': 'Adet',
    'box': 'Kutu',
    'package': 'Paket',
    'set': 'Set',
    'kit': 'Kit/Set'
}

def translate_product(description):
    """Ürün açıklamasını Türkçe'ye çevir"""
    if not description:
        return "Tanımsız Ürün"
    
    description_lower = str(description).lower()
    
    # Tam eşleşme kontrolü
    if description_lower in PRODUCT_TRANSLATIONS:
        return PRODUCT_TRANSLATIONS[description_lower]
    
    # Kısmi eşleşme kontrolü
    for eng, tr in PRODUCT_TRANSLATIONS.items():
        if eng in description_lower:
            return f"{tr} - {description}"
    
    # Eşleşme bulunamazsa orijinal açıklamayı döndür
    return f"[Çeviri Bulunamadı] {description}"

def process_invoice(file_path):
    """Invoice dosyasını işle ve Türkçe tanımlamaları ekle"""
    try:
        # Dosya uzantısına göre okuma
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            return None, "Desteklenmeyen dosya formatı"
        
        # Olası sütun isimleri
        description_columns = ['description', 'Description', 'DESCRIPTION', 
                             'item', 'Item', 'ITEM',
                             'product', 'Product', 'PRODUCT',
                             'name', 'Name', 'NAME',
                             'urun', 'Urun', 'URUN',
                             'aciklama', 'Aciklama', 'ACIKLAMA']
        
        # Açıklama sütununu bul
        desc_col = None
        for col in description_columns:
            if col in df.columns:
                desc_col = col
                break
        
        if not desc_col:
            # İlk string sütunu açıklama olarak kabul et
            for col in df.columns:
                if df[col].dtype == 'object':
                    desc_col = col
                    break
        
        if desc_col:
            # Türkçe tanımlamaları ekle
            df['Türkçe Tanım'] = df[desc_col].apply(translate_product)
            
            # Boş değerleri kontrol et
            df['Türkçe Tanım'].fillna('Tanımsız Ürün', inplace=True)
        
        return df, None
    except Exception as e:
        return None, str(e)

@app.route('/')
def index():
    return render_template('index.html')

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
            'data': df.to_dict('records')
        }
        
        # İşlenmiş dosyayı kaydet
        output_filename = f"translated_{filename.split('.')[-2]}.xlsx"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        df.to_excel(output_path, index=False)
        result['output_file'] = output_filename
        
        return jsonify(result)

@app.route('/download/<filename>')
def download_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/add_translation', methods=['POST'])
def add_translation():
    """Yeni çeviri ekle"""
    data = request.json
    eng = data.get('english', '').lower()
    tr = data.get('turkish', '')
    
    if eng and tr:
        PRODUCT_TRANSLATIONS[eng] = tr
        return jsonify({'success': True, 'message': 'Çeviri eklendi'})
    return jsonify({'success': False, 'message': 'Eksik bilgi'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)