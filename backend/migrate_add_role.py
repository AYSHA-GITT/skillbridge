import sqlite3
import os
from werkzeug.security import generate_password_hash

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'skillbridge.db')

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing columns in students
cursor.execute("PRAGMA table_info(students)")
columns = [row[1] for row in cursor.fetchall()]

if 'role' not in columns:
    print("Adding 'role' column to students table...")
    cursor.execute("ALTER TABLE students ADD COLUMN role VARCHAR(20) DEFAULT 'student'")
    cursor.execute("UPDATE students SET role = 'student' WHERE role IS NULL")
    conn.commit()
    print("Column 'role' added successfully with default 'student'!")
else:
    print("'role' column already exists in students table.")

# Ensure existing students have role set to 'student' if null
cursor.execute("UPDATE students SET role = 'student' WHERE role IS NULL")
conn.commit()

# Check if admin user exists, or create one
cursor.execute("SELECT id, email, role FROM students WHERE email = 'admin@skillbridge.edu'")
admin = cursor.fetchone()

if not admin:
    print("Creating institution admin account: admin@skillbridge.edu...")
    pwd_hash = generate_password_hash("admin123")
    cursor.execute("""
        INSERT INTO students (name, email, password_hash, college, course, year, target_career, readiness_score, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Institution Administrator",
        "admin@skillbridge.edu",
        pwd_hash,
        "SkillBridge Central Consortium",
        "Institutional Administration",
        "Faculty",
        "Institutional Research",
        100.0,
        "admin",
        1
    ))
    conn.commit()
    print("Admin user created successfully! (Email: admin@skillbridge.edu, Password: admin123)")
else:
    print(f"Admin user exists with role: {admin[2]}. Ensuring role is 'admin'...")
    cursor.execute("UPDATE students SET role = 'admin' WHERE email = 'admin@skillbridge.edu'")
    conn.commit()

conn.close()
print("Migration completed.")
