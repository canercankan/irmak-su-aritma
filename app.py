# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template, url_for, redirect, flash, session, send_from_directory
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, User, Customer, Appointment, VisitorCount, RegisteredCustomer, CustomerAddress, Order, OrderItem, GuestOrder, GuestOrderItem, Product, SparePart, Banner
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename

app = Flask(__name__)
load_dotenv()

# Dosya yükleme konfigürasyonu
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max dosya boyutu

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# E-posta ayarları - environment variables'dan al
EMAIL_USER = os.getenv("EMAIL_USER", "cenapoktay@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "uzvh emfn kgcf lcji")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "cenapoktay@gmail.com")

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# CORS yapılandırması
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "allow_headers": ["Content-Type"],
        "methods": ["GET", "POST", "OPTIONS"]
    }
})

# Rate limiter yapılandırması
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Veritabanı konfigürasyonu
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appointments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db, directory='migrations')


# Admin kimlik bilgileri
ADMIN_USERNAME = "cenap"
ADMIN_PASSWORD = "cenap123"

# Ürün verilerini veritabanından al
def get_products():
    return [product.to_dict() for product in Product.query.filter_by(is_active=True).all()]

def get_spare_parts():
    return [part.to_dict() for part in SparePart.query.filter_by(is_active=True).all()]

def send_email(subject, message):
    try:
        # E-posta ayarlarını kontrol et
        sender_email = EMAIL_USER
        sender_password = EMAIL_PASSWORD
        receiver_email = RECEIVER_EMAIL

        if not all([sender_email, sender_password, receiver_email]):
            print("E-posta ayarları eksik!")
            return False

        # E-posta mesajını oluştur
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject

        # Mesaj içeriğini ekle
        msg.attach(MIMEText(message, 'plain'))

        # SMTP sunucusuna bağlan ve e-postayı gönder
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        print("E-posta başarıyla gönderildi!")
        return True
    except Exception as e:
        print(f"E-posta gönderme hatası: {str(e)}")
        return False

@app.route("/")
def index():
    # Ziyaretçi sayısını artır
    today = datetime.now().date()
    visitor = VisitorCount.query.filter_by(date=today).first()
    if visitor:
        visitor.count += 1
    else:
        visitor = VisitorCount(date=today, count=1)
        db.session.add(visitor)
    db.session.commit()
    
    # Aktif banner'ları getir
    banners = Banner.query.filter_by(is_active=True).order_by(Banner.order_priority.asc()).all()
    
    return render_template('index.html', products=get_products(), banners=banners)

@app.route("/appointment")
def appointment_form():
    return render_template('appointment.html')

@app.route("/send_message", methods=["POST"])
def send_message():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Veri bulunamadı"}), 400

        # Zorunlu alanları kontrol et
        required_fields = ['name', 'email', 'message', 'subject']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} alanı zorunludur"}), 400

        # E-posta mesajını oluştur
        email_message = f"""
        Yeni İletişim Formu Mesajı:

        Gönderen: {data['name']}
        E-posta: {data['email']}
        Telefon: {data.get('phone', 'Belirtilmemiş')}
        Konu: {data['subject']}

        Mesaj:
        {data['message']}
        """

        # E-posta gönder
        success = send_email(
            subject=f"Yeni İletişim Formu Mesajı - {data['subject']}",
            message=email_message
        )

        if success:
            return jsonify({"message": "Mesajınız başarıyla gönderildi"})
        else:
            return jsonify({"error": "Mesaj gönderilemedi"}), 500

    except Exception as e:
        print(f"Hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/products')
def products_page():
    return render_template('products.html', products=get_products())

@app.route('/spare-parts')
def spare_parts_page():
    return render_template('spare_parts.html', spare_parts=get_spare_parts())

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = next((p for p in get_products() if p['id'] == product_id), None)
    if product is None:
        return "Ürün bulunamadı", 404
    return render_template('product_detail.html', product=product)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/spare-part/<int:part_id>')
def spare_part_detail(part_id):
    part = next((p for p in get_spare_parts() if p['id'] == part_id), None)
    if part is None:
        return "Yedek parça bulunamadı", 404
    return render_template('spare_part_detail.html', part=part)

@app.route('/appointment/create', methods=['POST'])
def create_appointment():
    try:
        data = request.get_json()

        # Zorunlu alanları kontrol et
        required_fields = ['name', 'phone', 'service_type', 'date']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} alanı zorunludur'})

        # Tarihi kontrol et
        appointment_date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
        if appointment_date < datetime.now():
            return jsonify({'success': False, 'error': 'Geçmiş bir tarih seçemezsiniz'})

        # Randevu oluştur
        appointment = Appointment(
            name=data['name'],
            phone=data['phone'],
            email=data.get('email'),
            date=appointment_date,
            service_type=data['service_type'],
            message=data.get('message')
        )

        db.session.add(appointment)
        db.session.commit()

        # E-posta bildirimi gönder
        email_message = f"""
        Yeni Randevu Bildirimi:

        Müşteri: {data['name']}
        Telefon: {data['phone']}
        E-posta: {data.get('email', 'Belirtilmemiş')}
        Hizmet: {data['service_type']}
        Tarih: {appointment_date.strftime('%d.%m.%Y %H:%M')}
        Mesaj: {data.get('message', 'Belirtilmemiş')}
        """

        send_email(
            subject="Yeni Randevu Bildirimi",
            message=email_message
        )

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/appointments')
def list_appointments():
    appointments = Appointment.query.order_by(Appointment.date.desc()).all()
    return render_template('appointments.html', appointments=appointments)

