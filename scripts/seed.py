"""
Seed the database with sample data for demo / development.

Usage:
    python -m scripts.seed          (from project root)
    python scripts/seed.py          (also works)
"""

import sys
import os

# Ensure project root is on sys.path when run as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, Base, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.models import User, DiagnosticCentre, DiagnosticTest  # noqa: E402


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Guard: skip if data already exists.
    if db.query(User).first():
        print("Database already has data — skipping seed.")
        db.close()
        return

    # ---- Demo user ----
    user = User(
        email="demo@eve.health",
        full_name="Demo Patient",
        hashed_password=hash_password("demo1234"),
    )
    db.add(user)

    # ---- Centres & tests ----
    centres_data = [
        {
            "name": "City Diagnostics",
            "location": "Delhi",
            "tests": [
                ("Complete Blood Count (CBC)", 500),
                ("Lipid Profile", 800),
                ("Thyroid Panel (T3/T4/TSH)", 1200),
                ("HbA1c", 600),
            ],
        },
        {
            "name": "HealthFirst Labs",
            "location": "Mumbai",
            "tests": [
                ("Complete Blood Count (CBC)", 450),
                ("Liver Function Test (LFT)", 900),
                ("Kidney Function Test (KFT)", 850),
                ("Vitamin D", 1100),
                ("Vitamin B12", 950),
            ],
        },
        {
            "name": "Apollo Diagnostics",
            "location": "Bangalore",
            "tests": [
                ("Full Body Checkup", 2500),
                ("COVID-19 RT-PCR", 500),
                ("Dengue NS1 Antigen", 700),
                ("Urine Routine", 200),
            ],
        },
    ]

    for cd in centres_data:
        centre = DiagnosticCentre(name=cd["name"], location=cd["location"])
        db.add(centre)
        db.flush()  # materialise centre.id
        for test_name, price in cd["tests"]:
            db.add(DiagnosticTest(centre_id=centre.id, name=test_name, price=price))

    db.commit()
    db.close()
    print("✓ Seeded database with 3 centres, 13 tests, and 1 demo user.")
    print("  Demo login: demo@eve.health / demo1234")


if __name__ == "__main__":
    seed()
