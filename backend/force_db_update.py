from main import create_db_and_tables, import_csv_data
import asyncio

async def force_sync():
    print("Forcing database update...")
    create_db_and_tables()
    print("Importing CSV data...")
    result = await import_csv_data()
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(force_sync())
