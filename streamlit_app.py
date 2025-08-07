#!/usr/bin/env python3
import streamlit as st
import os
import pandas as pd

# Set environment variable (get from environment)
if not os.environ.get('OPENAI_API_KEY'):
    st.error("❌ OPENAI_API_KEY environment variable gerekli!")
    st.stop()

# Import functions
from trek_sku_database import get_trek_product_info

st.set_page_config(page_title="Trek Invoice Analyzer", page_icon="🚲", layout="wide")

st.title("🚲 Trek Invoice Analyzer")
st.markdown("AI-powered Trek bicycle invoice processing with OpenAI GPT-4o")

# File upload
uploaded_file = st.file_uploader("PDF Fatura Yükle", type="pdf")

if uploaded_file is not None:
    st.success(f"✅ Dosya yüklendi: {uploaded_file.name}")
    
    if st.button("🔍 Faturayı Analiz Et", type="primary"):
        with st.spinner("PDF analiz ediliyor..."):
            try:
                # Import PDF processing functions
                from app_final import extract_item_numbers_from_pdf, extract_product_names_from_pdf
                
                # Save uploaded file temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    temp_path = tmp_file.name
                
                # Extract data
                st.info("📄 PDF'den SKU'lar çıkarılıyor...")
                item_numbers = extract_item_numbers_from_pdf(temp_path)
                
                st.info("📝 Ürün isimleri çıkarılıyor...")  
                product_names = extract_product_names_from_pdf(temp_path, item_numbers)
                
                st.success(f"✅ {len(item_numbers)} SKU bulundu!")
                
                # Process each SKU
                results = []
                progress_bar = st.progress(0)
                
                for i, sku in enumerate(item_numbers):
                    progress_bar.progress((i + 1) / len(item_numbers))
                    
                    st.info(f"🔍 Analiz ediliyor: {sku}")
                    
                    invoice_name = product_names.get(sku, '')
                    product_info = get_trek_product_info(sku, invoice_name)
                    
                    result = {
                        "Fatura Numarası": "INV-001",  # Default
                        "SKU": sku,
                        "Faturadaki İsmi": invoice_name,
                        "Türkçe Tanım": product_info.get('turkish', 'Tanımlanamadı') if product_info else 'Tanımlanamadı',
                        "GTİP Tanımı": product_info.get('gtip_description', 'Tanımlanamadı') if product_info else 'Tanımlanamadı',
                        "Tanımlandı": bool(product_info)
                    }
                    results.append(result)
                
                # Display results
                st.success("🎉 Analiz tamamlandı!")
                
                df = pd.DataFrame(results)
                
                # Color coding
                def highlight_undefined(row):
                    if not row['Tanımlandı']:
                        return ['background-color: #ffcccc'] * len(row)
                    return [''] * len(row)
                
                styled_df = df.drop('Tanımlandı', axis=1).style.apply(highlight_undefined, axis=1)
                st.dataframe(styled_df, use_container_width=True)
                
                # Stats
                total = len(results)
                defined = sum(1 for r in results if r['Tanımlandı'])
                undefined = total - defined
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Toplam SKU", total)
                col2.metric("Tanımlandı", defined) 
                col3.metric("Tanımlanamadı", undefined)
                
                # Download CSV
                csv = df.drop('Tanımlandı', axis=1).to_csv(index=False)
                st.download_button("📥 CSV İndir", csv, "trek_analysis.csv", "text/csv")
                
                # Cleanup
                os.unlink(temp_path)
                
            except Exception as e:
                st.error(f"❌ Hata: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

else:
    st.info("👆 PDF dosyanızı yükleyiniz")
    
    # Example
    st.markdown("### 📋 Nasıl Kullanılır:")
    st.markdown("""
    1. **PDF Yükle:** Trek fatura PDF'ini seçin
    2. **Analiz Et:** Butona tıklayın  
    3. **Sonuçları Gör:** 5 sütunlu tablo
    4. **CSV İndir:** Sonuçları kaydedin
    
    **Özellikler:**
    - 🔍 Trek website lookup
    - 🤖 OpenAI GPT-4o analizi  
    - 🇹🇷 Türkçe çeviriler
    - 📋 GTİP tanımları
    - 🎨 Kırmızı vurgu (tanımlanamayan)
    """)