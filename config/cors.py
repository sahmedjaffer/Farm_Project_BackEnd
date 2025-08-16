from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
# Load .env before using os.getenv
load_dotenv() 


def init_cors(app):
    
    # Detect the environment: development or production
    ENV = os.getenv("ENV")  # Default to "development" if not set

    if ENV == "dev":
        # Allowed origins in development environment
        origins = [
             "http://localhost:5174",  # Local React dev server
             "http://127.0.0.1:5174",  # Local React dev server (alternative)
             
        ]
    else:
        # Allowed origins in production environment
        origins = [
            "https://myfrontend.com",  # Your actual production frontend domain
        ]

    # Add CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,          # Only allow requests from these origins
        allow_credentials=True,         # Allow cookies / authentication headers
        allow_methods=["*"],            # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
        allow_headers=["*"],            # Allow all custom headers
    )
    