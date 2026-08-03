# DJ AI OS — Neon Performance System

**Gelecekten gelmiş bir DJ asistanı.** 6.957 parçalık arşivinizi yapay zeka ile yönetin, analiz edin ve profesyonel setler oluşturun.

## 🚀 Özellikler

### 🎛️ Neon Performance Cockpit (DJ Booth)
- **Spinning Vinyl** — dönen plak animasyonu, groove halkası, BPM label
- **BPM Scope** — osiloskop tarzı beat dalga çizimi, beat grid
- **Energy Orb** — pulsating enerji topu (mor→cyan→yeşil gradyan)
- **Harmonic Wheel** — interaktif12 dilim Camelot çarkı (tıkla ve uyumlu anahtarı bul)
- **VU Meter** — analog dijital VU meter, dB scala
- **Crossfader** — drag & drop crossfader (A→B gradient)
- **Set Energy Curve** — set boyunca enerji eğrisi (warmup→groove→peak→cool)

### 🧠 Gerçek AI Sınıflandırıcı
- **MFCC Classifier** — sklearn GradientBoostingClassifier ile ses tabanlı tür tahmini
- **Genre Knowledge Base** — 8 ana tür ailesi, 50+ alt tür, wedding/event desteği
- **Tempo Intelligence** — yarım/çift tempo düzeltmesi, Camelot anahtarı tespiti
- **AI Ear** — mixability, vocal risk, intro/outro analizi
- **DJ Heart** — duygu haritası, crowd moment, emotional color

### 🗄️ Arşiv Güveni
- **Fingerprint Cache** — JSON'a kaydedilen parmak izi indeksi, **9x hızlanma**
- **Version Intelligence** — Extended/Radio Edit/Remix/Acapella/Instrumental tespiti
- **Quarantine Flow** — dry-run + onaylı taşıma + geri getirme (SİLME YOK)
- **Archive Guardian** — zero-byte, legacy folder, tempo anomaly, duplicate detection

### ⭐ Kritik DJ Özellikleri
- **BPM Eşleştirme** — Deck A/B arası fark, pitch önerisi, harmonik kontrol
- **Harmonik Uyumluluk** — Camelot uyum kontrolü, set builder'a entegre
- **Enerji Akışı** — gerçek set verisiyle enerji eğrisi
- **Acil Kurtarma Crate** — enerji düşüşü, BPM monotonluk, harmonik atlama

### 🎁 Süprizler
- **Track DNA** — her parçaya benzersiz renkli barkod parmak izi
- **DJ Coach AI** — set sonrası S/A/B/C/D + Türkçe tavsiyeler
- **Library DNA Map** — 6957 parçalı scatter plot (enerji×parlaklık)
- **DJ Profile** — Style DNA fingerprint + stil analizi
- **Track Similarity Radar** — en benzer5 parçayı bul

### 📋 Set Araçları
- **Smart Playlist** — mekan bazlı enerji egrisi (Düğün/Kulüp/Festival/Lounge)
- **Set Recorder** — DJ kararlarını kaydet (çalınan/atlanan/geçiş)
- **Beat Grid Overlay** — waveform üzerinde beat çizgileri, phrase marker
- **Show Director** — segmentli gece planı + rescue crate
- **Remix Lab** — vocal ayırma, remix blueprint, FL mastering

## 🛠️ Kurulum

### Masaüstü Uygulaması (Tam)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Sadece Sunucu (Hafif)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-server.txt
uvicorn app.server.api:app --reload --port 8000
```

### Geliştirme Ortamı
```bash
pip install -r requirements-dev.txt
python tests/smoke_test.py
```

## 📁 Proje Yapısı

```
dj_ai_os/
├── app/
│   ├── ai/                    # Yapay zeka modülleri
│   │   ├── audio_analyzer.py  # librosa ile ses analizi (MFCC, enerji, key)
│   │   ├── music_ai.py        # Ana sınıflandırıcı (keyword + ML fallback)
│   │   ├── mfcc_classifier.py # sklearn GradientBoostingClassifier
│   │   ├── set_engine.py      # Set oluşturma motoru
│   │   ├── dj_coach.py        # Set sonrası koçluk
│   │   ├── emergency_crate.py # Acil kurtarma parçaları
│   │   ├── track_dna.py       # Parça DNA parmak izi
│   │   ├── track_similarity.py# Benzer parça bulucu
│   │   ├── dj_profile.py      # DJ stil profili
│   │   ├── smart_playlist.py  # Akıllı playlist şablonları
│   │   ├── set_recorder.py    # Set kaydı
│   │   ├── version_detector.py# Sürüm tespiti
│   │   └── ...                # (diğer AI modülleri)
│   ├── core/                  # Çekirdek sistem
│   │   ├── organizer.py       # Arşiv kopyalama + fingerprint cache
│   │   ├── archive_brain.py   # Arşiv sağlık raporları
│   │   ├── archive_auditor.py # Arşiv denetimi
│   │   ├── archive_reconciler.py # Duplicate temizlik + karantina
│   │   └── ...
│   ├── ui/                    # Arayüz
│   │   ├── main_window.py     # Ana pencere (~5500 satır)
│   │   ├── dj_widgets.py      #7 animasyonlu canvas widget
│   │   ├── dj_booth_view.py   # Tam ekran DJ kabini
│   │   ├── library_map.py     # Scatter plot visualization
│   │   ├── glass.py           # Neon Glass widget'ları
│   │   ├── theme.py           #41 tema token'ı
│   │   └── views/             # Çıkarılmış görünümler
│   ├── server/                # FastAPI sunucu
│   ├── license/               # Lisans yönetimi
│   └── cloud/                 # Cloud istemcileri
├── data/db/                   # SQLite veritabanı
├── legacy/                    # Eski/orphan modüller
├── scripts/                   # Geliştirme araçları
├── tests/                     #59 smoke test
└── requirements.txt           # Bağımlılıklar
```

## 🎨 Tasarım Sistemi — Neon Glass

Koyu cam estetiği + neon vurgular:
- **Cam yüzeyler**: `GLASS_BG`, `GLASS_BORDER`, `SURFACE_RAISED`
- **Parıltı**: `GLOW_ACCENT`, `GLOW_PURPLE`, `GLOW_BLUE`
- **Font ölçeği**: `F_H1` (30px) → `F_TINY` (8px)
- **Boşluk**: `SP1` (4px) → `SP6` (32px)

## 🔧 Kısayollar

| Kısayol | Aksiyon |
|---|---|
| `Ctrl+L` | Kütüphane yükle |
| `Ctrl+G` | Set oluştur |
| `Ctrl+B` | DJ Booth aç |
| `Ctrl+K` | Command Palette |
| `Ctrl+1/2` | Deck A/B'ye yükle |
| `Ctrl+M` | Auto-mix planı |
| `Space` | Play/Stop |
| `F5` | Görünümü yenile |

## 📊 Rakamlarla

| Metrik | Değer |
|---|---|
| Aktif modül |101 |
| Canvas widget |7 (animasyonlu) |
| Tema token |41 |
| Smoke test |59 |
| DB indeks |4 |
| DJ şablonu |4 |

## 🧪 Testler

```bash
python tests/smoke_test.py
# veya
python -m pytest tests/
```

59 test涵盖: sınıflandırma, arşiv güveni, set oluşturma, version tespiti, fingerprint cache, karantina, DJ koçu, track DNA, benzerlik, profil, akıllı playlist, set kaydı, BPM eşleştirme.

## 📄 Lisans

Proprietary — ASTRA Engineering
