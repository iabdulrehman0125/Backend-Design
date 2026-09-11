from app.database import Base, engine, SessionLocal
from app.models import User, Department, Student, Teacher, Course
from app.security import hash_password


def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Database already seeded.")
            return

        cs = Department(name="Computer Science", code="CS")
        ee = Department(name="Electrical Engineering", code="EE")
        db.add_all([cs, ee])
        db.commit()

        admin = User(
            email="admin@uni.edu",
            password_hash=hash_password("admin123"),
            full_name="System Admin",
            role="admin",
        )
        teacher_user = User(
            email="smith@uni.edu",
            password_hash=hash_password("teacher123"),
            full_name="Dr. John Smith",
            role="teacher",
        )
        student_user = User(
            email="ahmed@uni.edu",
            password_hash=hash_password("student123"),
            full_name="Ahmed Hassan",
            role="student",
        )
        db.add_all([admin, teacher_user, student_user])
        db.commit()

        db.add(Teacher(user_id=teacher_user.id, employee_code="TCH-2019-014",
                       department_id=cs.id, designation="Professor"))
        db.add(Student(user_id=student_user.id, roll_number="UNI-2024-8842",
                       department_id=cs.id, batch_year=2022, current_semester=5))
        db.add(Course(code="CS301", title="Artificial Intelligence", credits=4,
                      department_id=cs.id, semester=5))
        db.commit()
        print("✅ Seed complete.")
        print("   admin@uni.edu / admin123")
        print("   smith@uni.edu / teacher123")
        print("   ahmed@uni.edu / student123")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()