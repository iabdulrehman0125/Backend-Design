from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

passwords = {
    "admin@uni.edu":   "admin123",
    "smith@uni.edu":   "teacher123",
    "ahmed@uni.edu":   "student123",
}

for email, pw in passwords.items():
    hashed = pwd_context.hash(pw)
    print(f"{email}")
    print(f"  {hashed}")
    print(f"  Length: {len(hashed)}")
    print()