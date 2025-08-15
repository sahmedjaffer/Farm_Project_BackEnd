from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "attraction" ALTER COLUMN "attraction_daily_timing" TYPE VARCHAR(40) USING "attraction_daily_timing"::VARCHAR(40);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "attraction" ALTER COLUMN "attraction_daily_timing" TYPE VARCHAR(20) USING "attraction_daily_timing"::VARCHAR(20);"""
