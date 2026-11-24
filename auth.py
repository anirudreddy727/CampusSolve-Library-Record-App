"""Password authentication and in-memory sessions for the local web app."""
import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path


class AuthError(ValueError):
    """Authentication or account setup was rejected."""


class AuthManager:
    ITERATIONS = 210_000

    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "auth_users.json"
        self.users = self._load()
        self.sessions = {}

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError):
            try:
                self.path.replace(self.path.with_name("auth_users.corrupt.json"))
            except OSError:
                pass
            return []

    def _save(self):
        temp = self.path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(self.users, indent=2), encoding="utf-8")
        os.replace(temp, self.path)

    @property
    def needs_setup(self):
        return not any(user.get("role") == "administrator" for user in self.users)

    @staticmethod
    def _validate_password(password):
        if not isinstance(password, str) or len(password) < 8 or len(password) > 200:
            raise AuthError("Password must be between 8 and 200 characters.")

    def _add_user(self, username, password, role, member_id=None):
        self._validate_password(password)
        salt = secrets.token_bytes(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.ITERATIONS)
        user = {"username": username, "role": role, "member_id": member_id,
                "salt": salt.hex(), "password_hash": hashed.hex()}
        self.users.append(user)
        self._save()
        return user

    def setup_admin(self, username, password):
        username = str(username).strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
            raise AuthError("Admin username must be 3–32 letters, numbers, dots, dashes, or underscores.")
        if not self.needs_setup:
            raise AuthError("An administrator account is already configured.")
        return self._add_user(username, password, "administrator")

    def register_member(self, member_id, email, password, members):
        member_id = str(member_id).strip().upper()
        email = str(email).strip().casefold()
        member = next((m for m in members if m.member_id.casefold() == member_id.casefold() and m.email.casefold() == email), None)
        if not member:
            raise AuthError("Member ID and email do not match a registered library member.")
        if any(u.get("member_id") == member.member_id for u in self.users):
            raise AuthError("This member already has a login account.")
        return self._add_user(member.member_id, password, "member", member.member_id)

    def login(self, username, password):
        user = next((u for u in self.users if u.get("username", "").casefold() == str(username).strip().casefold()), None)
        if not user:
            raise AuthError("Username or password is incorrect.")
        try:
            salt = bytes.fromhex(user["salt"])
            expected = bytes.fromhex(user["password_hash"])
            actual = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"), salt, self.ITERATIONS)
        except (KeyError, ValueError, TypeError):
            raise AuthError("Username or password is incorrect.")
        if not hmac.compare_digest(actual, expected):
            raise AuthError("Username or password is incorrect.")
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {"username": user["username"], "role": user["role"], "member_id": user.get("member_id")}
        return token, self.sessions[token]

    def get_session(self, token):
        return self.sessions.get(token)

    def logout(self, token):
        if token:
            self.sessions.pop(token, None)
