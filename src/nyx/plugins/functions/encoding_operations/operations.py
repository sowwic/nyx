"""Hashing and text encoding functions."""

import base64
import hashlib
import hmac
import html
import pathlib
import urllib.parse


def md5(text: str) -> str:
    """Get the MD5 hash of a text as hex. Fine for checksums, not for security.

    Args:
        text: Text to use.
    """
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def sha1(text: str) -> str:
    """Get the SHA-1 hash of a text as hex.

    Args:
        text: Text to use.
    """
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def sha256(text: str) -> str:
    """Get the SHA-256 hash of a text as hex.

    Args:
        text: Text to use.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha512(text: str) -> str:
    """Get the SHA-512 hash of a text as hex.

    Args:
        text: Text to use.
    """
    return hashlib.sha512(text.encode("utf-8")).hexdigest()


def hmac_sha256(text: str, key: str) -> str:
    """Get the HMAC-SHA256 of a text with a secret key as hex.

    Args:
        text: Text to use.
        key: Secret key.
    """
    return hmac.new(key.encode("utf-8"), text.encode("utf-8"), "sha256").hexdigest()


def hash_file(path: str, algorithm: str = "sha256") -> str:
    """Get the hash of the content of a file as hex, for example "sha256" or "md5".

    Args:
        path: File to hash.
        algorithm: Hash name, like sha256 or md5.
    """
    digest = hashlib.new(algorithm)
    with pathlib.Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def base64_encode(text: str) -> str:
    """Encode a text as base64.

    Args:
        text: Text to use.
    """
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def base64_decode(text: str) -> str:
    """Decode base64 to a text.

    Args:
        text: Base64 text.
    """
    return base64.b64decode(text).decode("utf-8")


def hex_encode(text: str) -> str:
    """Write the bytes of a text as hex.

    Args:
        text: Text to use.
    """
    return text.encode("utf-8").hex()


def hex_decode(text: str) -> str:
    """Read a text written as hex.

    Args:
        text: Text written as hex.
    """
    return bytes.fromhex(text).decode("utf-8")


def url_encode(text: str) -> str:
    """Escape a text so it can be part of a URL.

    Args:
        text: Text to use.
    """
    return urllib.parse.quote(text, safe="")


def url_decode(text: str) -> str:
    """Undo the escaping of a URL part.

    Args:
        text: Escaped text.
    """
    return urllib.parse.unquote(text)


def html_escape(text: str) -> str:
    """Replace <, >, & and quotes with HTML entities.

    Args:
        text: Text to use.
    """
    return html.escape(text)


def html_unescape(text: str) -> str:
    """Replace HTML entities with their characters.

    Args:
        text: Text with HTML entities.
    """
    return html.unescape(text)
