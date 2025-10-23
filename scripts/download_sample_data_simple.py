"""
Simple data downloader using direct HTTP requests.

Downloads sample data for frontend development.
"""

import asyncio
import json
import httpx
from pathlib import Path
from datetime import datetime


BASE_URL = "https://api.openparliament.ca"


async def download_data():
    """Download sample data from OpenParliament API."""
    
    data_dir = Path(__file__).parent.parent / '.data'
    data_dir.mkdir(exist_ok=True)
    
    print("📥 Downloading sample data from OpenParliament API...\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Download Bills
        print("📄 Fetching bills...")
        try:
            response = await client.get(f"{BASE_URL}/bills/?parliament=44&session=1&limit=50")
            if response.status_code == 200:
                data = response.json()
                bills = data.get('objects', [])
                bills_file = data_dir / 'bills.json'
                with open(bills_file, 'w', encoding='utf-8') as f:
                    json.dump(bills, f, indent=2)
                print(f"   ✅ Saved {len(bills)} bills")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Download Politicians  
        print("\n👥 Fetching politicians...")
        try:
            response = await client.get(f"{BASE_URL}/politicians/?limit=100&current=true")
            if response.status_code == 200:
                data = response.json()
                politicians = data.get('objects', [])
                politicians_file = data_dir / 'politicians.json'
                with open(politicians_file, 'w', encoding='utf-8') as f:
                    json.dump(politicians, f, indent=2)
                print(f"   ✅ Saved {len(politicians)} politicians")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Download Votes
        print("\n🗳️  Fetching votes...")
        try:
            response = await client.get(f"{BASE_URL}/votes/?parliament=44&session=1&limit=30")
            if response.status_code == 200:
                data = response.json()
                votes = data.get('objects', [])
                votes_file = data_dir / 'votes.json'
                with open(votes_file, 'w', encoding='utf-8') as f:
                    json.dump(votes, f, indent=2)
                print(f"   ✅ Saved {len(votes)} votes")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Download Debates
        print("\n💬 Fetching debates...")
        try:
            response = await client.get(f"{BASE_URL}/debates/?parliament=44&session=1&limit=20")
            if response.status_code == 200:
                data = response.json()
                debates = data.get('objects', [])
                debates_file = data_dir / 'debates.json'
                with open(debates_file, 'w', encoding='utf-8') as f:
                    json.dump(debates, f, indent=2)
                print(f"   ✅ Saved {len(debates)} debates")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Download Speeches
        print("\n🗣️  Fetching speeches...")
        try:
            response = await client.get(f"{BASE_URL}/speeches/?limit=100")
            if response.status_code == 200:
                data = response.json()
                speeches = data.get('objects', [])
                speeches_file = data_dir / 'speeches.json'
                with open(speeches_file, 'w', encoding='utf-8') as f:
                    json.dump(speeches, f, indent=2)
                print(f"   ✅ Saved {len(speeches)} speeches")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Create metadata
    metadata = {
        'downloaded_at': datetime.utcnow().isoformat(),
        'source': 'OpenParliament API',
        'parliament': 44,
        'session': 1
    }
    
    metadata_file = data_dir / 'metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n📊 Data saved to: {data_dir}")
    print("✅ Download complete!")


if __name__ == "__main__":
    asyncio.run(download_data())
