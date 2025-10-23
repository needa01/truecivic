import asyncio
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

# Load environment variables before importing application modules so settings pick them up
target_env = (os.getenv("DEBUG_ENV") or "local").lower()

env_priority = {
    "production": [ROOT_DIR / ".env.production", ROOT_DIR / ".env.local", ROOT_DIR / ".env"],
    "prod": [ROOT_DIR / ".env.production", ROOT_DIR / ".env.local", ROOT_DIR / ".env"],
    "local": [ROOT_DIR / ".env.local", ROOT_DIR / ".env", ROOT_DIR / ".env.production"],
}

env_files = env_priority.get(target_env, env_priority["local"])

for candidate in env_files:
    if candidate.exists():
        load_dotenv(candidate, override=True)
        break
else:
    load_dotenv(override=True)

from src.adapters.openparliament_debates import OpenParliamentDebatesAdapter
from src.config import settings
from src.db.session import async_session_factory
from src.db.repositories.debate_repository import DebateRepository
from src.db.repositories.speech_repository import SpeechRepository


async def main():
    print('Using DB connection:', settings.db.connection_string)
    adapter = OpenParliamentDebatesAdapter()
    debates_resp = await adapter.fetch(limit=1, parliament=45, session=1)
    print('debate fetch errors:', debates_resp.errors)
    debates = debates_resp.data or []
    if not debates:
        print('No debates returned')
        return

    debate = debates[0]
    debate_path = debate.get('url')

    speeches_resp = await adapter.fetch_speeches_for_debate(
        debate_id=debate_path,
        speeches_url=debate.get('speeches_url'),
        limit=500,
    )
    print('speech fetch errors:', speeches_resp.errors)
    speeches = speeches_resp.data or []
    print('speeches fetched:', len(speeches))

    async with async_session_factory() as session:
        debate_repo = DebateRepository(session)
        speech_repo = SpeechRepository(session)

        mapping = await debate_repo.map_document_urls([debate_path])
        debate_model = mapping.get(debate_path)
        if not debate_model:
            print('No debate model for path')
            return

        payloads = []
        for idx, speech in enumerate(speeches[:50], start=1):
            sequence = speech.get('sequence')
            try:
                sequence = int(sequence) if sequence is not None else idx
            except (ValueError, TypeError):
                sequence = idx

            language = speech.get('language') or (
                'fr' if speech.get('text_content_fr') and not speech.get('text_content_en') else 'en'
            )

            text_content = (
                speech.get('text_content_en')
                or speech.get('text_content')
                or speech.get('text_content_fr')
                or ''
            )

            payloads.append(
                {
                    'debate_id': debate_model.id,
                    'speaker_name': speech.get('speaker_name') or 'Unknown speaker',
                    'sequence': sequence,
                    'language': language,
                    'text_content': text_content,
                    'timestamp_start': speech.get('timestamp_start'),
                    'timestamp_end': speech.get('timestamp_end'),
                    'politician_id': None,
                }
            )

        try:
            await speech_repo.upsert_many(payloads)
            await session.commit()
            print('Subset upsert succeeded')
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            print('Subset upsert failed:', type(exc), exc)


if __name__ == '__main__':
    asyncio.run(main())
