from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "attraction" ALTER COLUMN "attraction_daily_timing" TYPE VARCHAR(20) USING "attraction_daily_timing"::VARCHAR(20);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_availability_date" TYPE VARCHAR(30) USING "attraction_availability_date"::VARCHAR(30);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_price" TYPE VARCHAR(30) USING "attraction_price"::VARCHAR(30);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_average_review" TYPE VARCHAR(10) USING "attraction_average_review"::VARCHAR(10);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_total_review" TYPE VARCHAR(10) USING "attraction_total_review"::VARCHAR(10);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_photo" TYPE VARCHAR(200) USING "attraction_photo"::VARCHAR(200);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "attraction" ALTER COLUMN "attraction_daily_timing" TYPE VARCHAR(100) USING "attraction_daily_timing"::VARCHAR(100);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_availability_date" TYPE VARCHAR(100) USING "attraction_availability_date"::VARCHAR(100);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_price" TYPE VARCHAR(100) USING "attraction_price"::VARCHAR(100);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_average_review" TYPE VARCHAR(100) USING "attraction_average_review"::VARCHAR(100);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_total_review" TYPE VARCHAR(100) USING "attraction_total_review"::VARCHAR(100);
        ALTER TABLE "attraction" ALTER COLUMN "attraction_photo" TYPE VARCHAR(300) USING "attraction_photo"::VARCHAR(300);"""
