from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal, User, init_db
from app.services.auth import hash_password


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        accounts = [
            ("Demo Administrator", "admin@mitadt.local", "admin", "admin-demo-123"),
            ("Demo Student", "student@mitadt.local", "student", "student-demo-123"),
        ]
        for name, email, role, password in accounts:
            if db.query(User).filter_by(email=email).first():
                continue
            db.add(User(name=name, email=email, role=role, password_hash=hash_password(password)))
        db.commit()
        print("Demo accounts ensured:")
        print("  Admin:   admin@mitadt.local / admin-demo-123")
        print("  Student: student@mitadt.local / student-demo-123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