@app.route('/appointment/<int:id>/update', methods=['POST'])
def update_appointment(id):
    try:
        appointment = Appointment.query.get_or_404(id)
        data = request.get_json()

        if 'status' in data:
            appointment.status = data['status']

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Yönetici girişi için basit bir kimlik doğrulama
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Veritabanından admin kullanıcısını bul
        admin = User.query.filter_by(username=username).first()

        # Kullanıcı adı ve şifre kontrolü
        if admin and check_password_hash(admin.password, password) and admin.is_admin:
            session['admin'] = True
            return redirect(url_for('admin_stats'))  # Chat yerine stats'a yönlendir
        return render_template('admin_login.html', error="Hatalı kullanıcı adı veya şifre")
    return render_template('admin_login.html')

@app.route('/admin/stats')
def admin_stats():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    try:
        # Toplam ziyaretçi sayısı
        total_visitors = db.session.query(db.func.sum(VisitorCount.count)).scalar() or 0
        
        # Bugünkü ziyaretçi sayısı
        today = datetime.now().date()
        today_visitors = VisitorCount.query.filter_by(date=today).first()
        today_count = today_visitors.count if today_visitors else 0
        
        # Son 7 günün istatistikleri
        from datetime import timedelta
        week_ago = today - timedelta(days=7)
        weekly_stats = VisitorCount.query.filter(VisitorCount.date >= week_ago).order_by(VisitorCount.date.desc()).all()
        
        stats = {
            'total_visitors': total_visitors,
            'today_visitors': today_count,
            'weekly_stats': weekly_stats
        }
        
        return render_template('admin_stats.html', stats=stats)
    except Exception as e:
        return f"Hata: {e}"

# Admin Ürün Yönetimi
@app.route('/admin/products')
def admin_products():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    return render_template('admin_products.html', products=get_products(), spare_parts=get_spare_parts())

