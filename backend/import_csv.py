#!/usr/bin/env python3
"""
CSV 파일에서 분양 데이터를 읽어 데이터베이스에 import
"""

import csv
from sqlmodel import Field, Session, SQLModel, create_engine
from typing import Optional
import datetime

# Database setup
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

class Site(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    
    id: str = Field(primary_key=True)
    name: str
    address: str
    brand: Optional[str] = None
    category: str
    price: float
    target_price: float
    supply: int
    status: Optional[str] = None
    last_updated: datetime.datetime = Field(default_factory=datetime.datetime.now)

def import_csv(filename="sites_data.csv"):
    """CSV 파일에서 데이터 import"""
    SQLModel.metadata.create_all(engine)
    
    imported = 0
    updated = 0
    
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        with Session(engine) as session:
            for row in reader:
                site_id = row['id']
                existing = session.get(Site, site_id)
                
                if existing:
                    # 기존 데이터 업데이트
                    existing.name = row['name']
                    existing.address = row['address']
                    existing.brand = row['brand'] if row['brand'] else None
                    existing.category = row['category']
                    existing.price = float(row['price'])
                    existing.target_price = float(row['target_price'])
                    existing.supply = int(row['supply'])
                    existing.status = row['status'] if row['status'] else None
                    existing.last_updated = datetime.datetime.now()
                    updated += 1
                else:
                    # 새 데이터 추가
                    new_site = Site(
                        id=site_id,
                        name=row['name'],
                        address=row['address'],
                        brand=row['brand'] if row['brand'] else None,
                        category=row['category'],
                        price=float(row['price']),
                        target_price=float(row['target_price']),
                        supply=int(row['supply']),
                        status=row['status'] if row['status'] else None
                    )
                    session.add(new_site)
                    imported += 1
            
            session.commit()
    
    print(f"✅ Import 완료!")
    print(f"   신규 추가: {imported}개")
    print(f"   업데이트: {updated}개")
    print(f"   총: {imported + updated}개")
    
    return {"imported": imported, "updated": updated}

if __name__ == "__main__":
    print("CSV 데이터 import를 시작합니다...\n")
    result = import_csv()
    print(f"\n완료! 데이터베이스에 총 {result['imported'] + result['updated']}개의 현장이 등록되었습니다.")
