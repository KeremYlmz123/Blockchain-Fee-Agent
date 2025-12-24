# Mimari Özeti

- **Bileşenler**:  
  - *Frontend*: Statik HTML/JS, tarayıcıdan FastAPI backend’e istek atar.  
  - *Backend*: FastAPI + requests + pydantic. Mempool verisini çeker, önceliğe göre ücret hesaplar, cache fallback sağlar.  
  - *Data*: `data/cache.json` cache ve ileride veri saklama için.  
  - *Off-chain AI agent*: `backend/agent.py` içindeki deterministik mantık; zincir dışı çalışır, mempool verisini kullanıp öneri üretir.

- **Veri Akışı**:  
  1. Frontend `GET /recommend` veya `GET /compare` çağırır.  
  2. Backend `data_fetcher` ile mempool.space API’ye istek yapar (timeout, retry, rate-limit). Başarısız olursa cache’den okur ve `cache_used=true` döner.  
  3. Agent, `fee_data` + `mempool_data` ile congestion multiplier uygular, fee/ETA/confidence hesaplar.  
  4. Yanıt Pydantic modelleriyle tiplenir ve Frontend kartlarda gösterir.

- **Neden smart contract yok?**  
  - Bu iş akışı tamamen off-chain veri (mempool) ve hesaplama gerektirir; zincir üstü durum değişimi yapılmaz.  
  - Hızlı yanıt ve düşük maliyet için merkeziyetsiz olmayan, hızlı ve deterministik bir servis yeterlidir.  
  - Zincir üstünde oracle, state değişimi veya fon transferi ihtiyacı yoktur; bu yüzden akıllı sözleşme eklemek maliyet ve karmaşıklık getirir, değer katmaz.

- **Güvenlik ve Gizlilik**:  
  - **Private key yok**: Uygulama imzalama veya fon hareketi yapmaz; cüzdan entegrasyonu bulunmaz.  
  - **Sadece okuma**: Mempool API’si yalnızca okuma istekleriyle kullanılır.  
  - **Timeout ve retry**: API çökse bile cache ile cevap verir; bekleme süreleri sınırlandırılır.  
  - **CORS kontrollü**: Frontend için CORS açık; başka alanlarda yalnızca okuma olduğu için risk sınırlı.  
  - **Deterministik mantık**: Aynı girdi aynı çıktıyı üretir; öngörülebilir davranış.

- **Arayüz**:  
  - Endpoints: `/health`, `/recommend?priority=fast|normal|cheap`, `/compare`.  
  - Pydantic modeller Swagger’da açıkça görülür; `CompareResponse` üç önceliği tek yanıtla döner.  
  - Frontend statik sunucudan (`python -m http.server 5500`) çalışır, backend’e `http://127.0.0.1:8000` üzerinden erişir.
