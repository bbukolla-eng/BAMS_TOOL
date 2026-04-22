"""
Seed script: create the default organization and admin user.
Run FIRST before other seed scripts.
Usage: python scripts/seed_users.py
"""
import asyncio
import sys
sys.path.insert(0, "backend")

from core.database import AsyncSessionLocal
from core.security import hash_password
from models.user import Organization, User, UserRole, PlanTier
from sqlalchemy import select


DEFAULT_ORG_NAME = "BAMS Demo Org"
DEFAULT_ADMIN_EMAIL = "admin@bams.local"
DEFAULT_ADMIN_PASSWORD = "Admin1234!"


async def seed():
    async with AsyncSessionLocal() as db:
        # Org
        result = await db.execute(select(Organization).where(Organization.name == DEFAULT_ORG_NAME))
        org = result.scalar_one_or_none()
        if not org:
            org = Organization(
                name=DEFAULT_ORG_NAME,
                slug="bams-demo",
                plan=PlanTier.pro,
                is_active=True,
            )
            db.add(org)
            await db.flush()
            print(f"Created organization: {org.name} (id={org.id})")
        else:
            print(f"Organization already exists (id={org.id})")

        # Admin user
        user_result = await db.execute(select(User).where(User.email == DEFAULT_ADMIN_EMAIL))
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(
                org_id=org.id,
                email=DEFAULT_ADMIN_EMAIL,
                hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
                full_name="BAMS Admin",
                role=UserRole.admin,
                is_active=True,
            )
            db.add(user)
            print(f"Created admin user: {DEFAULT_ADMIN_EMAIL}")
        else:
            print(f"Admin user already exists (id={user.id})")

        await db.commit()
        print("\nSeed complete.")
        print(f"  Login: {DEFAULT_ADMIN_EMAIL}")
        print(f"  Password: {DEFAULT_ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
