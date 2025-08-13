run:
    uvicorn main:app --reload
    # Starts the FastAPI application using Uvicorn ASGI server.
    # The `main:app` means the `app` instance inside the `main.py` file.
    # The `--reload` option enables auto-reload on code changes (useful during development).

migrate:
    aerich migrate
    # Generates new migration scripts based on the current database models and schema changes.
    # Aerich is a database migration tool for Tortoise ORM.

applymigrate:
    aerich upgrade
    # Applies the generated migration scripts to the actual database.
    # It upgrades the database schema to match the latest migrations.

create:
    aerich init-db
    # Initializes the database, creating tables as defined in the current models.
    # Usually run the first time or after resetting the database.
