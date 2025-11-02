"""
Utility functions for ZebEduApplication
"""
import os
import secrets
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app, url_for
from flask_mail import Mail, Message as EmailMessage
from models import db, Notification, Message, ApplicationAnalytics
import requests

# Initialize Flask-Mail
mail = Mail()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, folder='uploads'):
    """Save uploaded file and return the file path"""
    if file and allowed_file(file.filename):
        # Create upload folder if it doesn't exist
        upload_folder = os.path.join(current_app.root_path, 'static', folder)
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        unique_filename = f"{secrets.token_hex(8)}_{filename}"
        file_path = os.path.join(upload_folder, unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Return relative path for database
        return f"{folder}/{unique_filename}"
    return None

def create_notification(user_id, title, message, type='system', link=None, icon='fa-bell'):
    """Create a notification for a user"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        link=link,
        icon=icon
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def send_email_notification(to_email, subject, body):
    """Send email notification"""
    try:
        msg = EmailMessage(
            subject=subject,
            recipients=[to_email],
            body=body,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_sms_notification(phone_number, message):
    """
    Send SMS notification
    Note: You need to sign up for an SMS API service like:
    - Twilio (https://www.twilio.com/)
    - Africa's Talking (https://africastalking.com/)
    - Clickatell (https://www.clickatell.com/)
    
    This is a placeholder function
    """
    # Example with Africa's Talking (popular in South Africa)
    # API_KEY = current_app.config.get('AFRICASTALKING_API_KEY')
    # USERNAME = current_app.config.get('AFRICASTALKING_USERNAME')
    
    # For now, just print (you'll need to implement actual SMS service)
    print(f"SMS to {phone_number}: {message}")
    return True

def notify_application_status_change(application, old_status, new_status):
    """Notify student when application status changes"""
    student = application.student
    school = application.school
    
    # Create in-app notification
    if new_status == 'approved':
        title = "🎉 Application Approved!"
        message = f"Congratulations! Your application to {school.name} has been approved."
        icon = "fa-check-circle"
    elif new_status == 'rejected':
        title = "Application Update"
        message = f"Your application to {school.name} has been reviewed. Please check your dashboard for details."
        icon = "fa-info-circle"
    elif new_status == 'under_review':
        title = "Application Under Review"
        message = f"Your application to {school.name} is now being reviewed by administrators."
        icon = "fa-hourglass-half"
    else:
        title = "Application Status Update"
        message = f"Your application to {school.name} status has changed to {new_status}."
        icon = "fa-bell"
    
    create_notification(
        user_id=student.id,
        title=title,
        message=message,
        type='application_status',
        link=url_for('student_dashboard'),
        icon=icon
    )
    
    # Send email if enabled
    if student.email_notifications:
        email_body = f"""
Dear {student.full_name},

Your application to {school.name} has been updated.

Status: {new_status.upper()}

Please log in to your dashboard to view more details:
{url_for('student_dashboard', _external=True)}

Best regards,
ZebEduApplication Team
        """
        send_email_notification(student.email, title, email_body)
    
    # Send SMS if enabled
    if student.sms_notifications and student.phone_number:
        sms_message = f"ZebEdu: Your application to {school.name} status: {new_status}. Check dashboard for details."
        send_sms_notification(student.phone_number, sms_message)
def get_location_from_coordinates(latitude, longitude):
    """
    Get location details from coordinates using OpenStreetMap Nominatim
    Returns suburb, district, and province information
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'ZebEduApplication/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if 'address' in data:
            address = data['address']
            
            # Extract suburb (most specific location)
            suburb = (address.get('suburb') or 
                     address.get('neighbourhood') or
                     address.get('residential') or
                     address.get('village') or
                     address.get('town') or
                     address.get('city') or
                     'Unknown')
            
            # Extract district/municipality
            district = (address.get('municipality') or 
                       address.get('city') or 
                       address.get('town') or 
                       suburb)
            
            province = address.get('state', 'Limpopo')
            
            return {
                'suburb': suburb,
                'district': district,
                'province': province,
                'full_address': data.get('display_name', '')
            }
    except Exception as e:
        print(f"Geocoding error: {e}")
    
    # Default fallback
    return {
        'suburb': 'Eduanpark',
        'district': 'Capricorn',
        'province': 'Limpopo',
        'full_address': 'Eduanpark, Polokwane, Limpopo'
    }
def update_daily_analytics():
    """Update daily analytics data"""
    from models import Application, User
    
    today = datetime.utcnow().date()
    
    # Check if analytics for today already exists
    analytics = ApplicationAnalytics.query.filter_by(date=today).first()
    
    if not analytics:
        analytics = ApplicationAnalytics(date=today)
        db.session.add(analytics)
    
    # Update counts
    analytics.total_applications = Application.query.count()
    analytics.approved_applications = Application.query.filter_by(status='approved').count()
    analytics.rejected_applications = Application.query.filter_by(status='rejected').count()
    analytics.pending_applications = Application.query.filter_by(status='pending').count()
    analytics.new_registrations = User.query.filter(
        User.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()
    
    # Most popular school
    from sqlalchemy import func
    popular_school = db.session.query(
        Application.school_id, 
        func.count(Application.school_id).label('count')
    ).group_by(Application.school_id).order_by(func.count(Application.school_id).desc()).first()
    
    if popular_school:
        analytics.most_popular_school_id = popular_school[0]
    
    db.session.commit()