@app.route('/admin/product/<int:product_id>/edit', methods=['POST'])
def edit_product_price(product_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetki yok'})
    
    try:
        data = request.get_json()
        new_price = float(data.get('price', 0))
        
        # Ürünü bul ve fiyatını güncelle
        product = Product.query.get(product_id)
        if product:
            product.price = new_price
            db.session.commit()
            return jsonify({'success': True, 'message': 'Ürün fiyatı güncellendi'})
        
        return jsonify({'success': False, 'error': 'Ürün bulunamadı'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/spare-part/<int:part_id>/edit', methods=['POST'])
def edit_spare_part_price(part_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetki yok'})
    
    try:
        data = request.get_json()
        new_price = float(data.get('price', 0))
        
        # Yedek parçayı bul ve fiyatını güncelle
        part = SparePart.query.get(part_id)
        if part:
            part.price = new_price
            db.session.commit()
            return jsonify({'success': True, 'message': 'Yedek parça fiyatı güncellendi'})
        
        return jsonify({'success': False, 'error': 'Yedek parça bulunamadı'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# Yeni Ürün Ekleme
@app.route('/admin/product/add', methods=['POST'])
def add_new_product():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetki yok'})
    
    try:
        data = request.get_json()
        
        # Zorunlu alanları kontrol et
        required_fields = ['name', 'description', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} alanı zorunludur'})
        
        # Yeni ürün oluştur
        new_product = Product(
            name=data['name'],
            description=data['description'],
            price=float(data['price']),
            image=data.get('image', '/static/images/default-product.jpg')
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Yeni ürün eklendi', 'product': new_product.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Resim yükleme ile ürün ekleme
@app.route('/admin/product/add-with-image', methods=['POST'])
def add_product_with_image():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetki yok'})
    
    try:
        # Form verilerini al
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        
        # Zorunlu alanları kontrol et
        if not name or not description or not price:
            return jsonify({'success': False, 'error': 'Tüm alanlar zorunludur'})
        
        # Dosya kontrolü
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'Resim dosyası seçilmedi'})
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Resim dosyası seçilmedi'})
        
        if file and allowed_file(file.filename):
            # Güvenli dosya adı oluştur
            filename = secure_filename(file.filename)
            # Benzersiz dosya adı için timestamp ekle
            import time
            timestamp = str(int(time.time()))
            name_part, ext_part = filename.rsplit('.', 1)
            filename = f"{name_part}_{timestamp}.{ext_part}"
            
            # Dosyayı kaydet
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Yeni ürün oluştur
            new_product = Product(
                name=name,
                description=description,
                price=float(price),
                image=f'/static/images/{filename}'
            )
            
            db.session.add(new_product)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Ürün resimle birlikte eklendi', 'product': new_product.to_dict()})
        else:
            return jsonify({'success': False, 'error': 'Geçersiz dosya formatı. PNG, JPG, JPEG, GIF veya WEBP dosyası seçin.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Yedek parça resim yükleme
@app.route('/admin/spare-part/add-with-image', methods=['POST'])
def add_spare_part_with_image():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetki yok'})
    
    try:
        # Form verilerini al
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        
        # Zorunlu alanları kontrol et
        if not name or not description or not price:
            return jsonify({'success': False, 'error': 'Tüm alanlar zorunludur'})
        
        # Dosya kontrolü
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'Resim dosyası seçilmedi'})
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Resim dosyası seçilmedi'})
        
        if file and allowed_file(file.filename):
            # Güvenli dosya adı oluştur
            filename = secure_filename(file.filename)
            # Benzersiz dosya adı için timestamp ekle
            import time
            timestamp = str(int(time.time()))
            name_part, ext_part = filename.rsplit('.', 1)
            filename = f"{name_part}_{timestamp}.{ext_part}"
            
            # Dosyayı kaydet
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Yeni yedek parça oluştur
            new_part = SparePart(
                name=name,
                description=description,
                price=float(price),
                image=f'/static/images/{filename}'
            )
            
            db.session.add(new_part)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Yedek parça resimle birlikte eklendi', 'part': new_part.to_dict()})
        else:
            return jsonify({'success': False, 'error': 'Geçersiz dosya formatı. PNG, JPG, JPEG, GIF veya WEBP dosyası seçin.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Ürün Silme
@app.route('/admin/product/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetki yok'})
    
    try:
        # Silinecek ürünü bul
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'error': 'Ürün bulunamadı'})
        
        # Ürünün resmini sil (eğer varsayılan resim değilse)
        if product.image and not product.image.startswith('/static/images/default'):
            try:
                image_path = product.image.replace('/static/', 'static/')
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"Resim silindi: {image_path}")
            except Exception as e:
                print(f"Resim silme hatası: {e}")
        
        # Ürünü veritabanından sil
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Ürün ve resmi silindi'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/spare-part/<int:part_id>/delete', methods=['POST'])
def delete_spare_part(part_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetki yok'})
    
    try:
        # Silinecek yedek parçayı bul
        part = SparePart.query.get(part_id)
        if not part:
            return jsonify({'success': False, 'error': 'Yedek parça bulunamadı'})
        
        # Yedek parçanın resmini sil (eğer varsayılan resim değilse)
        if part.image and not part.image.startswith('/static/images/default'):
            try:
                image_path = part.image.replace('/static/', 'static/')
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"Resim silindi: {image_path}")
            except Exception as e:
                print(f"Resim silme hatası: {e}")
        
        # Yedek parçayı veritabanından sil
        db.session.delete(part)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Yedek parça ve resmi silindi'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Müşteri Kayıt ve Giriş Sistemi
@app.route('/register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            # Zorunlu alanları kontrol et
            required_fields = ['first_name', 'last_name', 'email', 'phone', 'password']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'success': False, 'error': f'{field} alanı zorunludur'})
            
            # E-posta kontrolü
            existing_customer = RegisteredCustomer.query.filter_by(email=data['email']).first()
            if existing_customer:
                return jsonify({'success': False, 'error': 'Bu e-posta adresi zaten kayıtlı'})
            
            # Yeni müşteri oluştur
            customer = RegisteredCustomer(
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                phone=data['phone']
            )
            customer.set_password(data['password'])
            
            db.session.add(customer)
            db.session.commit()
            
            # Hoş geldin e-postası gönder
            welcome_message = f"""
            Merhaba {customer.full_name},
            
            Irmak Su Arıtma'ya hoş geldiniz! Hesabınız başarıyla oluşturuldu.
            
            Artık online sipariş verebilir, randevu alabilir ve hesabınızı yönetebilirsiniz.
            
            İyi günler dileriz.
            """
            
            send_email(
                subject="Irmak Su Arıtma - Hoş Geldiniz!",
                message=welcome_message
            )
            
            return jsonify({'success': True, 'message': 'Kayıt başarılı! Giriş yapabilirsiniz.'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    
    return render_template('customer_register.html')

@app.route('/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return jsonify({'success': False, 'error': 'E-posta ve şifre gerekli'})
            
            # Müşteriyi bul
            customer = RegisteredCustomer.query.filter_by(email=email).first()
            
            if customer and customer.check_password(password):
                # Giriş başarılı
                session['customer_id'] = customer.id
                session['customer_name'] = customer.full_name
                customer.last_login = datetime.utcnow()
                db.session.commit()
                
                return jsonify({'success': True, 'message': 'Giriş başarılı'})
            else:
                return jsonify({'success': False, 'error': 'Hatalı e-posta veya şifre'})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return render_template('customer_login.html')

@app.route('/logout')
def customer_logout():
    session.pop('customer_id', None)
    session.pop('customer_name', None)
    flash('Başarıyla çıkış yaptınız', 'success')
    return redirect(url_for('home'))

@app.route('/profile')
def customer_profile():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer = RegisteredCustomer.query.get(session['customer_id'])
    if not customer:
        return redirect(url_for('customer_login'))
    
    return render_template('customer_profile.html', customer=customer)

@app.route('/profile/edit', methods=['POST'])
def edit_customer_profile():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        customer = RegisteredCustomer.query.get(session['customer_id'])
        data = request.get_json()
        
        customer.first_name = data.get('first_name', customer.first_name)
        customer.last_name = data.get('last_name', customer.last_name)
        customer.phone = data.get('phone', customer.phone)
        
        db.session.commit()
        session['customer_name'] = customer.full_name
        
        return jsonify({'success': True, 'message': 'Profil güncellendi'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/profile/change-password', methods=['POST'])
def change_customer_password():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        customer = RegisteredCustomer.query.get(session['customer_id'])
        data = request.get_json()
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not customer.check_password(current_password):
            return jsonify({'success': False, 'error': 'Mevcut şifre yanlış'})
        
        customer.set_password(new_password)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Şifre başarıyla değiştirildi'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Adres Yönetimi
@app.route('/addresses')
def customer_addresses():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer = RegisteredCustomer.query.get(session['customer_id'])
    return render_template('customer_addresses.html', customer=customer)

@app.route('/address/add', methods=['POST'])
def add_customer_address():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        data = request.get_json()
        
        # Zorunlu alanları kontrol et
        required_fields = ['title', 'first_name', 'last_name', 'phone', 'city', 'district', 'address_line']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} alanı zorunludur'})
        
        # Eğer bu varsayılan adres ise, diğerlerini varsayılan olmaktan çıkar
        if data.get('is_default'):
            CustomerAddress.query.filter_by(customer_id=session['customer_id']).update({'is_default': False})
        
        address = CustomerAddress(
            customer_id=session['customer_id'],
            title=data['title'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data['phone'],
            city=data['city'],
            district=data['district'],
            neighborhood=data.get('neighborhood', ''),
            address_line=data['address_line'],
            postal_code=data.get('postal_code', ''),
            is_default=data.get('is_default', False)
        )
        
        db.session.add(address)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Adres eklendi'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/address/<int:address_id>/set-default', methods=['POST'])
def set_default_address(address_id):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        # Önce tüm adresleri varsayılan olmaktan çıkar
        CustomerAddress.query.filter_by(customer_id=session['customer_id']).update({'is_default': False})
        
        # Seçilen adresi varsayılan yap
        address = CustomerAddress.query.filter_by(id=address_id, customer_id=session['customer_id']).first()
        if address:
            address.is_default = True
            db.session.commit()
            return jsonify({'success': True, 'message': 'Varsayılan adres güncellendi'})
        else:
            return jsonify({'success': False, 'error': 'Adres bulunamadı'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/address/<int:address_id>/delete', methods=['POST'])
def delete_address(address_id):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        address = CustomerAddress.query.filter_by(id=address_id, customer_id=session['customer_id']).first()
        if not address:
            return jsonify({'success': False, 'error': 'Adres bulunamadı'})
        
        # Varsayılan adres silinmesin
        if address.is_default:
            # Başka adres var mı kontrol et
            other_addresses = CustomerAddress.query.filter(
                CustomerAddress.customer_id == session['customer_id'],
                CustomerAddress.id != address_id
            ).all()
            
            if other_addresses:
                # Başka bir adresi varsayılan yap
                other_addresses[0].is_default = True
            else:
                return jsonify({'success': False, 'error': 'Son adresinizi silemezsiniz. En az bir adres bulunmalıdır.'})
        
        db.session.delete(address)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Adres başarıyla silindi'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Adres silme hatası: {str(e)}")  # Debug için
        return jsonify({'success': False, 'error': f'Adres silinirken hata oluştu: {str(e)}'})

@app.route('/address/<int:address_id>/get', methods=['GET'])
def get_address(address_id):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        address = CustomerAddress.query.filter_by(id=address_id, customer_id=session['customer_id']).first()
        if address:
            return jsonify({
                'success': True,
                'address': {
                    'id': address.id,
                    'title': address.title,
                    'first_name': address.first_name,
                    'last_name': address.last_name,
                    'phone': address.phone,
                    'city': address.city,
                    'district': address.district,
                    'neighborhood': address.neighborhood,
                    'address_line': address.address_line,
                    'postal_code': address.postal_code,
                    'is_default': address.is_default
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Adres bulunamadı'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/address/<int:address_id>/edit', methods=['POST'])
def edit_address(address_id):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        address = CustomerAddress.query.filter_by(id=address_id, customer_id=session['customer_id']).first()
        if not address:
            return jsonify({'success': False, 'error': 'Adres bulunamadı'})
        
        data = request.get_json()
        
        # Zorunlu alanları kontrol et
        required_fields = ['title', 'first_name', 'last_name', 'phone', 'city', 'district', 'address_line']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} alanı zorunludur'})
        
        # Eğer bu varsayılan adres ise, diğerlerini varsayılan olmaktan çıkar
        if data.get('is_default'):
            CustomerAddress.query.filter_by(customer_id=session['customer_id']).update({'is_default': False})
        
        # Adres bilgilerini güncelle
        address.title = data['title']
        address.first_name = data['first_name']
        address.last_name = data['last_name']
        address.phone = data['phone']
        address.city = data['city']
        address.district = data['district']
        address.neighborhood = data.get('neighborhood', '')
        address.address_line = data['address_line']
        address.postal_code = data.get('postal_code', '')
        address.is_default = data.get('is_default', False)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Adres güncellendi'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Sipariş Sistemi
@app.route('/cart')
def shopping_cart():
    return render_template('shopping_cart.html', products=get_products(), spare_parts=get_spare_parts())

@app.route('/checkout')
def checkout():
    if not session.get('customer_id'):
        return redirect(url_for('customer_login'))
    
    customer = RegisteredCustomer.query.get(session['customer_id'])
    addresses = CustomerAddress.query.filter_by(customer_id=customer.id).all()
    return render_template('checkout.html', customer=customer, addresses=addresses)

# Yeni: Üye olmadan sipariş sayfası
@app.route('/guest-checkout')
def guest_checkout():
    return render_template('guest_checkout.html')

@app.route('/order/create', methods=['POST'])
def create_order():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        data = request.get_json()
        
        # Sipariş numarası oluştur
        import random
        import string
        order_number = 'G' + ''.join(random.choices(string.digits, k=8))
        
        # Sipariş oluştur
        order = Order(
            order_number=order_number,
            customer_id=session['customer_id'],
            address_id=data['address_id'],
            total_amount=data['total_amount'],
            notes=data.get('notes', '')
        )
        
        db.session.add(order)
        db.session.flush()  # ID'yi al
        
        # Sipariş kalemlerini ekle
        for item in data['items']:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item['product_id'],
                product_name=item['product_name'],
                product_price=item['product_price'],
                quantity=item['quantity'],
                total_price=item['total_price']
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        # Sipariş bildirimi e-postası gönder
        customer = RegisteredCustomer.query.get(session['customer_id'])
        order_message = f"""
        Yeni Sipariş Bildirimi:
        
        Sipariş No: {order_number}
        Müşteri: {customer.full_name}
        E-posta: {customer.email}
        Telefon: {customer.phone}
        Toplam Tutar: {data['total_amount']} TL
        
        Sipariş Detayları:
        """
        
        for item in data['items']:
            order_message += f"\n- {item['product_name']} x{item['quantity']} = {item['total_price']} TL"
        
        send_email(
            subject=f"Yeni Sipariş - {order_number}",
            message=order_message
        )
        
        return jsonify({'success': True, 'order_number': order_number})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/orders')
def customer_orders():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    orders = Order.query.filter_by(customer_id=session['customer_id']).order_by(Order.created_at.desc()).all()
    return render_template('customer_orders.html', orders=orders)

@app.route('/order/<order_number>/cancel', methods=['POST'])
def cancel_order(order_number):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        order = Order.query.filter_by(
            order_number=order_number, 
            customer_id=session['customer_id']
        ).first()
        
        if not order:
            return jsonify({'success': False, 'error': 'Sipariş bulunamadı'})
        
        if order.status not in ['Bekliyor', 'Onaylandı']:
            return jsonify({'success': False, 'error': 'Bu sipariş iptal edilemez'})
        
        order.status = 'İptal'
        db.session.commit()
        
        # İptal bildirimi e-postası gönder
        customer = RegisteredCustomer.query.get(session['customer_id'])
        cancel_message = f"""
        Sipariş İptal Bildirimi:
        
        Sipariş No: {order_number}
        Müşteri: {customer.full_name}
        E-posta: {customer.email}
        Telefon: {customer.phone}
        İptal Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}
        """
        
        send_email(
            subject=f"Sipariş İptal - {order_number}",
            message=cancel_message
        )
        
        return jsonify({'success': True, 'message': 'Sipariş iptal edildi'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/order/<order_number>/reorder', methods=['POST'])
def reorder(order_number):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        order = Order.query.filter_by(
            order_number=order_number, 
            customer_id=session['customer_id']
        ).first()
        
        if not order:
            return jsonify({'success': False, 'error': 'Sipariş bulunamadı'})
        
        # Sipariş kalemlerini sepete ekle (frontend'de localStorage'a eklenmesi gerekiyor)
        # Bu route sadece onay veriyor, gerçek sepet işlemi JavaScript'te yapılacak
        
        return jsonify({
            'success': True, 
            'message': 'Ürünler sepete eklendi',
            'items': [
                {
                    'id': item.product_id,
                    'name': item.product_name,
                    'price': item.product_price,
                    'quantity': item.quantity,
                    'type': 'product'
                } for item in order.items
            ]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/order/<order_number>/delete', methods=['POST'])
def delete_order(order_number):
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        order = Order.query.filter_by(
            order_number=order_number, 
            customer_id=session['customer_id']
        ).first()
        
        if not order:
            return jsonify({'success': False, 'error': 'Sipariş bulunamadı'})
        
        # Sadece iptal edilmiş siparişler silinebilir
        if order.status != 'İptal':
            return jsonify({'success': False, 'error': 'Sadece iptal edilmiş siparişler silinebilir'})
        
        # Sipariş kalemlerini sil (cascade ile otomatik silinir)
        db.session.delete(order)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Sipariş başarıyla silindi'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/orders/delete-cancelled', methods=['POST'])
def delete_all_cancelled_orders():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    try:
        # İptal edilmiş siparişleri bul
        cancelled_orders = Order.query.filter_by(
            customer_id=session['customer_id'],
            status='İptal'
        ).all()
        
        if not cancelled_orders:
            return jsonify({'success': False, 'error': 'Silinecek iptal edilmiş sipariş bulunamadı'})
        
        deleted_count = len(cancelled_orders)
        
        # Tüm iptal edilmiş siparişleri sil
        for order in cancelled_orders:
            db.session.delete(order)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'{deleted_count} adet iptal edilmiş sipariş silindi'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/spare-part/add', methods=['POST'])
def add_new_spare_part():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetki yok'})
    
    try:
        data = request.get_json()
        
        # Zorunlu alanları kontrol et
        required_fields = ['name', 'description', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} alanı zorunludur'})
        
        # Yeni yedek parça oluştur
        new_part = SparePart(
            name=data['name'],
            description=data['description'],
            price=float(data['price']),
            image=data.get('image', '/static/images/default-part.jpg')
        )
        
        db.session.add(new_part)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Yeni yedek parça eklendi', 'part': new_part.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Kullanılmayan resimleri temizleme
@app.route('/admin/cleanup-images', methods=['POST'])
def cleanup_unused_images():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetki yok'})
    
    try:
        # Kullanılan resimlerin listesini oluştur
        used_images = set()
        
        # Ürün resimlerini ekle
        for product in get_products():
            if product['image'] and not product['image'].startswith('/static/images/default'):
                image_path = product['image'].replace('/static/', '')
                used_images.add(image_path)
        
        # Yedek parça resimlerini ekle
        for part in get_spare_parts():
            if part['image'] and not part['image'].startswith('/static/images/default'):
                image_path = part['image'].replace('/static/', '')
                used_images.add(image_path)
        
        # Varsayılan resimleri koruma listesi
        protected_images = {
            'images/premium.jpg',
            'images/economy-system.jpg', 
            'images/industrial-system.jpg',
            'images/filters.jpg',
            'images/membranes.jpg',
            'images/pumps.jpg',
            'images/tank.jpg',
            'images/valfler.jpg',
            'images/musluk.jpg',
            'images/filtre-kabi.jpg',
            'images/watergold-su-aritma-cihazi-motor-pompa-adaptoerue-24-volt.jpg'
        }
        
        # Images klasöründeki tüm dosyaları kontrol et
        images_dir = 'static/images'
        deleted_files = []
        
        if os.path.exists(images_dir):
            for filename in os.listdir(images_dir):
                file_path = os.path.join(images_dir, filename)
                relative_path = f'images/{filename}'
                
                # Dosya ise ve kullanılmıyorsa ve korumalı değilse sil
                if (os.path.isfile(file_path) and 
                    relative_path not in used_images and 
                    relative_path not in protected_images and
                    filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))):
                    
                    try:
                        os.remove(file_path)
                        deleted_files.append(filename)
                        print(f"Kullanılmayan resim silindi: {filename}")
                    except Exception as e:
                        print(f"Dosya silme hatası {filename}: {e}")
        
        if deleted_files:
            return jsonify({
                'success': True, 
                'message': f'{len(deleted_files)} adet kullanılmayan resim silindi',
                'deleted_files': deleted_files
            })
        else:
            return jsonify({
                'success': True, 
                'message': 'Silinecek kullanılmayan resim bulunamadı'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Resim listesi görüntüleme
@app.route('/admin/images')
def admin_images():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    try:
        # Kullanılan resimlerin listesini oluştur
        used_images = set()
        
        # Ürün resimlerini ekle
        for product in get_products():
            if product['image']:
                used_images.add(product['image'])
        
        # Yedek parça resimlerini ekle
        for part in get_spare_parts():
            if part['image']:
                used_images.add(part['image'])
        
        # Images klasöründeki tüm dosyaları listele
        images_dir = 'static/images'
        all_images = []
        
        if os.path.exists(images_dir):
            for filename in os.listdir(images_dir):
                file_path = os.path.join(images_dir, filename)
                if (os.path.isfile(file_path) and 
                    filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))):
                    
                    image_url = f'/static/images/{filename}'
                    file_size = os.path.getsize(file_path)
                    file_size_mb = round(file_size / (1024 * 1024), 2)
                    
                    all_images.append({
                        'filename': filename,
                        'url': image_url,
                        'size_mb': file_size_mb,
                        'is_used': image_url in used_images
                    })
        
        # Dosya boyutuna göre sırala (büyükten küçüğe)
        all_images.sort(key=lambda x: x['size_mb'], reverse=True)
        
        return render_template('admin_images.html', images=all_images)
        
    except Exception as e:
        return f"Hata: {e}"

# Tek resim silme
@app.route('/admin/image/delete', methods=['POST'])
def delete_single_image():
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Yetki yok'})
    
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'success': False, 'error': 'Dosya adı belirtilmedi'})
        
        # Güvenlik kontrolü - sadece images klasöründeki dosyalar
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'success': False, 'error': 'Geçersiz dosya adı'})
        
        file_path = os.path.join('static/images', filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'Dosya bulunamadı'})
        
        # Kullanılıp kullanılmadığını kontrol et
        image_url = f'/static/images/{filename}'
        is_used = False
        
        # Ürünlerde kullanılıyor mu?
        for product in get_products():
            if product['image'] == image_url:
                is_used = True
                break
        
        # Yedek parçalarda kullanılıyor mu?
        if not is_used:
            for part in get_spare_parts():
                if part['image'] == image_url:
                    is_used = True
                    break
        
        if is_used:
            return jsonify({'success': False, 'error': 'Bu resim hala kullanılıyor, silinemez'})
        
        # Dosyayı sil
        os.remove(file_path)
        
        return jsonify({'success': True, 'message': f'{filename} başarıyla silindi'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Yeni: Üye olmadan sipariş oluşturma
@app.route('/guest-order/create', methods=['POST'])
def create_guest_order():
    try:
        data = request.get_json()
        
        # Form verilerini al
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        city = data.get('city', '').strip()
        district = data.get('district', '').strip()
        neighborhood = data.get('neighborhood', '').strip()
        address_line = data.get('address_line', '').strip()
        postal_code = data.get('postal_code', '').strip()
        notes = data.get('notes', '').strip()
        cart_items = data.get('cart_items', [])
        
        # Zorunlu alanları kontrol et
        if not all([first_name, last_name, phone, city, district, address_line]):
            return jsonify({'success': False, 'error': 'Lütfen tüm zorunlu alanları doldurun!'})
        
        if not cart_items:
            return jsonify({'success': False, 'error': 'Sepetiniz boş!'})
        
        # Sipariş numarası oluştur
        import random
        import string
        order_number = 'G' + ''.join(random.choices(string.digits, k=8))
        
        # Toplam tutarı hesapla
        total_amount = 0
        for item in cart_items:
            total_amount += float(item['price']) * int(item['quantity'])
        
        # Yeni sipariş oluştur
        guest_order = GuestOrder(
            order_number=order_number,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            city=city,
            district=district,
            neighborhood=neighborhood,
            address_line=address_line,
            postal_code=postal_code,
            total_amount=total_amount,
            notes=notes
        )
        
        db.session.add(guest_order)
        db.session.flush()  # ID'yi al
        
        # Sipariş kalemlerini ekle
        for item in cart_items:
            order_item = GuestOrderItem(
                guest_order_id=guest_order.id,
                product_id=item['id'],
                product_name=item['name'],
                product_price=float(item['price']),
                product_type=item['type'],
                quantity=int(item['quantity']),
                total_price=float(item['price']) * int(item['quantity'])
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        # E-posta gönder
        try:
            subject = f"Yeni Sipariş - {order_number}"
            message = f"""
Yeni bir sipariş alındı!

Sipariş Numarası: {order_number}
Müşteri: {first_name} {last_name}
Telefon: {phone}
E-posta: {email}

Adres:
{city} / {district}
{neighborhood}
{address_line}
{postal_code}

Sipariş Detayları:
"""
            for item in cart_items:
                message += f"- {item['name']} x{item['quantity']} = {float(item['price']) * int(item['quantity'])} TL\n"
            
            message += f"\nToplam: {total_amount} TL"
            
            if notes:
                message += f"\nNotlar: {notes}"
            
            send_email(subject, message)
        except Exception as e:
            print(f"E-posta gönderme hatası: {str(e)}")
        
        return jsonify({
            'success': True, 
            'message': 'Siparişiniz başarıyla alındı!',
            'order_number': order_number
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Sipariş oluşturma hatası: {str(e)}")
        return jsonify({'success': False, 'error': 'Sipariş oluşturulurken bir hata oluştu!'})

# Banner Yönetimi Routes
@app.route('/admin/banners')
def admin_banners():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    banners = Banner.query.order_by(Banner.order_priority.asc(), Banner.created_at.desc()).all()
    return render_template('admin_banners.html', banners=banners)

@app.route('/admin/banner/add', methods=['POST'])
def add_banner():
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'})
    
    try:
        print("Banner ekleme isteği alındı")
        print(f"Form verileri: {request.form}")
        print(f"Dosyalar: {request.files}")
        
        # Resim dosyalarını işle
        left_image_filename = None
        right_image_filename = None
        
        if 'left_image' in request.files:
            left_image = request.files['left_image']
            print(f"Sol resim: {left_image.filename}, boyut: {len(left_image.read()) if left_image else 0}")
            left_image.seek(0)  # Dosya pointer'ını başa al
            if left_image and left_image.filename != '' and allowed_file(left_image.filename):
                left_image_filename = secure_filename(left_image.filename)
                # Benzersiz dosya adı oluştur
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                left_image_filename = f"left_{timestamp}_{left_image_filename}"
                left_image.save(os.path.join(app.config['UPLOAD_FOLDER'], left_image_filename))
                print(f"Sol resim kaydedildi: {left_image_filename}")
            else:
                print("Sol resim geçersiz veya boş")
        
        if 'right_image' in request.files:
            right_image = request.files['right_image']
            print(f"Sağ resim: {right_image.filename}, boyut: {len(right_image.read()) if right_image else 0}")
            right_image.seek(0)  # Dosya pointer'ını başa al
            if right_image and right_image.filename != '' and allowed_file(right_image.filename):
                right_image_filename = secure_filename(right_image.filename)
                # Benzersiz dosya adı oluştur
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                right_image_filename = f"right_{timestamp}_{right_image_filename}"
                right_image.save(os.path.join(app.config['UPLOAD_FOLDER'], right_image_filename))
                print(f"Sağ resim kaydedildi: {right_image_filename}")
            else:
                print("Sağ resim geçersiz veya boş")
        
        banner = Banner(
            title=request.form.get('title'),
            subtitle=request.form.get('subtitle'),
            description=request.form.get('description'),
            button_text=request.form.get('button_text'),
            button_link=request.form.get('button_link'),
            banner_type=request.form.get('banner_type'),
            background_color=request.form.get('background_color', '#007bff'),
            text_color=request.form.get('text_color', '#ffffff'),
            left_image=left_image_filename,
            right_image=right_image_filename,
            order_priority=int(request.form.get('order_priority', 1)),
            is_active=bool(request.form.get('is_active'))
        )
        
        db.session.add(banner)
        db.session.commit()
        
        print(f"Banner başarıyla eklendi: {banner.id}")
        return jsonify({'success': True, 'message': 'Banner başarıyla eklendi'})
    except Exception as e:
        print(f"Banner ekleme hatası: {str(e)}")
        return jsonify({'success': False, 'message': f'Hata: {str(e)}'})

@app.route('/admin/banner/<int:banner_id>/edit', methods=['POST'])
def edit_banner(banner_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'})
    
    try:
        banner = Banner.query.get(banner_id)
        if not banner:
            return jsonify({'success': False, 'message': 'Banner bulunamadı'})
        
        # Resim dosyalarını işle
        if 'left_image' in request.files:
            left_image = request.files['left_image']
            if left_image and left_image.filename != '' and allowed_file(left_image.filename):
                # Eski resmi sil
                if banner.left_image:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], banner.left_image)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                # Yeni resmi kaydet
                left_image_filename = secure_filename(left_image.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                left_image_filename = f"left_{timestamp}_{left_image_filename}"
                left_image.save(os.path.join(app.config['UPLOAD_FOLDER'], left_image_filename))
                banner.left_image = left_image_filename
        
        if 'right_image' in request.files:
            right_image = request.files['right_image']
            if right_image and right_image.filename != '' and allowed_file(right_image.filename):
                # Eski resmi sil
                if banner.right_image:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], banner.right_image)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                # Yeni resmi kaydet
                right_image_filename = secure_filename(right_image.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                right_image_filename = f"right_{timestamp}_{right_image_filename}"
                right_image.save(os.path.join(app.config['UPLOAD_FOLDER'], right_image_filename))
                banner.right_image = right_image_filename
        
        banner.title = request.form.get('title')
        banner.subtitle = request.form.get('subtitle')
        banner.description = request.form.get('description')
        banner.button_text = request.form.get('button_text')
        banner.button_link = request.form.get('button_link')
        banner.banner_type = request.form.get('banner_type')
        banner.background_color = request.form.get('background_color', '#007bff')
        banner.text_color = request.form.get('text_color', '#ffffff')
        banner.order_priority = int(request.form.get('order_priority', 1))
        banner.is_active = bool(request.form.get('is_active'))
        banner.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Banner başarıyla güncellendi'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Hata: {str(e)}'})

@app.route('/admin/banner/<int:banner_id>/toggle', methods=['POST'])
def toggle_banner(banner_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'})
    
    try:
        banner = Banner.query.get(banner_id)
        if not banner:
            return jsonify({'success': False, 'message': 'Banner bulunamadı'})
        
        banner.is_active = not banner.is_active
        banner.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = "aktif" if banner.is_active else "pasif"
        return jsonify({'success': True, 'message': f'Banner {status} duruma getirildi'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Hata: {str(e)}'})

@app.route('/admin/banner/<int:banner_id>/delete', methods=['POST'])
def delete_banner(banner_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'})
    
    try:
        banner = Banner.query.get(banner_id)
        if not banner:
            return jsonify({'success': False, 'message': 'Banner bulunamadı'})
        
        db.session.delete(banner)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Banner başarıyla silindi'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Hata: {str(e)}'})

@app.route('/admin/banner/<int:banner_id>/get', methods=['GET'])
def get_banner(banner_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'})
    
    try:
        banner = Banner.query.get(banner_id)
        if not banner:
            return jsonify({'success': False, 'message': 'Banner bulunamadı'})
        
        banner_data = {
            'id': banner.id,
            'title': banner.title,
            'subtitle': banner.subtitle,
            'description': banner.description,
            'button_text': banner.button_text,
            'button_link': banner.button_link,
            'banner_type': banner.banner_type,
            'background_color': banner.background_color,
            'text_color': banner.text_color,
            'left_image': banner.left_image,
            'right_image': banner.right_image,
            'order_priority': banner.order_priority,
            'is_active': banner.is_active
        }
        
        return jsonify({'success': True, 'banner': banner_data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Hata: {str(e)}'})

if __name__ == "__main__":
    # Veritabanı ve admin kullanıcısını sadece gerektiğinde oluştur
    with app.app_context():
        try:
            # Veritabanı tablolarını oluştur
            db.create_all()
            print("Veritabanı kontrol edildi.")
            
            # Admin kullanıcısını kontrol et ve gerekirse oluştur
            admin_user = User.query.filter_by(username=ADMIN_USERNAME).first()
            if not admin_user:
                admin_user = User(
                    username=ADMIN_USERNAME,
                    password=generate_password_hash(ADMIN_PASSWORD),
                    is_admin=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print("Admin kullanıcısı oluşturuldu.")
            else:
                print("Admin kullanıcısı zaten mevcut.")
                
        except Exception as e:
            print(f"Veritabanı hatası: {e}")
    
    # Railway için port ayarı
    port = int(os.environ.get('PORT', 9292))
    app.run(host='0.0.0.0', port=port, debug=False)
