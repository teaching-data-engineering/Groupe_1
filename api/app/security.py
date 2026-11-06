import json
import secrets
from pathlib import Path
from typing import Annotated

from fastapi import Header, HTTPException

# Le token reste dans credentials/, ignoré par git : il ne doit jamais être écrit dans le code
API_TOKEN = json.loads(Path("credentials/api_token.json").read_text(encoding="utf-8"))["token"]
if not API_TOKEN:
    raise ValueError("Le token de credentials/api_token.json est vide : l'API ne démarre pas sans token.")


def verify_token(x_token: Annotated[str | None, Header()] = None, token: str | None = None):
    """Refuse la requête (403) si le token, dans l'en-tête X-Token ou dans l'URL, est absent ou incorrect."""
    received_token = x_token or token
    if received_token is None or not secrets.compare_digest(received_token.encode(), API_TOKEN.encode()):
        raise HTTPException(status_code=403, detail="Token absent ou invalide")
