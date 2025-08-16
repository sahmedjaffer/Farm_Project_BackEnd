import os
from dotenv import load_dotenv

# Load environment variables from .env file before accessing them
load_dotenv() 

TORTOISE_ORM = {
 "connections": {
    "default": {
        "engine": os.getenv("NEON_ENGINE"),
        "credentials": {
            "host": os.getenv("NEON_HOST"),
            "port": int(os.getenv("NEON_PORT")),
            "user": os.getenv("NEON_USER"),
            "password": os.getenv("NEON_PASSWORD"),
            "database": os.getenv("NEON_DATABASE"),
            "ssl": bool(os.getenv("NEON_SSL")),
            "server_settings": {"channel_binding": "require"},
        },
    }
},
    "apps": {
        "models": {
            "models": [
                "models.attraction",
                "models.user",
                "models.hotel",
                "models.flight",
                "aerich.models",
            ],
            "default_connection": "default",
        }
    },
    # Pass server_settings as a dict, not in the URL
    "use_tz": True,
    "timezone": "UTC",
}
