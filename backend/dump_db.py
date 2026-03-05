from sqlmodel import Session, create_engine, select
from main import Site
import os

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

def dump_db():
    with Session(engine) as session:
        count = session.exec(select(Site)).all()
        print(f"Total sites in DB: {len(count)}")
        
        sites = session.exec(select(Site).limit(5)).all()
        for s in sites:
            print(f"ID: {s.id}, Name: {s.name}, Address: {s.address}, Brand: {s.brand}")

if __name__ == "__main__":
    dump_db()
