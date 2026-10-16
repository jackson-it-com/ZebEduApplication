from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_from_directory,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from config import Config
from models import (
    db,
    User,
    School,
    Application,
    PasswordReset,
    Message,
    Notification,
    ApplicationAnalytics,
)
from utils import (
    mail,
    save_uploaded_file,
    create_notification,
    notify_application_status_change,
    get_location_from_coordinates,
    update_daily_analytics,
)
import secrets
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from flask import send_file
from flask import Flask


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'



app.config.from_object(Config)

# Use environment variables for config
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "default-secret-key")
app.config["DEBUG"] = os.environ.get("DEBUG", "False") == "True"

# Initialize extensions
db.init_app(app)
mail.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create tables and upload folder
with app.app_context():
    db.create_all()

    # Create upload folder
    upload_folder = os.path.join(app.root_path, "static", "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    # Create default admin if not exists
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@zebedu.com",
            role="admin",
            full_name="System Administrator",
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Default admin created: username='admin', password='admin123'")


# Context processor for notifications
@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        return {
            "unread_notifications": current_user.unread_notifications_count(),
            "unread_messages": current_user.unread_messages_count(),
        }
    return {}


# Routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        if current_user.role == "super_admin" or current_user.role == "school_admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        full_name = request.form.get("full_name")
        id_number = request.form.get("id_number")
        phone_number = request.form.get("phone_number")
        role = request.form.get("role", "student")  # NEW: Get role
        school_id = request.form.get("school_id")  # NEW: Get school_id

        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "danger")
            return redirect(url_for("register"))

        # Validate school_id for school admins
        if role == "school_admin":
            if not school_id:
                flash("Please select a school to manage", "danger")
                return redirect(url_for("register"))

            # Check if school exists
            school = School.query.get(school_id)
            if not school:
                flash("Invalid school selected", "danger")
                return redirect(url_for("register"))

        # Create new user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            id_number=id_number,
            phone_number=phone_number,
            role=role,
            school_id=int(school_id) if school_id else None,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Create welcome notification
        if role == "school_admin":
            school = School.query.get(school_id)
            message = f"Your school admin account for {school.name} has been created successfully!"
            link = url_for("admin_dashboard")
        else:
            message = "Your account has been created successfully. Start browsing schools and apply to your dream high school!"
            link = url_for("schools")

        create_notification(
            user_id=user.id,
            title="Welcome to ZebEduApplication! 🎓",
            message=message,
            type="system",
            link=link,
            icon="fa-graduation-cap",
        )

        flash(
            f'Registration successful! You can now login as {role.replace("_", " ").title()}.',
            "success",
        )
        return redirect(url_for("login"))

    # GET request - load all schools for dropdown
    schools = School.query.order_by(School.name).all()
    return render_template("register.html", schools=schools)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Login successful!", "success")

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("student_dashboard"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        id_last_4 = request.form.get("id_last_4")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Validate passwords match
        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("forgot_password"))

        # Find user by email
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("No account found with that email address.", "danger")
            return redirect(url_for("forgot_password"))

        # Check if user has ID number registered
        if not user.id_number:
            flash(
                "Your account does not have an ID number registered. Please contact the administrator.",
                "danger",
            )
            return redirect(url_for("forgot_password"))

        # Verify last 4 digits of ID number
        if user.id_number[-4:] != id_last_4:
            flash(
                "❌ Security verification failed! The last 4 digits of your ID number do not match our records.",
                "danger",
            )
            return redirect(url_for("forgot_password"))

        # All checks passed - reset password
        user.set_password(new_password)
        db.session.commit()

        # Create notification
        create_notification(
            user_id=user.id,
            title="Password Changed Successfully",
            message="Your password has been reset successfully. If you did not make this change, please contact support immediately.",
            type="system",
            link=url_for("login"),
            icon="fa-lock",
        )

        flash(
            "✅ Password reset successful! You can now login with your new password.",
            "success",
        )
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    # This route is kept for backward compatibility but redirects to new system
    flash("Please use the new password reset system with ID verification.", "info")
    return redirect(url_for("forgot_password"))


