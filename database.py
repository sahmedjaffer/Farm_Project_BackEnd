# database.py
from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI

def init_db(app: FastAPI):
    register_tortoise(
        app,
        db_url="sqlite://database.sqlite3",
        modules={
            "models": [
                # "models.models",
                "models.user",
                "models.trips",
                "models.preferences"
            ]
        },
        generate_schemas=True,
        add_exception_handlers=True,
    )
