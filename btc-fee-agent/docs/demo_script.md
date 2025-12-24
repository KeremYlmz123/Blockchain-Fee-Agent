# 3 Dakikalık Demo Akışı

## Hazırlık
- Backend: `uvicorn backend.main:app --reload` (http://127.0.0.1:8000)
- Frontend: `cd frontend && python -m http.server 5500` (http://127.0.0.1:5500)
- Tarayıcıda frontend’i aç, Swagger için ayrı sekmede http://127.0.0.1:8000/docs hazır dursun.

## Adımlar (≈3 dakika)
1. **Açılış (15 sn)**  
   - Başlık: “Bitcoin Fee Advisor — mempool verisine göre anlık öneri”.  
   - Kısa not: “API kapalı olsa bile cache kullanarak yanıt veriyor.”

2. **Swagger Health Check (20 sn)**  
   - Swagger sekmesinde `/health` GET çalıştır; 200 ve `{"status":"ok"}` çıktısını göster.

3. **Tek Öneri (60 sn)**  
   - Frontend sekmesinde dropdown “Normal” seçiliyken **Get Recommendation** butonuna bas.  
   - Kartta gösterilecekler: fee, blocks, minutes, mempool tx, confidence badge, cache badge (varsa).  
   - Explanation maddelerinden 3+ gerekçeyi oku; “cache used” satırına değin.

4. **Compare (60 sn)**  
   - **Compare All** butonuna bas.  
   - Üç kartın yan yana geldiğini göster (Fast/Normal/Cheap).  
   - Farklı fee, blocks, ETA ve confidence değerlerine dikkat çek.

5. **Cache/Offline Senaryosu (25 sn)**  
   - İstersen backend’i durdurup (veya ağ kablosunu çekip) tekrar **Get Recommendation** de.  
   - Yanıtın yine geldiğini, kartta “cache” badge’inin belirdiğini göster.

6. **Kapanış (20 sn)**  
   - `data/cache.json` sayesinde offline yanıt; env ile timeout/retry ayarları değiştirilebilir.  
   - API yüzeyi: `/health`, `/recommend?priority=fast|normal|cheap`, `/compare`.