@app.route("/student/dashboard")
@login_required
def student_dashboard():
    if current_user.role != "student":
        return redirect(url_for("admin_dashboard"))

    applications = (
        Application.query.filter_by(student_id=current_user.id)
        .order_by(Application.applied_at.desc())
        .all()
    )
    recent_notifications = (
        Notification.query.filter_by(user_id=current_user.id).limit(5).all()
    )

    return render_template(
        "student_dashboard.html",
        applications=applications,
        recent_notifications=recent_notifications,
    )


@app.route("/application-form")
@login_required
def application_form():
    if current_user.role != "student":
        flash("Only students can access the application form", "warning")
        return redirect(url_for("admin_dashboard"))

    return render_template("application_form.html")


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    # Only admins can access
    if current_user.role not in ["school_admin", "super_admin"]:
        return redirect(url_for("student_dashboard"))

    # Initialize default values
    admin_name = current_user.full_name or current_user.username
    my_school = None
    
    # Super admin sees ALL data
    if current_user.is_super_admin():
        total_students = User.query.filter_by(role="student").count()
        total_schools = School.query.count()
        total_applications = Application.query.count()
        pending_applications = Application.query.filter_by(status="pending").count()
        recent_applications = (
            Application.query.order_by(Application.applied_at.desc()).limit(10).all()
        )

    # School admin sees ONLY their school's data
    elif current_user.is_school_admin():
        # Get the school this admin manages
        my_school = School.query.get(current_user.school_id)
        if not my_school:
            flash(
                "Your school assignment is invalid. Please contact support.", "danger"
            )
            return redirect(url_for("index"))

        # Count applications by status for THIS school
        total_applications = Application.query.filter_by(school_id=my_school.id).count()
        pending_applications = Application.query.filter_by(
            school_id=my_school.id, status="pending"
        ).count()
        approved_applications = Application.query.filter_by(
            school_id=my_school.id, status="approved"
        ).count()
        rejected_applications = Application.query.filter_by(
            school_id=my_school.id, status="rejected"
        ).count()

        # Unique students for this school
        total_students = (
            db.session.query(Application.student_id)
            .filter_by(school_id=my_school.id)
            .distinct()
            .count()
        )

        # Recent applications for THIS school only
        recent_applications = (
            Application.query.filter_by(school_id=my_school.id)
            .order_by(Application.applied_at.desc())
            .limit(10)
            .all()
        )

        total_schools = 1  # School admin manages 1 school
    
    else:
        # Fallback for 'admin' role (legacy)
        total_students = User.query.filter_by(role="student").count()
        total_schools = School.query.count()
        total_applications = Application.query.count()
        pending_applications = Application.query.filter_by(status="pending").count()
        recent_applications = (
            Application.query.order_by(Application.applied_at.desc()).limit(10).all()
        )

    # Get analytics for today
    today = datetime.utcnow().date()
    analytics = ApplicationAnalytics.query.filter_by(date=today).first()

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_schools=total_schools,
        total_applications=total_applications,
        pending_applications=pending_applications,
        recent_applications=recent_applications,
        analytics=analytics,
        my_school=my_school,
        admin_name=admin_name,
    )


# =======================
# MESSAGING ROUTES (UNIFIED)
# =======================
@app.route("/messages")
@login_required
def messages():
    sent_messages = (
        Message.query.filter_by(sender_id=current_user.id)
        .order_by(Message.sent_at.desc())
        .all()
    )
    received_messages = (
        Message.query.filter_by(receiver_id=current_user.id)
        .order_by(Message.sent_at.desc())
        .all()
    )

    # Get all users for dropdown
    if current_user.role == "admin":
        available_users = User.query.filter_by(role="student").all()
    else:
        available_users = User.query.filter_by(role="admin").all()

    return render_template(
        "messages.html",
        sent_messages=sent_messages,
        received_messages=received_messages,
        available_users=available_users,
    )


