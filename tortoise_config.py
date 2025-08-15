TORTOISE_ORM = {
 "connections": {
    "default": {
        "engine": "tortoise.backends.asyncpg",
        "credentials": {
            "host": "ep-old-snow-ae85hwtu-pooler.c-2.us-east-2.aws.neon.tech",
            "port": 5432,
            "user": "neondb_owner",
            "password": "npg_iv67cfugejOQ",
            "database": "neondb",
            "ssl": True,
            "server_settings": {"channel_binding": "require"},
        },
    }
},
    "apps": {
        "models": {
            "models": [
                "models.attraction",
                "models.user",
                "models.trips",
                "models.preferences",
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
