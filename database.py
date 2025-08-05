# database.py
from tortoise.contrib.fastapi import register_tortoise

def init_db(app):
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
