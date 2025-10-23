import asyncio
from argparse import Namespace
from scripts.backfill_2025_sample import backfill_2025

async def run():
    args = Namespace(
        bill_limit=1,
        vote_limit=1,
        debate_limit=1,
        committee_limit=1,
        meetings_limit=1,
        parliament=None,
        session=None,
        full=True,
    )
    try:
        result = await backfill_2025(args)
        print(result)
    except Exception as exc:
        import traceback
        traceback.print_exc()

asyncio.run(run())
