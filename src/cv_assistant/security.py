from cryptography.fernet import Fernet, InvalidToken

from cv_assistant.config import get_settings


def _fernet() -> Fernet:
    key = get_settings().data_encryption_key.get_secret_value().encode("ascii")
    try:
        return Fernet(key)
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("DATA_ENCRYPTION_KEY must be a valid Fernet key from Fernet.generate_key()") from exc


def encrypt_resume(text: str) -> str:
    return _fernet().encrypt(text.encode("utf-8")).decode("ascii")


def decrypt_resume(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError) as exc:
        raise ValueError("Resume ciphertext is invalid or the configured key has changed") from exc
