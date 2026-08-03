# Python, Demucs ve FFmpeg Kurulumu

Bu rehber Windows icin hazirlandi.

## 1. Python Kur

1. Resmi Python sayfasini ac: https://www.python.org/downloads/windows/
2. Windows 64-bit installer indir.
3. Kurulum ekraninda mutlaka `Add python.exe to PATH` secenegini isaretle.
4. `Install Now` ile kur.
5. PowerShell'i kapatip yeniden ac.
6. Kontrol et:

```powershell
py --version
python --version
py -m pip --version
```

Demucs kurulumunda sorun yasarsan Python 3.10 veya 3.11 daha guvenli bir secimdir.

## 2. Demucs Kur

PowerShell ac ve sunu calistir:

```powershell
py -m pip install -U demucs soundfile
```

Kontrol:

```powershell
demucs --help
```

Eger `demucs` komutu bulunamazsa:

```powershell
py -m demucs --help
```

## 3. FFmpeg Kur

Winget varsa:

```powershell
winget install Gyan.FFmpeg
```

Sonra PowerShell'i kapatip yeniden ac ve kontrol et:

```powershell
ffmpeg -version
```

## 4. Programda Kontrol

DJ AI OS icinde `Remix Atolyesi` ekranini ac.

Ekranda sunlari gormelisin:

- Python komutu: hazir
- Vokal ayirma araci: Demucs hazir
- Ses donusturme araci: FFmpeg hazir

Bu ucu hazir oldugunda `VOKALI AYIR` butonu gercek stem/vokal ayirma islemini baslatabilir.
