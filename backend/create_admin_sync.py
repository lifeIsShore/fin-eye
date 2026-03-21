from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.user import User
from app.core.security import hash_password

def run():
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "admin@fin-eye.com").first()
        if not user:
            user = User(
                email="admin@fin-eye.com",
                hashed_password=hash_password("admin"),
                is_active=True,
                is_admin=True,
                first_name="Admin",
                last_name="User"
            )
            db.add(user)
            db.commit()
            print("Admin created.")
        else:
            user.is_admin = True
            db.commit()
            print("Admin already exists, promoted to admin.")

if __name__ == "__main__":
    run()
