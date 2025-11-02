from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Student specific fields
    full_name = db.Column(db.String(150))
    id_number = db.Column(db.String(13))
    phone_number = db.Column(db.String(15))
    current_school = db.Column(db.String(200))
    grade = db.Column(db.String(10))
    profile_photo = db.Column(db.String(255))
    
    # Notification preferences
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    
    # Relationships
    applications = db.relationship('Application', backref='student', lazy=True)
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, order_by='Notification.created_at.desc()')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def unread_notifications_count(self):
        return Notification.query.filter_by(user_id=self.id, read=False).count()
    
    def unread_messages_count(self):
        return Message.query.filter_by(receiver_id=self.id, read=False).count()

class School(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    province = db.Column(db.String(100), nullable=False)
    suburb = db.Column(db.String(100))  # ADD THIS LINE - Suburb/Location
    address = db.Column(db.Text)
    contact_number = db.Column(db.String(15))
    email = db.Column(db.String(120))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # ... rest of the fields remain the same
    
    # Performance metrics
    pass_rate = db.Column(db.Float)
    performance_rating = db.Column(db.String(20))
    total_students = db.Column(db.Integer)
    requires_performance = db.Column(db.Boolean, default=False)
    
    # School details
    school_type = db.Column(db.String(50))
    facilities = db.Column(db.Text)
    website = db.Column(db.String(200))
    logo = db.Column(db.String(255))
    
    applications = db.relationship('Application', backref='school', lazy=True)
    
    def __repr__(self):
        return f'<School {self.name}>'

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected', 'under_review'
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    admin_notes = db.Column(db.Text)
    
    # Student documents/info
    motivation_letter = db.Column(db.Text)
    previous_report = db.Column(db.String(255))  # File path
    birth_certificate = db.Column(db.String(255))  # File path
    proof_of_residence = db.Column(db.String(255))  # File path
    id_document = db.Column(db.String(255))  # File path
    additional_documents = db.Column(db.Text)  # JSON array of file paths
    
    # Tracking
    viewed_by_admin = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default='normal')  # 'low', 'normal', 'high', 'urgent'
    
    def __repr__(self):
        return f'<Application {self.id} - Student {self.student_id} to School {self.school_id}>'

class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used = db.Column(db.Boolean, default=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'))
    subject = db.Column(db.String(200))
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.receiver_id}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # 'application_status', 'message', 'system', 'reminder'
    link = db.Column(db.String(255))  # URL to related resource
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    icon = db.Column(db.String(50))  # Font Awesome icon class
    
    def __repr__(self):
        return f'<Notification {self.id} for user {self.user_id}>'

class ApplicationAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    total_applications = db.Column(db.Integer, default=0)
    approved_applications = db.Column(db.Integer, default=0)
    rejected_applications = db.Column(db.Integer, default=0)
    pending_applications = db.Column(db.Integer, default=0)
    new_registrations = db.Column(db.Integer, default=0)
    most_popular_school_id = db.Column(db.Integer, db.ForeignKey('school.id'))
    most_popular_district = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<Analytics {self.date}>'