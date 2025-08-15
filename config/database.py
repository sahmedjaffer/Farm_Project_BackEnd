from tortoise.contrib.fastapi import register_tortoise
from tortoise_config import TORTOISE_ORM

def init_db(app):
    register_tortoise(
        app,
        config=TORTOISE_ORM,
        generate_schemas=False,
        add_exception_handlers=True,
    )
