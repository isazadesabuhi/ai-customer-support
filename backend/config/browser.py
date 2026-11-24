from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import URLValidator


def frontend_origins(value, *, local_development):
    if value is None:
        return ["http://localhost:3000"] if local_development else []

    validate_url = URLValidator(schemes=["http", "https"])
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    for origin in origins:
        try:
            validate_url(origin)
            parts = urlsplit(origin)
            if (
                origin != f"{parts.scheme}://{parts.netloc}"
                or parts.username is not None
                or parts.port == 0
                or "*" in origin
                or (
                    parts.scheme == "http"
                    and (
                        not local_development
                        or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
                    )
                )
            ):
                raise ValueError
        except (ValidationError, ValueError):
            raise ImproperlyConfigured(
                "DJANGO_FRONTEND_ORIGINS must contain exact origins without paths or "
                "credentials. Use HTTPS outside local development."
            ) from None
    return origins
