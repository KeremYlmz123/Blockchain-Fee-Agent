import requests

# API KEY'inizi buraya yapıştırın
API_KEY = ""

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

print("📡 Kullanılabilir modeller Google'dan çekiliyor...")

try:
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ HESABINIZA TANIMLI MODELLER:")
        print("-" * 40)
        found_any = False
        for model in data.get('models', []):
            # Sadece içerik üretimine (generateContent) izin verenleri listeleyelim
            if "generateContent" in model.get("supportedGenerationMethods", []):
                print(f"👉 Model Adı: {model['name']}")
                found_any = True
        
        if not found_any:
            print("⚠️ Hiçbir model 'generateContent' özelliğini desteklemiyor.")
            
    else:
        print(f"❌ HATA: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"HATA: {e}")