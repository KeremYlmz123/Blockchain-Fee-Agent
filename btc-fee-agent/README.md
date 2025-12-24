# btc-fee-agent

FastAPI tabanlı, mempool.space verisiyle çalışan deterministik bir Bitcoin ücret öneri ve tahmin servisi; basit HTML/JS frontend ile beraber gelir. Cüzdan, private key veya akıllı sözleşme yok; yalnızca zincir dışı karar destek.

## Klasör yapısı
- `backend/`: FastAPI uygulaması, agent mantığı, opsiyonel Gemini LLM açıklamaları.
- `frontend/`: Statik HTML/JS arayüzü.
- `data/`: Cache ve çıktı dosyaları (history, plot).

## Çevre değişkenleri
1. `.env.example` dosyasını `.env` olarak kopyalayın.
2. Gerekirse `MEMPOOL_BASE_URL` vb. ayarları değiştirin.
3. Opsiyonel LLM için:
   ```env
   GEMINI_API_KEY=
   GEMINI_MODEL=gemini-1.5-flash-latest
   ```
   Anahtar yoksa sistem deterministik açıklamalarla çalışır.

## Kurulum (Windows)
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Çalıştırma
- Backend (proje kökünden):
  ```powershell
  python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
  ```
- Frontend:
  ```powershell
  cd frontend
  python -m http.server 5500
  ```

## Uçlar
- Sağlık: `GET http://127.0.0.1:8000/health`
- Öneri: `GET http://127.0.0.1:8000/recommend?priority=fast|medium|slow&explain=none|llm`
- Tahmin (kullanıcı ücreti): `GET http://127.0.0.1:8000/estimate?fee=25&explain=none|llm`
- Karşılaştırma: `GET http://127.0.0.1:8000/compare?explain=none|llm` (fast/medium/slow + overpay delta)
- Canlı durum: `GET http://127.0.0.1:8000/live/status` (10 sn’de bir güncellenen snapshot)
- Geçmiş: `GET http://127.0.0.1:8000/history` (son 10 kayıt)
- Swagger: `http://127.0.0.1:8000/docs`

## Mimari kısa özet
- Arka plan görevi her 10 sn’de mempool.space’den `fees` + `mempool` çeker; başarılı veri `LATEST` state’e ve `data/cache.json`’a yazılır. Hata durumunda cache fallback kullanılır (`cache_used=true`).
- Agent deterministik: observe → decide → explain; mempool yoğunluğuna göre 1.0–1.3 çarpanı uygular, kurallar/sinyaller/confidence/risk üretir. Preset’ler fast/medium/slow ve custom fee tahmini desteklenir; ETA aralıkları, agent_summary ve what_if_hint döner.
- LLM opsiyonel: `?explain=llm` ile Gemini çağrılır; başarısız veya anahtar yoksa yerel açıklama döner (LLM yalnızca açıklama için, karar için değil).
- Network State: canlı veriden calm/moderate/congested sınıflaması ve Türkçe not; compare verdict ve overpay delta içeren çıktı.
- Frontend 3 sn’de bir `/live/status` çeker; preset seçimi, custom fee girişi, explain modu (none/llm), `/recommend`, `/estimate`, `/compare` çağrılarını yapar; kartlarda fee/ETA aralığı/confidence/risk/agent_summary/what_if_hint/explanation/rules/llm_explanation gösterilir; history sekmesi son 10 kaydı ve insight’ı gösterir.

## Güvenlik notu
- Cüzdan veya private key tutulmaz; yalnızca mempool.space’e okuma istekleri yapılır.
- LLM isteği yapılıyorsa sadece açıklama amaçlı metin gönderilir; anahtar yoksa devre dışı kalır.
