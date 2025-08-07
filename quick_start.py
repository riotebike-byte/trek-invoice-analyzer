#!/usr/bin/env python3
import os
import webbrowser
import time

# API key check - environment variable'dan al
if not os.environ.get('OPENAI_API_KEY'):
    print("❌ HATA: OPENAI_API_KEY environment variable gerekli!")
    print("Kullanım: export OPENAI_API_KEY='your-key-here' && python3 quick_start.py")
    exit(1)

print("🚀 TREK INVOICE ANALYZER BAŞLATILIYOR...")
print("=" * 50)

try:
    from flask import Flask, render_template, request, jsonify, send_from_directory
    import threading
    
    # Import main app
    from app_final import app
    
    def open_browser():
        time.sleep(2)
        print("🌐 Tarayıcı otomatik açılıyor...")
        webbrowser.open('http://localhost:9999')
    
    # Start browser thread
    threading.Thread(target=open_browser).start()
    
    print("📱 Manuel URL: http://localhost:9999")
    print("⚡ Uygulama hazır!")
    
    # Start Flask
    app.run(host='0.0.0.0', port=9999, debug=False)
    
except Exception as e:
    print(f"❌ HATA: {e}")
    print("\n🔧 MANUEL ÇÖZÜM:")
    print("1. Terminalde: python3 app_final.py")
    print("2. Tarayıcıda: http://localhost:5000")