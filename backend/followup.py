import asyncio

async def start_followup_scheduler():
    while True:
        await asyncio.sleep(600)
