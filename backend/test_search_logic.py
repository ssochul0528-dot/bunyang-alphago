from main import search_sites
import asyncio
import json

async def test_search():
    print("Testing search for '이안'...")
    results = await search_sites("이안")
    print(f"Results count: {len(results)}")
    for r in results:
        print(f" - {r.name} (Brand: {r.brand})")

    print("\nTesting search for '엘리움'...")
    results = await search_sites("엘리움")
    print(f"Results count: {len(results)}")
    for r in results:
        print(f" - {r.name} (Brand: {r.brand})")

    print("\nTesting search for '서울'...")
    results = await search_sites("서울")
    print(f"Results count: {len(results)}")
    for r in results:
        print(f" - {r.name} (Address: {r.address})")

    print("\nTesting search for '메이플'...")
    results = await search_sites("메이플")
    print(f"Results count: {len(results)}")
    for r in results:
        print(f" - {r.name}")

if __name__ == "__main__":
    asyncio.run(test_search())