@app.route("/messages/send", methods=["POST"])
@login_required
def send_message():
    receiver_id = request.form.get("receiver_id")
    subject = request.form.get("subject")
    body = request.form.get("body")
    application_id = request.form.get("application_id")

    if not receiver_id or not subject or not body:
        flash("All fields are required!", "danger")
        return redirect(url_for("messages"))

    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        subject=subject,
        body=body,
        application_id=application_id if application_id else None,
    )

    db.session.add(message)
    db.session.commit()

    # Create notification for receiver
    create_notification(
        user_id=int(receiver_id),
        title=f"New Message: {subject}",
        message=f"You have a new message from {current_user.full_name}",
        type="message",
        link=url_for("messages"),
        icon="fa-envelope",
    )

    flash("Message sent successfully!", "success")
    return redirect(url_for("messages"))


@app.route("/messages/<int:user_id>")
@login_required
def messages_with_user(user_id):
    """Display message thread between current user and another user"""
    messages_list = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.sent_at.asc()).all()

    other_user = User.query.get_or_404(user_id)
    return render_template("message_thread.html", messages=messages_list, other_user=other_user)


@app.route("/messages/<int:msg_id>/read", methods=["POST"])
@login_required
def mark_message_read(msg_id):
    message = Message.query.get_or_404(msg_id)
    if message.receiver_id == current_user.id:
        message.read = True
        message.read_at = datetime.utcnow()
        db.session.commit()
    return jsonify({"success": True})


@app.route("/schools")
@login_required
def schools():
    suburb_filter = request.args.get("suburb", "")
    district_filter = request.args.get("district", "")

    # Filter by suburb first (most specific), then district
    if suburb_filter:
        schools_list = (
            School.query.filter_by(suburb=suburb_filter)
            .order_by(School.pass_rate.desc())
            .all()
        )
    elif district_filter:
        schools_list = (
            School.query.filter_by(district=district_filter)
            .order_by(School.pass_rate.desc())
            .all()
        )
    else:
        schools_list = School.query.order_by(School.pass_rate.desc()).all()

    # Get all unique suburbs and districts for filters
    suburbs = db.session.query(School.suburb).distinct().order_by(School.suburb).all()
    suburbs = [s[0] for s in suburbs if s[0]]

    districts = db.session.query(School.district).distinct().all()
    districts = [d[0] for d in districts]

    # Pass ALL required variables to template
    return render_template(
        "schools.html",
        schools=schools_list,
        suburbs=suburbs,
        districts=districts,
        selected_suburb=suburb_filter,
        selected_district=district_filter,
    )


@app.route("/apply/<int:school_id>", methods=["POST"])
@login_required
def apply_to_school(school_id):
    if current_user.role != "student":
        return jsonify({"success": False, "message": "Only students can apply"}), 403

    # Check if already applied
    existing = Application.query.filter_by(
        student_id=current_user.id, school_id=school_id
    ).first()
    if existing:
        flash("You have already applied to this school", "warning")
        return redirect(url_for("schools"))

    # Handle file uploads
    previous_report = save_uploaded_file(request.files.get("previous_report"))
    birth_certificate = save_uploaded_file(request.files.get("birth_certificate"))
    proof_of_residence = save_uploaded_file(request.files.get("proof_of_residence"))
    id_document = save_uploaded_file(request.files.get("id_document"))

    application = Application(
        student_id=current_user.id,
        school_id=school_id,
        motivation_letter=request.form.get("motivation_letter", ""),
        previous_report=previous_report,
        birth_certificate=birth_certificate,
        proof_of_residence=proof_of_residence,
        id_document=id_document,
    )

    db.session.add(application)
    db.session.commit()

    # Create notification
    school = School.query.get(school_id)
    create_notification(
        user_id=current_user.id,
        title="Application Submitted Successfully! 📝",
        message=f"Your application to {school.name} has been submitted and is pending review.",
        type="application_status",
        link=url_for("view_application", app_id=application.id),
        icon="fa-paper-plane",
    )

    flash("Application submitted successfully!", "success")
    return redirect(url_for("student_dashboard"))


