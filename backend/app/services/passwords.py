import base64
import hashlib
import hmac
import secrets

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LENGTH = 32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=KEY_LENGTH,
    )
    return "$".join(
        (
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.urlsafe_b64encode(salt).decode(),
            base64.urlsafe_b64encode(derived).decode(),
        ),
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, n_value, r_value, p_value, salt_value, hash_value = encoded.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_value)
        expected = base64.urlsafe_b64decode(hash_value)
        actual = hashlib.scrypt(
            password.encode(),
            salt=salt,
            n=int(n_value),
            r=int(r_value),
            p=int(p_value),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)
