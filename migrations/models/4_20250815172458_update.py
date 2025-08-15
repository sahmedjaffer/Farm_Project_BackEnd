from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "flight" ADD "outbound_legs" JSONB;
        ALTER TABLE "flight" ADD "return_legs" JSONB;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "flight" DROP COLUMN "outbound_legs";
        ALTER TABLE "flight" DROP COLUMN "return_legs";"""
