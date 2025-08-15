from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "hotel" ALTER COLUMN "hotel_review_score" TYPE DOUBLE PRECISION USING "hotel_review_score"::DOUBLE PRECISION;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "hotel" ALTER COLUMN "hotel_review_score" TYPE VARCHAR(10) USING "hotel_review_score"::VARCHAR(10);"""
