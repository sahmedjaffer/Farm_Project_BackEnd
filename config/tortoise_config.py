TORTOISE_ORM = {
    "connections": {
        "default": "sqlite://database.sqlite3",
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
    }
}
