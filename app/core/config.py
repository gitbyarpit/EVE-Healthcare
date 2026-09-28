import os
from datetime import timedelta


class Settings:
    """Central config, read from environment variables (see .env.example)."""

    PROJECT_NAME: str = "EVE Diagnostics Booking API"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://eve:eve@localhost:5432/eve_bookings",
    )

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-prod")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE: timedelta = timedelta(
        minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    )

    # Probability that the simulated payment succeeds (0-1)
    SIMULATED_PAYMENT_SUCCESS_RATE: float = float(
        os.getenv("SIMULATED_PAYMENT_SUCCESS_RATE", "0.8")
    )


settings = Settings()
