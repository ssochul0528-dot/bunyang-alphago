from main import create_db_and_tables, import_csv_data
import asyncio

async def force_sync():
    print("Forcing database update...")
    from main import engine, Site
    from sqlmodel import Session, select, delete
    
    with Session(engine) as session:
        print("Clearing existing Site data...")
        session.exec(delete(Site))
        session.commit()
        
    create_db_and_tables()
    print("Importing CSV data...")
    result = await import_csv_data()
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(force_sync())
