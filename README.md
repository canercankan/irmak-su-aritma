# Irmak Su Arıtma - E-Ticaret Sitesi

Flask tabanlı su arıtma cihazları ve yedek parçaları satış sitesi.

## Özellikler

- 🛒 E-ticaret sistemi
- 👥 Müşteri kayıt/giriş sistemi
- 📅 Randevu sistemi
- 🛡️ Admin paneli
- 📧 E-posta bildirimleri
- 🖼️ Resim yükleme
- 📊 Ziyaretçi istatistikleri
- 🎨 Banner yönetimi

## Kurulum

### Gereksinimler
- Python 3.9+
- Flask
- SQLite

### Yerel Kurulum

1. Projeyi klonlayın:
```bash
git clone <repo-url>
cd cenap
```

2. Sanal ortam oluşturun:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows
```

3. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

4. Uygulamayı çalıştırın:
```bash
python app.py
```

5. Tarayıcıda `http://localhost:9292` adresine gidin.

## Admin Girişi

- **Kullanıcı Adı:** cenap
- **Şifre:** cenap123
- **URL:** `/admin/login`

## Environment Variables

Aşağıdaki environment variables'ları ayarabilirsiniz:

```bash
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
RECEIVER_EMAIL=receiver@gmail.com
SECRET_KEY=your-secret-key
```

## Deployment

### Deta Space

1. `Spacefile` dosyası zaten hazır
2. Deta Space'e upload edin
3. Environment variables'ları ayarlayın

### Diğer Platformlar

- Heroku
- Railway
- PythonAnywhere
- Vercel

## Proje Yapısı

```
cenap/
├── app.py              # Ana Flask uygulaması
├── models.py           # Veritabanı modelleri
├── requirements.txt    # Python bağımlılıkları
├── Spacefile          # Deta Space konfigürasyonu
├── templates/         # HTML şablonları
├── static/           # CSS, JS, resimler
├── migrations/       # Veritabanı migrasyonları
└── README.md         # Bu dosya
```

## Lisans

Bu proje özel kullanım içindir. 

# Railway Deployment Test
