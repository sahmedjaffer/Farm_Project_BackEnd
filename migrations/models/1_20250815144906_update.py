from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "attraction" ALTER COLUMN "attraction_average_review" TYPE VARCHAR(100) USING "attraction_average_review"::VARCHAR(100);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_price" TYPE VARCHAR(100) USING "attraction_price"::VARCHAR(100);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_total_review" TYPE VARCHAR(100) USING "attraction_total_review"::VARCHAR(100);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "attraction" ALTER COLUMN "attraction_average_review" TYPE VARCHAR(20) USING "attraction_average_review"::VARCHAR(20);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_price" TYPE VARCHAR(30) USING "attraction_price"::VARCHAR(30);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_total_review" TYPE VARCHAR(20) USING "attraction_total_review"::VARCHAR(20);"""
