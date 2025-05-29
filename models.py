from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Yeni: Kayıtlı Müşteri Modeli
class RegisteredCustomer(db.Model):
    __tablename__ = 'registered_customer'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # İlişkiler
    addresses = db.relationship('CustomerAddress', backref='customer', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='customer', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

# Yeni: Müşteri Adresleri
class CustomerAddress(db.Model):
    __tablename__ = 'customer_address'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('registered_customer.id'), nullable=False)
    title = db.Column(db.String(50), nullable=False)  # Ev, İş, vb.
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    neighborhood = db.Column(db.String(100))
    address_line = db.Column(db.Text, nullable=False)
    postal_code = db.Column(db.String(10))
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Yeni: Siparişler
class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('registered_customer.id'), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('customer_address.id'), nullable=False)
    
    # Sipariş bilgileri
    status = db.Column(db.String(20), default='Bekliyor')  # Bekliyor, Onaylandı, Hazırlanıyor, Kargoda, Teslim Edildi, İptal
    total_amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    
    # Tarihler
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    # İlişkiler
    address = db.relationship('CustomerAddress', backref='orders')
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

# Yeni: Sipariş Kalemleri
class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)  # Ürün ID'si (products listesinden)
    product_name = db.Column(db.String(200), nullable=False)
    product_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Float, nullable=False)

# Yeni: Üye Olmayan Müşteri Siparişleri
class GuestOrder(db.Model):
    __tablename__ = 'guest_order'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    
    # Müşteri bilgileri
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    
    # Adres bilgileri
    city = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    neighborhood = db.Column(db.String(100))
    address_line = db.Column(db.Text, nullable=False)
    postal_code = db.Column(db.String(10))
    
    # Sipariş bilgileri
    status = db.Column(db.String(20), default='Bekliyor')  # Bekliyor, Onaylandı, Hazırlanıyor, Kargoda, Teslim Edildi, İptal
    total_amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    
    # Tarihler
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    # İlişkiler
    items = db.relationship('GuestOrderItem', backref='guest_order', lazy=True, cascade='all, delete-orphan')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

# Yeni: Üye Olmayan Müşteri Sipariş Kalemleri
class GuestOrderItem(db.Model):
    __tablename__ = 'guest_order_item'
    id = db.Column(db.Integer, primary_key=True)
    guest_order_id = db.Column(db.Integer, db.ForeignKey('guest_order.id'), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)  # Ürün ID'si (products listesinden)
    product_name = db.Column(db.String(200), nullable=False)
    product_price = db.Column(db.Float, nullable=False)
    product_type = db.Column(db.String(20), nullable=False)  # 'product' veya 'spare_part'
    quantity = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Float, nullable=False)

# Yeni: Ürünler Tablosu
class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(500), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'image': self.image
        }

# Yeni: Yedek Parçalar Tablosu
class SparePart(db.Model):
    __tablename__ = 'spare_part'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(500), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'image': self.image
        }

class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200))
    email = db.Column(db.String(120))
    model = db.Column(db.String(100))
    filter_type = db.Column(db.String(100))
    last_change = db.Column(db.DateTime)
    next_change = db.Column(db.DateTime)
    remaining_days = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)

class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    date = db.Column(db.DateTime, nullable=False)
    service_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='Bekliyor')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VisitorCount(db.Model):
    __tablename__ = 'visitor_count'
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=0)
    date = db.Column(db.Date, default=datetime.now().date)
    page = db.Column(db.String(100), default='/')
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<VisitorCount {self.date}: {self.count}>'

class Banner(db.Model):
    __tablename__ = 'banner'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(300), nullable=True)
    description = db.Column(db.Text, nullable=True)
    button_text = db.Column(db.String(100), nullable=True)
    button_link = db.Column(db.String(200), nullable=True)
    banner_type = db.Column(db.String(50), nullable=False)  # 'campaign', 'delivery', 'info'
    background_color = db.Column(db.String(50), default='#007bff')
    text_color = db.Column(db.String(50), default='#ffffff')
    left_image = db.Column(db.String(200), nullable=True)  # Sol çerçeve resmi
    right_image = db.Column(db.String(200), nullable=True)  # Sağ çerçeve resmi
    is_active = db.Column(db.Boolean, default=True)
    order_priority = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Banner {self.title}>'
