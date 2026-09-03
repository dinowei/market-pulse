from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
_DUMMY_HASH = _HASHER.hash("market-pulse-dummy-password-123")


def hash_password(password: str) -> str:
    return _HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _HASHER.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False


def verify_dummy(password: str) -> None:
    verify_password(password, _DUMMY_HASH)
