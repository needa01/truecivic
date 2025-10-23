"""
Generate mock data for frontend development.

Creates realistic sample data based on Canadian parliamentary structure.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import random


def generate_mock_data():
    """Generate comprehensive mock data."""
    
    data_dir = Path(__file__).parent.parent / '.data'
    data_dir.mkdir(exist_ok=True)
    
    print("🎭 Generating mock data for frontend development...\n")
    
    # Parties
    parties = [
        {"id": 1, "name_en": "Liberal", "abbreviation": "LPC", "color": "#D71920"},
        {"id": 2, "name_en": "Conservative", "abbreviation": "CPC", "color": "#1A4782"},
        {"id": 3, "name_en": "NDP", "abbreviation": "NDP", "color": "#F37021"},
        {"id": 4, "name_en": "Bloc Québécois", "abbreviation": "BQ", "color": "#02819E"},
        {"id": 5, "name_en": "Green", "abbreviation": "GPC", "color": "#3D9B35"},
    ]
    
    # Generate Politicians
    print("👥 Generating politicians...")
    first_names = ["Sarah", "Michael", "Emma", "James", "Olivia", "William", "Ava", "Benjamin", "Sophie", "Daniel"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    
    politicians = []
    for i in range(100):
        party = random.choice(parties)
        politicians.append({
            "id": i + 1,
            "jurisdiction": "ca-federal",
            "politician_id": f"mp-{i+1}",
            "name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "given_name": random.choice(first_names),
            "family_name": random.choice(last_names),
            "current_party": party["name_en"],
            "current_riding": f"Riding-{i+1}",
            "gender": random.choice(["M", "F"]),
            "photo_url": f"https://i.pravatar.cc/150?img={i+1}",
            "created_at": (datetime.now() - timedelta(days=random.randint(100, 1000))).isoformat(),
            "updated_at": datetime.now().isoformat()
        })
    
    politicians_file = data_dir / 'politicians.json'
    with open(politicians_file, 'w') as f:
        json.dump(politicians, f, indent=2)
    print(f"   ✅ Generated {len(politicians)} politicians")
    
    # Generate Bills
    print("\n📄 Generating bills...")
    bill_types = ["C", "S"]
    bill_statuses = ["1st reading", "2nd reading", "Committee", "3rd reading", "Royal Assent"]
    
    bills = []
    for i in range(50):
        bill_type = random.choice(bill_types)
        status = random.choice(bill_statuses)
        bills.append({
            "id": i + 1,
            "jurisdiction": "ca-federal",
            "parliament": 44,
            "session": 1,
            "number": f"{bill_type}-{i+1}",
            "bill_type": "Government Bill" if bill_type == "C" else "Senate Bill",
            "title_en": f"An Act respecting {random.choice(['healthcare', 'education', 'environment', 'justice', 'economic development'])}",
            "title_fr": f"Loi concernant {random.choice(['santé', 'éducation', 'environnement', 'justice', 'développement économique'])}",
            "status_en": status,
            "introduced_date": (datetime.now() - timedelta(days=random.randint(30, 300))).isoformat(),
            "sponsor_politician_id": random.randint(1, 100),
            "created_at": (datetime.now() - timedelta(days=random.randint(50, 350))).isoformat(),
            "updated_at": datetime.now().isoformat()
        })
    
    bills_file = data_dir / 'bills.json'
    with open(bills_file, 'w') as f:
        json.dump(bills, f, indent=2)
    print(f"   ✅ Generated {len(bills)} bills")
    
    # Generate Votes
    print("\n🗳️  Generating votes...")
    votes = []
    for i in range(30):
        yeas = random.randint(100, 200)
        nays = random.randint(80, 150)
        result = "Passed" if yeas > nays else "Defeated"
        
        votes.append({
            "id": i + 1,
            "jurisdiction": "ca-federal",
            "vote_id": f"44-1-{i+1}",
            "parliament": 44,
            "session": 1,
            "number": i + 1,
            "bill_id": random.randint(1, 50),
            "vote_date": (datetime.now() - timedelta(days=random.randint(10, 200))).isoformat(),
            "result": result,
            "yea_count": yeas,
            "nay_count": nays,
            "paired_count": random.randint(0, 5),
            "description": f"Vote on Bill C-{random.randint(1, 50)}",
            "created_at": (datetime.now() - timedelta(days=random.randint(20, 210))).isoformat(),
            "updated_at": datetime.now().isoformat()
        })
    
    votes_file = data_dir / 'votes.json'
    with open(votes_file, 'w') as f:
        json.dump(votes, f, indent=2)
    print(f"   ✅ Generated {len(votes)} votes")
    
    # Generate Debates
    print("\n💬 Generating debates...")
    debates = []
    for i in range(20):
        debates.append({
            "id": i + 1,
            "jurisdiction": "ca-federal",
            "hansard_id": f"hansard-{i+1}",
            "parliament": 44,
            "session": 1,
            "sitting_date": (datetime.now() - timedelta(days=random.randint(5, 150))).isoformat(),
            "chamber": random.choice(["Commons", "Senate"]),
            "created_at": (datetime.now() - timedelta(days=random.randint(10, 160))).isoformat(),
            "updated_at": datetime.now().isoformat()
        })
    
    debates_file = data_dir / 'debates.json'
    with open(debates_file, 'w') as f:
        json.dump(debates, f, indent=2)
    print(f"   ✅ Generated {len(debates)} debates")
    
    # Generate Speeches
    print("\n🗣️  Generating speeches...")
    speech_topics = [
        "climate change legislation",
        "healthcare funding",
        "education reform",
        "economic policy",
        "immigration reform"
    ]
    
    speeches = []
    for i in range(100):
        speeches.append({
            "id": i + 1,
            "debate_id": random.randint(1, 20),
            "politician_id": random.randint(1, 100),
            "sequence": i % 10 + 1,
            "speaker_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "speaker_role": random.choice(["Member", "Minister", "Leader"]),
            "text_content": f"Speech regarding {random.choice(speech_topics)}. Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "language": random.choice(["en", "fr"]),
            "created_at": (datetime.now() - timedelta(days=random.randint(1, 140))).isoformat(),
            "updated_at": datetime.now().isoformat()
        })
    
    speeches_file = data_dir / 'speeches.json'
    with open(speeches_file, 'w') as f:
        json.dump(speeches, f, indent=2)
    print(f"   ✅ Generated {len(speeches)} speeches")
    
    # Generate metadata
    metadata = {
        'generated_at': datetime.now().isoformat(),
        'type': 'mock_data',
        'parliament': 44,
        'session': 1,
        'counts': {
            'politicians': len(politicians),
            'bills': len(bills),
            'votes': len(votes),
            'debates': len(debates),
            'speeches': len(speeches)
        }
    }
    
    metadata_file = data_dir / 'metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n📊 Mock data saved to: {data_dir}")
    print("✅ Generation complete!")


if __name__ == "__main__":
    generate_mock_data()