# Application details view
@app.route("/application/<int:app_id>")
@login_required
def view_application(app_id):
    application = Application.query.get_or_404(app_id)

    # Check permissions - students can only view their own applications
    if current_user.role == "student" and application.student_id != current_user.id:
        flash("Unauthorized access to this application", "danger")
        return redirect(url_for("student_dashboard"))

    # Mark as viewed by admin
    if current_user.role == "admin" and not application.viewed_by_admin:
        application.viewed_by_admin = True
        db.session.commit()

    return render_template("application_detail.html", application=application)


# Cancel application route
@app.route("/application/<int:app_id>/cancel", methods=["POST"])
@login_required
def cancel_application(app_id):
    application = Application.query.get_or_404(app_id)

    # Check permissions - only the student who created the application can cancel it
    if current_user.role != "student" or application.student_id != current_user.id:
        flash("Unauthorized action", "danger")
        return redirect(url_for("student_dashboard"))

    # Check if application can be cancelled (only pending applications)
    if application.status != "pending":
        flash(
            f"Cannot cancel an application with status: {application.status}", "warning"
        )
        return redirect(url_for("student_dashboard"))

    # Get cancellation reason
    cancellation_reason = request.form.get("cancellation_reason", "No reason provided")

    # Update application status
    old_status = application.status
    application.status = "cancelled"
    application.admin_notes = f"CANCELLED BY STUDENT\nReason: {cancellation_reason}\nCancelled at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"

    db.session.commit()

    # Create notification for student
    school = application.school
    create_notification(
        user_id=current_user.id,
        title="Application Cancelled",
        message=f"Your application to {school.name} has been cancelled successfully.",
        type="application_status",
        link=url_for("student_dashboard"),
        icon="fa-times-circle",
    )

    # Update analytics
    update_daily_analytics()

    flash(
        f"Your application to {school.name} has been cancelled successfully.", "success"
    )
    return redirect(url_for("student_dashboard"))

