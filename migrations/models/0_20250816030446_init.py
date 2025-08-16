from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID NOT NULL PRIMARY KEY,
    "first_name" VARCHAR(30) NOT NULL,
    "last_name" VARCHAR(30) NOT NULL,
    "email" VARCHAR(100) NOT NULL,
    "password" VARCHAR(100) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "attraction" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "attraction_name" VARCHAR(100) NOT NULL,
    "attraction_description" TEXT NOT NULL,
    "attraction_price" VARCHAR(30) NOT NULL,
    "attraction_availability_date" VARCHAR(30) NOT NULL,
    "attraction_average_review" VARCHAR(10) NOT NULL,
    "attraction_total_review" VARCHAR(10) NOT NULL,
    "attraction_photo" VARCHAR(200) NOT NULL,
    "attraction_daily_timing" VARCHAR(40) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "related_user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "hotel" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "hotel_name" VARCHAR(100) NOT NULL,
    "hotel_review_score_word" VARCHAR(30) NOT NULL,
    "hotel_review_score" DOUBLE PRECISION NOT NULL,
    "hotel_gross_price" VARCHAR(30) NOT NULL,
    "hotel_currency" VARCHAR(3) NOT NULL,
    "hotel_check_in" VARCHAR(70) NOT NULL,
    "hotel_check_out" VARCHAR(70) NOT NULL,
    "hotel_photo_url" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "related_user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "flight" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "departure_airport_info" VARCHAR(100) NOT NULL,
    "arrival_airport_info" VARCHAR(100) NOT NULL,
    "outbound_price" VARCHAR(10) NOT NULL,
    "outbound_currency" VARCHAR(4) NOT NULL,
    "outbound_duration_hours" VARCHAR(25) NOT NULL,
    "outbound_departure_time" VARCHAR(25) NOT NULL,
    "outbound_arrival_time" VARCHAR(25) NOT NULL,
    "outbound_cabin_class" VARCHAR(10) NOT NULL,
    "outbound_flight_number" VARCHAR(10) NOT NULL,
    "outbound_carrier" VARCHAR(30) NOT NULL,
    "outbound_legs" JSONB,
    "return_price" VARCHAR(10) NOT NULL,
    "return_currency" VARCHAR(4) NOT NULL,
    "return_duration_hours" VARCHAR(25) NOT NULL,
    "return_departure_time" VARCHAR(25) NOT NULL,
    "return_arrival_time" VARCHAR(25) NOT NULL,
    "return_cabin_class" VARCHAR(10) NOT NULL,
    "return_flight_number" VARCHAR(10) NOT NULL,
    "return_carrier" VARCHAR(30) NOT NULL,
    "return_legs" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "related_user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
