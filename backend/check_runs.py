import asyncio
from app.database import async_session
from app.models.cloud_log import CloudLog
from sqlalchemy import select, func

async def check():
    async with async_session() as s:
        r = await s.execute(select(func.count(CloudLog.id)).where(CloudLog.is_processed == False))
        print(f"Unprocessed cloud_logs: {r.scalar()}")
        r2 = await s.execute(select(func.count(CloudLog.id)).where(CloudLog.is_processed == True))
        print(f"Processed cloud_logs: {r2.scalar()}")

asyncio.run(check())
