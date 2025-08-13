from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" CHAR(36) NOT NULL PRIMARY KEY,
    "first_name" VARCHAR(30) NOT NULL,
    "last_name" VARCHAR(30) NOT NULL,
    "email" VARCHAR(100) NOT NULL,
    "hashed_password" VARCHAR(100) NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "attraction" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "attraction_name" VARCHAR(100) NOT NULL,
    "attraction_description" TEXT NOT NULL,
    "attraction_price" VARCHAR(30) NOT NULL,
    "attraction_availability_date" VARCHAR(30) NOT NULL,
    "attraction_average_review" VARCHAR(10) NOT NULL,
    "attraction_total_review" VARCHAR(10) NOT NULL,
    "attraction_photo" VARCHAR(200) NOT NULL,
    "attraction_daily_timing" VARCHAR(20) NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "related_user_id" CHAR(36) NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "trips" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "preferences" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "preferred_countries" VARCHAR(100) NOT NULL,
    "preferred_activities" VARCHAR(100) NOT NULL,
    "preferred_hotels" VARCHAR(100) NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id_id" CHAR(36) NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "hotel" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "hotel_name" VARCHAR(100) NOT NULL,
    "hotel_review_score_word" VARCHAR(30) NOT NULL,
    "hotel_review_score" VARCHAR(10) NOT NULL,
    "hotel_gross_price" VARCHAR(30) NOT NULL,
    "hotel_currency" VARCHAR(3) NOT NULL,
    "hotel_check_in" VARCHAR(70) NOT NULL,
    "hotel_check_out" VARCHAR(70) NOT NULL,
    "hotel_score" TEXT NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "related_user_id" CHAR(36) NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "flight" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "departure_airport_info" VARCHAR(100) NOT NULL,
    "arrival_airport_info" VARCHAR(30) NOT NULL,
    "outbound_price" VARCHAR(10) NOT NULL,
    "outbound_currency" VARCHAR(30) NOT NULL,
    "outbound_duration_hours" VARCHAR(3) NOT NULL,
    "outbound_departure_time" VARCHAR(70) NOT NULL,
    "outbound_arrival_time" VARCHAR(70) NOT NULL,
    "outbound_cabin_class" TEXT NOT NULL,
    "outbound_flight_number" VARCHAR(70) NOT NULL,
    "outbound_carrier" TEXT NOT NULL,
    "return_price" VARCHAR(10) NOT NULL,
    "return_currency" VARCHAR(30) NOT NULL,
    "return_duration_hours" VARCHAR(3) NOT NULL,
    "return_departure_time" VARCHAR(70) NOT NULL,
    "return_arrival_time" VARCHAR(70) NOT NULL,
    "return_cabin_class" TEXT NOT NULL,
    "return_flight_number" VARCHAR(70) NOT NULL,
    "return_carrier" TEXT NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "related_user_id" CHAR(36) NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
