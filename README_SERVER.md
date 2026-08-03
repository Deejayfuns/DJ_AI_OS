DJ AI OS - Server API

Bu doküman, geliştirdiğimiz basit FastAPI sunucusunun nasıl başlatılacağını ve Beatport
çekirdeği ile öneri uç noktalarının nasıl kullanılacağını açıklar.

Kurulum

1. Ortamı hazırla (tercih edilen: virtualenv)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-server.txt
```

(Masaüstü uygulaması için `pip install -r requirements.txt`; geliştirme araçları
için `pip install -r requirements-dev.txt` kullanılır.)

Çalıştırma

```bash
uvicorn app.server.api:app --reload --port 8000
```

Uç Noktalar (examples)

- GET /charts/top100 -> Beatport Top100 (scrape)
- POST /recommendations {"genre":"techno"} -> Basit öneriler
- GET /graph/summary -> Hafıza grafi özeti
- POST /graph/learn {"text":"yeni kelime örneği"} -> Graf hafızasına ekle

Notlar

- Beatport scraping, Beatport sitesinin markup'ına bağlıdır; markup değişirse parser güncellenmelidir.
- Üretim için resmi API/izin gereklidir; bu sadece prototip amaçlıdır.
