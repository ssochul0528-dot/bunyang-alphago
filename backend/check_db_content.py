from sqlmodel import Session, create_engine, select
from main import Site
import os

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

def check_db():
    with Session(engine) as session:
        # Check for '이안'
        iaan_sites = session.exec(select(Site).where(Site.brand == "이안")).all()
        print(f"Iaan sites found: {len(iaan_sites)}")
        for s in iaan_sites:
            print(f" - {s.name} ({s.id})")
            
        # Check for '엘리움'
        elium_sites = session.exec(select(Site).where(Site.brand == "엘리움")).all()
        print(f"Elium sites found: {len(elium_sites)}")
        for s in elium_sites:
            print(f" - {s.name} ({s.id})")

if __name__ == "__main__":
    if os.path.exists(sqlite_file_name):
        check_db()
    else:
        print("Database file not found!")
