"""Access control utilities for shared demo key validation."""

import secrets

from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, get_settings

ACCESS_KEY_HEADER = "X-Demo-Key"


def require_demo_key(
    x_demo_key: str | None = Header(default=None, alias=ACCESS_KEY_HEADER),
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate the incoming request header against the configured access key if enabled."""
    configured = settings.demo_access_key
    if configured is None:
        return

    supplied = x_demo_key or ""
    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(supplied.encode("utf-8"), configured.get_secret_value().encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail=(
                "This action requires an access key. Open the app with the key link you were "
                "given, or enter the key in the app."
            ),
            headers={"WWW-Authenticate": f'{ACCESS_KEY_HEADER} realm="vedai-demo"'},
        )
