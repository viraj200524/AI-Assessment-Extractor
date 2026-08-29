"""Access control for the deployed demo.

Scope: this gates *cost and destruction*, not identity. Reads stay public so a reviewer can
explore the app without a signup wall; the endpoints that spend Gemini quota or delete data
require a shared key supplied out of band.

It is deliberately not a user authentication system. Real multi-tenancy would mean per-user
ownership and Supabase RLS, which is a different product than the one this repo describes.
"""

import secrets

from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, get_settings

ACCESS_KEY_HEADER = "X-Demo-Key"


def require_demo_key(
    x_demo_key: str | None = Header(default=None, alias=ACCESS_KEY_HEADER),
    settings: Settings = Depends(get_settings),
) -> None:
    """Reject a mutating request unless it carries the configured shared key.

    A no-op when DEMO_ACCESS_KEY is unset, so local development and the test suite are
    unaffected and the guard only activates where it is actually configured.
    """
    configured = settings.demo_access_key
    if configured is None:
        return

    supplied = x_demo_key or ""
    # compare_digest over equal-length byte strings; encode both sides so a non-ASCII key
    # cannot raise instead of comparing.
    if not secrets.compare_digest(supplied.encode("utf-8"), configured.get_secret_value().encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail=(
                "This action requires an access key. Open the app with the key link you were "
                "given, or enter the key in the app."
            ),
            headers={"WWW-Authenticate": f'{ACCESS_KEY_HEADER} realm="vedai-demo"'},
        )