@app.route("/admin/applications/<int:app_id>/review", methods=["POST"])
@login_required
def review_application(app_id):

    # Only allow school admins or super admins
    if current_user.role not in ["school_admin", "super_admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    application = Application.query.get_or_404(app_id)

    # Restrict school admin to ONLY their school
    if current_user.role == "school_admin":
        if application.school_id != current_user.school_id:
            return jsonify(
                {"success": False, "message": "Access denied: Not your school"}
            ), 403

    old_status = application.status
    new_status = request.form.get("status")
    admin_notes = request.form.get("admin_notes", "")

    # NEW: School info from approve modal
    school_name = request.form.get("school_name")
    reporting_date = request.form.get("reporting_date")

    application.status = new_status
    application.admin_notes = admin_notes
    application.reviewed_at = datetime.utcnow()
    application.viewed_by_admin = True

    db.session.commit()

    # ======================
    # STUDENT NOTIFICATION
    # ======================
    if new_status == "approved":
        message = (
            f"🎉 Congratulations {application.student.full_name}!\n\n"
            f"Your application has been APPROVED.\n\n"
            f"🏫 School: {school_name or application.school.name}\n"
            f"📅 Reporting Date: {reporting_date or 'To be communicated'}\n\n"
            f"ℹ️ Important Information:\n"
            f"{admin_notes if admin_notes else 'No additional instructions.'}"
        )

        create_notification(
            user_id=application.student_id,
            title="Application Approved 🎓",
            message=message,
            type="application_status",
            link=url_for("view_application", app_id=application.id),
            icon="fa-check-circle",
        )

    elif new_status == "rejected":
        create_notification(
            user_id=application.student_id,
            title="Application Rejected",
            message=f"Your application has been rejected.\n\nReason:\n{admin_notes}",
            type="application_status",
            link=url_for("view_application", app_id=application.id),
            icon="fa-times-circle",
        )

    elif new_status == "pending":
        create_notification(
            user_id=application.student_id,
            title="Application Status Updated",
            message="Your application status has been reset to pending.",
            type="application_status",
            link=url_for("view_application", app_id=application.id),
            icon="fa-clock",
        )

    # Analytics
    update_daily_analytics()

    # Flash messages
    if new_status == "approved":
        flash("Application approved and student notified.", "success")
    elif new_status == "rejected":
        flash("Application rejected and student notified.", "warning")
    elif new_status == "pending":
        flash("Application reset back to pending.", "info")
    else:
        flash("Application status updated.", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/api/detect-location", methods=["POST"])
@login_required
def detect_location():
    data = request.get_json()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    # Use real geocoding to get suburb
    location_data = get_location_from_coordinates(latitude, longitude)

    return jsonify(location_data)


@app.route("/admin/school/<int:school_id>/applications")
@login_required
def school_applications(school_id):
    # Only admins can access
    if current_user.role not in ["school_admin", "super_admin"]:
        flash("Unauthorized access", "danger")
        return redirect(url_for("login"))

    # Restrict school_admin to their own school
    if current_user.role == "school_admin" and current_user.school_id != school_id:
        flash("Access denied: Not your school", "danger")
        return redirect(url_for("admin_dashboard"))

    school = School.query.get_or_404(school_id)
    applications = (
        Application.query.filter_by(school_id=school_id)
        .order_by(Application.applied_at.desc())
        .all()
    )

    return render_template(
        "school_applications.html", school=school, applications=applications
    )
#----------------------------------------------------------------------------
@app.route('/application/<int:app_id>/replace-document', methods=['POST'])
@login_required
def replace_document(app_id):
    # Get the application
    application = Application.query.get_or_404(app_id)
    
    # Check if user is the owner and application is pending
    if current_user.id != application.student_id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('student_dashboard'))
    
    if application.status != 'pending':
        flash('You can only replace documents for pending applications.', 'warning')
        return redirect(url_for('view_application', app_id=app_id))
    
    # Get form data
    document_type = request.form.get('document_type')
    reason = request.form.get('reason', '')
    file = request.files.get('document')
    
    if not file or file.filename == '':
        flash('No file selected!', 'danger')
        return redirect(url_for('view_application', app_id=app_id))
    
    # Validate file
    allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        flash('Invalid file type! Only PDF, JPG, and PNG are allowed.', 'danger')
        return redirect(url_for('view_application', app_id=app_id))
    
    try:
        # Delete old file if it exists
        old_file_path = None
        if document_type == 'previous_report' and application.previous_report:
            old_file_path = os.path.join(app.root_path, 'static', application.previous_report)
        elif document_type == 'birth_certificate' and application.birth_certificate:
            old_file_path = os.path.join(app.root_path, 'static', application.birth_certificate)
        elif document_type == 'proof_of_residence' and application.proof_of_residence:
            old_file_path = os.path.join(app.root_path, 'static', application.proof_of_residence)
        elif document_type == 'id_document' and application.id_document:
            old_file_path = os.path.join(app.root_path, 'static', application.id_document)
        
        # Delete old file
        if old_file_path and os.path.exists(old_file_path):
            os.remove(old_file_path)
        
        # Save new file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_extension = filename.rsplit('.', 1)[1]
        new_filename = f"{document_type}_{application.student_id}_{timestamp}.{file_extension}"
        upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'documents')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, new_filename)
        file.save(file_path)
        
        # Update database
        relative_path = f'uploads/documents/{new_filename}'
        if document_type == 'previous_report':
            application.previous_report = relative_path
        elif document_type == 'birth_certificate':
            application.birth_certificate = relative_path
        elif document_type == 'proof_of_residence':
            application.proof_of_residence = relative_path
        elif document_type == 'id_document':
            application.id_document = relative_path
        
        db.session.commit()
        
        flash(f'Document replaced successfully! {reason if reason else ""}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error replacing document: {str(e)}', 'danger')
    
    return redirect(url_for('view_application', app_id=app_id))

# Notifications
@app.route("/notifications")
@login_required
def notifications():
    user_notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("notifications.html", notifications=user_notifications)


@app.route("/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notif_id):
    notification = Notification.query.get_or_404(notif_id)
    if notification.user_id == current_user.id:
        notification.read = True
        db.session.commit()
    return jsonify({"success": True})


@app.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, read=False).update(
        {"read": True}
    )
    db.session.commit()
    return jsonify({"success": True})


