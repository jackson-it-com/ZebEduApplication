from app import app, db, User, School

with app.app_context():
    print("\n" + "="*50)
    print("CHECKING ADMIN DATA")
    print("="*50 + "\n")
    
    # Check all admins
    admins = User.query.filter(User.role.in_(['admin', 'school_admin', 'super_admin'])).all()
    
    if not admins:
        print("❌ No admins found in database!")
    else:
        print(f"✅ Found {len(admins)} admin(s):\n")
        
        for admin in admins:
            print(f"Username: {admin.username}")
            print(f"Role: {admin.role}")
            print(f"Full Name: {admin.full_name if admin.full_name else '❌ NOT SET'}")
            print(f"Email: {admin.email}")
            print(f"School ID: {admin.school_id if admin.school_id else '❌ NOT SET'}")
            
            if admin.school_id:
                school = School.query.get(admin.school_id)
                if school:
                    print(f"School Name: ✅ {school.name}")
                    print(f"School Location: {school.suburb}, {school.district}")
                else:
                    print(f"School: ❌ School ID {admin.school_id} not found!")
            
            print("-" * 50)
    
    # Check all schools
    print("\n" + "="*50)
    print("ALL SCHOOLS IN DATABASE")
    print("="*50 + "\n")
    
    schools = School.query.all()
    if not schools:
        print("❌ No schools found!")
    else:
        print(f"✅ Found {len(schools)} school(s):\n")
        for school in schools:
            print(f"ID: {school.id} | Name: {school.name}")