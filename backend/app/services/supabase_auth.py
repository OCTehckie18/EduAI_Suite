"""Supabase Auth JWT verification for the FastAPI compatibility layer."""

import os
import time
from typing import Any, Dict

import requests
from jose import JWTError, jwk, jwt


class SupabaseAuthVerifier:
    """Verify Supabase access tokens without exposing service-role credentials."""

    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.issuer = os.getenv("SUPABASE_AUTH_ISSUER", f"{self.url}/auth/v1")
        self.audience = os.getenv("SUPABASE_AUTH_AUDIENCE", "authenticated")
        self.jwks_url = os.getenv("SUPABASE_AUTH_JWKS_URL", f"{self.issuer}/.well-known/jwks.json")
        self._keys: Dict[str, Any] = {}
        self._keys_loaded_at = 0.0

    def _load_keys(self) -> Dict[str, Any]:
        response = requests.get(self.jwks_url, timeout=5)
        response.raise_for_status()
        keys = response.json().get("keys", [])
        self._keys = {key["kid"]: jwk.construct(key) for key in keys if key.get("kid")}
        self._keys_loaded_at = time.monotonic()
        return self._keys

    def verify(self, token: str) -> Dict[str, Any]:
        if not self.url:
            raise JWTError("SUPABASE_URL is not configured")

        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise JWTError("Supabase token has no key id")

        keys = self._keys if time.monotonic() - self._keys_loaded_at < 300 else self._load_keys()
        key = keys.get(kid) or self._load_keys().get(kid)
        if key is None:
            raise JWTError("Supabase signing key not found")

        return jwt.decode(
            token,
            key,
            algorithms=[header.get("alg", "RS256")],
            audience=self.audience,
            issuer=self.issuer,
        )


supabase_auth_verifier = SupabaseAuthVerifier()
