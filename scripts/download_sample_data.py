"""
Download sample data from OpenParliament API for local testing.

Saves data to .data/ directory (git ignored).

Responsibility: Local data collection for frontend development
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.adapters.openparliament_bills import OpenParliamentBillsAdapter
from src.adapters.openparliament_politicians import OpenParliamentPoliticiansAdapter
from src.adapters.openparliament_votes import OpenParliamentVotesAdapter
from src.adapters.openparliament_debates import OpenParliamentDebatesAdapter


async def download_sample_data():
    """Download sample data from all adapters."""
    
    # Create data directory
    data_dir = Path(__file__).parent.parent / '.data'
    data_dir.mkdir(exist_ok=True)
    
    print("📥 Downloading sample data from OpenParliament API...\n")
    
    # Initialize adapters
    bills_adapter = OpenParliamentBillsAdapter()
    politicians_adapter = OpenParliamentPoliticiansAdapter()
    votes_adapter = OpenParliamentVotesAdapter()
    debates_adapter = OpenParliamentDebatesAdapter()
    
    # Download Bills
    print("📄 Fetching bills...")
    try:
        bills = await bills_adapter.fetch_bills(limit=50, parliament=44, session=1)
        bills_file = data_dir / 'bills.json'
        with open(bills_file, 'w', encoding='utf-8') as f:
            json.dump([b.model_dump() for b in bills], f, indent=2, default=str)
        print(f"   ✅ Saved {len(bills)} bills to {bills_file}")
    except Exception as e:
        print(f"   ❌ Error fetching bills: {e}")
    
    # Download Politicians
    print("\n👥 Fetching politicians...")
    try:
        politicians = await politicians_adapter.fetch_politicians(limit=100)
        politicians_file = data_dir / 'politicians.json'
        with open(politicians_file, 'w', encoding='utf-8') as f:
            json.dump(politicians, f, indent=2, default=str)
        print(f"   ✅ Saved {len(politicians)} politicians to {politicians_file}")
    except Exception as e:
        print(f"   ❌ Error fetching politicians: {e}")
    
    # Download Votes
    print("\n🗳️  Fetching votes...")
    try:
        votes = await votes_adapter.fetch_votes(limit=30, parliament=44, session=1)
        votes_file = data_dir / 'votes.json'
        with open(votes_file, 'w', encoding='utf-8') as f:
            json.dump([v for v in votes], f, indent=2, default=str)
        print(f"   ✅ Saved {len(votes)} votes to {votes_file}")
    except Exception as e:
        print(f"   ❌ Error fetching votes: {e}")
    
    # Download Debates
    print("\n💬 Fetching debates...")
    try:
        debates = await debates_adapter.fetch_debates(limit=20, parliament=44, session=1)
        debates_file = data_dir / 'debates.json'
        with open(debates_file, 'w', encoding='utf-8') as f:
            json.dump(debates, f, indent=2, default=str)
        print(f"   ✅ Saved {len(debates)} debates to {debates_file}")
    except Exception as e:
        print(f"   ❌ Error fetching debates: {e}")
    
    # Download sample speeches
    print("\n🗣️  Fetching speeches...")
    try:
        speeches = await debates_adapter.fetch_speeches(limit=50)
        speeches_file = data_dir / 'speeches.json'
        with open(speeches_file, 'w', encoding='utf-8') as f:
            json.dump(speeches, f, indent=2, default=str)
        print(f"   ✅ Saved {len(speeches)} speeches to {speeches_file}")
    except Exception as e:
        print(f"   ❌ Error fetching speeches: {e}")
    
    # Create metadata file
    metadata = {
        'downloaded_at': datetime.utcnow().isoformat(),
        'parliament': 44,
        'session': 1,
        'files': {
            'bills': 'bills.json',
            'politicians': 'politicians.json',
            'votes': 'votes.json',
            'debates': 'debates.json',
            'speeches': 'speeches.json'
        }
    }
    
    metadata_file = data_dir / 'metadata.json'
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n📊 Sample data saved to: {data_dir}")
    print("✅ Download complete!")


if __name__ == "__main__":
    asyncio.run(download_sample_data())
