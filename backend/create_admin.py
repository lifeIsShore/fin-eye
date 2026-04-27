import asyncio
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.email == "admin@yagmurterminal.com"))
        user = res.scalars().first()
        if not user:
            user = User(
                email="admin@yagmurterminal.com",
                hashed_password=hash_password("admin"),
                name="Admin",
                is_active=True,
                is_verified=True,
                is_admin=True,
            )
            db.add(user)
            await db.commit()
            print("Admin created.")
        else:
            user.is_admin = True
            await db.commit()
            print("Admin already exists, promoted to admin.")

if __name__ == "__main__":
    asyncio.run(run())