# Analytics
@app.route("/admin/analytics")
@login_required
def analytics():
    if current_user.role != "admin":
        return redirect(url_for("student_dashboard"))

    # Get last 30 days analytics
    thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
    analytics_data = (
        ApplicationAnalytics.query.filter(ApplicationAnalytics.date >= thirty_days_ago)
        .order_by(ApplicationAnalytics.date.desc())
        .all()
    )

    # Application statistics
    from sqlalchemy import func

    status_stats = (
        db.session.query(Application.status, func.count(Application.id).label("count"))
        .group_by(Application.status)
        .all()
    )

    # Popular schools
    popular_schools = (
        db.session.query(School.name, func.count(Application.id).label("app_count"))
        .join(Application)
        .group_by(School.id)
        .order_by(func.count(Application.id).desc())
        .limit(10)
        .all()
    )

    # District distribution
    district_stats = (
        db.session.query(School.district, func.count(Application.id).label("count"))
        .join(Application)
        .group_by(School.district)
        .all()
    )

    return render_template(
        "analytics.html",
        analytics_data=analytics_data,
        status_stats=status_stats,
        popular_schools=popular_schools,
        district_stats=district_stats,
    )


# Profile & Settings
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name")
        current_user.email = request.form.get("email")
        current_user.phone_number = request.form.get("phone_number")
        current_user.email_notifications = "email_notifications" in request.form
        current_user.sms_notifications = "sms_notifications" in request.form

        # Handle profile photo upload
        if "profile_photo" in request.files:
            profile_photo = save_uploaded_file(
                request.files["profile_photo"], folder="profiles"
            )
            if profile_photo:
                current_user.profile_photo = profile_photo

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html")

# Add these routes to your app.py file

@app.route('/admin/approved-students')
@login_required
def approved_students():
    """View list of approved students"""
    # Check if user is admin (either school admin or super admin)
    if not (current_user.is_school_admin() or current_user.is_super_admin()):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Get approved applications
    if current_user.is_school_admin() and current_user.school_id:
        # School admin sees only their school's approved students
        approved_apps = Application.query.filter_by(
            school_id=current_user.school_id,
            status='approved'
        ).order_by(Application.applied_at.desc()).all()
    else:
        # Super admin sees all approved students
        approved_apps = Application.query.filter_by(
            status='approved'
        ).order_by(Application.applied_at.desc()).all()
    
    return render_template('approved_students.html', applications=approved_apps)


@app.route('/admin/rejected-students')
@login_required
def rejected_students():
    """View list of rejected students"""
    # Check if user is admin (either school admin or super admin)
    if not (current_user.is_school_admin() or current_user.is_super_admin()):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Get rejected applications
    if current_user.is_school_admin() and current_user.school_id:
        # School admin sees only their school's rejected students
        rejected_apps = Application.query.filter_by(
            school_id=current_user.school_id,
            status='rejected'
        ).order_by(Application.applied_at.desc()).all()
    else:
        # Super admin sees all rejected students
        rejected_apps = Application.query.filter_by(
            status='rejected'
        ).order_by(Application.applied_at.desc()).all()
    
    return render_template('rejected_students.html', applications=rejected_apps)
