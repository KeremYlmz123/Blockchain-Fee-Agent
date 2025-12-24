import requests

# 1. API KEY'inizi buraya tırnak içine yapıştırın (Env dosyasından değil, direkt buraya)
MY_API_KEY = ""

# 2. Test edilecek model (En stabil olanı)
MODEL_NAME = "gemini-2.5-flash-lite"

url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

body = {
    "contents": [{
        "parts": [{"text": "Merhaba, bu bir test mesajıdır. Çalışıyorsan 'API Çalışıyor' de."}]
    }]
}

print(f"📡 İstek gönderiliyor: {url}")
print("-" * 30)

try:
    response = requests.post(url, params={"key": MY_API_KEY}, json=body, timeout=10)
    
    # Hata varsa detayını görelim
    if response.status_code != 200:
        print(f"❌ HATA KODU: {response.status_code}")
        print(f"❌ HATA MESAJI: {response.text}")
    else:
        data = response.json()
        print("✅ BAŞARILI! Cevap:")
        print(data['candidates'][0]['content']['parts'][0]['text'])

except Exception as e:
    print(f"🔥 KRİTİK HATA: {e}")