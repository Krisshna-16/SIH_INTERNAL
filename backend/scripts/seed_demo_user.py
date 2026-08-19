import sys
import os
import logging

# Ensure backend root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal, Base, engine
from app.models.user import User, UserRole
from app.auth.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_demo_user")

DEMO_USERNAME = "investigator"
DEMO_PASSWORD = "demo123"


def seed_demo_user():
    """
    Seeds default demo investigator account for hackathon evaluation.
    
    DEMO CREDENTIALS:
    Username: investigator
    Password: demo123
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == DEMO_USERNAME).first()
        if existing:
            logger.info(f"Demo user '{DEMO_USERNAME}' already exists.")
            return

        hashed_pw = get_password_hash(DEMO_PASSWORD)
        demo_user = User(username=DEMO_USERNAME, hashed_password=hashed_pw, role=UserRole.INVESTIGATOR)
        db.add(demo_user)
        db.commit()
        logger.info(f"Successfully seeded demo user '{DEMO_USERNAME}' with role 'INVESTIGATOR'.")
    except Exception as e:
        logger.error(f"Failed to seed demo user: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_user()