@app.route('/application/<int:app_id>/toggle-document-approval', methods=['POST'])
@login_required
def toggle_document_approval(app_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    application = Application.query.get_or_404(app_id)
    data = request.get_json()
    
    document_type = data.get('document_type')
    approved = data.get('approved', False)
    
    # Map document types to approval fields
    approval_fields = {
        'previous_report': 'previous_report_approved',
        'birth_certificate': 'birth_certificate_approved',
        'proof_of_residence': 'proof_of_residence_approved',
        'id_document': 'id_document_approved'
    }
    
    if document_type in approval_fields:
        setattr(application, approval_fields[document_type], approved)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid document type'}), 400

@app.route('/admin/download-approved-pdf')
@login_required
def download_approved_pdf():
    """Download PDF of approved students"""
    # Check if user is admin (either school admin or super admin)
    if not (current_user.is_school_admin() or current_user.is_super_admin()):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from io import BytesIO
    from datetime import datetime
    
    # Get approved applications
    if current_user.is_school_admin() and current_user.school_id:
        approved_apps = Application.query.filter_by(
            school_id=current_user.school_id,
            status='approved'
        ).order_by(Application.applied_at.desc()).all()
        school = School.query.get(current_user.school_id)
        school_name = school.name if school else "Unknown School"
    else:
        approved_apps = Application.query.filter_by(
            status='approved'
        ).order_by(Application.applied_at.desc()).all()
        school_name = "All Schools"
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#28a745'),
        spaceAfter=30,
        alignment=1  # Center
    )
    title = Paragraph(f"Approved Students - {school_name}", title_style)
    elements.append(title)
    
    # Date
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=1
    )
    date_text = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", date_style)
    elements.append(date_text)
    elements.append(Spacer(1, 20))
    
    # Table data
    data = [['#', 'Student Name', 'ID Number', 'School', 'Grade', 'Applied Date', 'Approved Date']]
    
    for idx, app in enumerate(approved_apps, 1):
        data.append([
            str(idx),
            app.student.full_name or 'N/A',
            app.student.id_number or 'N/A',
            app.school.name,
            app.student.grade or 'Grade 8',
            app.applied_at.strftime('%Y-%m-%d'),
            app.reviewed_at.strftime('%Y-%m-%d') if app.reviewed_at else 'N/A'
        ])
    
    # Create table
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'approved_students_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )


@app.route('/admin/download-rejected-pdf')
@login_required
def download_rejected_pdf():
    """Download PDF of rejected students"""
    # Check if user is admin (either school admin or super admin)
    if not (current_user.is_school_admin() or current_user.is_super_admin()):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from io import BytesIO
    from datetime import datetime
    
    # Get rejected applications
    if current_user.is_school_admin() and current_user.school_id:
        rejected_apps = Application.query.filter_by(
            school_id=current_user.school_id,
            status='rejected'
        ).order_by(Application.applied_at.desc()).all()
        school = School.query.get(current_user.school_id)
        school_name = school.name if school else "Unknown School"
    else:
        rejected_apps = Application.query.filter_by(
            status='rejected'
        ).order_by(Application.applied_at.desc()).all()
        school_name = "All Schools"
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#dc3545'),
        spaceAfter=30,
        alignment=1  # Center
    )
    title = Paragraph(f"Rejected Students - {school_name}", title_style)
    elements.append(title)
    
    # Date
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=1
    )
    date_text = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", date_style)
    elements.append(date_text)
    elements.append(Spacer(1, 20))
    
    # Table data
    data = [['#', 'Student Name', 'ID Number', 'School', 'Grade', 'Applied Date', 'Rejected Date', 'Reason']]
    
    for idx, app in enumerate(rejected_apps, 1):
        reason = app.admin_notes[:30] + '...' if app.admin_notes and len(app.admin_notes) > 30 else (app.admin_notes or 'N/A')
        data.append([
            str(idx),
            app.student.full_name or 'N/A',
            app.student.id_number or 'N/A',
            app.school.name,
            app.student.grade or 'N/A',
            app.applied_at.strftime('%Y-%m-%d'),
            app.reviewed_at.strftime('%Y-%m-%d') if app.reviewed_at else 'N/A',
            reason
        ])
    
    # Create table
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc3545')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'rejected_students_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )# File downloads (for admins to view uploaded documents)
@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    try:
        # Get the full path to the uploads directory
        upload_dir = os.path.join(app.root_path, "static", "uploads")

        # Check if file exists
        file_path = os.path.join(upload_dir, filename)
        if not os.path.exists(file_path):
            flash("File not found", "danger")
            return redirect(request.referrer or url_for("student_dashboard"))

        # Serve the file
        directory = os.path.dirname(file_path)
        filename_only = os.path.basename(file_path)
        return send_from_directory(directory, filename_only, as_attachment=True)
    except Exception as e:
        flash(f"Error downloading file: {str(e)}", "danger")
        return redirect(request.referrer or url_for("student_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)