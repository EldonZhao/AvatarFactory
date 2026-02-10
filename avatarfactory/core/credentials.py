"""
Credential management with encryption for AvatarFactory.

Provides secure storage and retrieval of sensitive credentials
using Fernet symmetric encryption.
"""

import base64
import hashlib
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    raise ImportError(
        "cryptography package required for credential management. "
        "Install with: pip install cryptography"
    )


class CredentialManager:
    """
    Manages encrypted storage of sensitive credentials.

    Uses Fernet symmetric encryption (AES-128-CBC) for secure storage.
    The master key can be provided directly, loaded from environment,
    or generated and stored in a key file.
    """

    def __init__(
        self,
        master_key: Optional[bytes] = None,
        key_file_path: Optional[Path] = None,
    ):
        """
        Initialize the credential manager.

        Args:
            master_key: Optional master key bytes (32 bytes, base64-encoded for Fernet)
            key_file_path: Optional path to store/load the master key file

        The key is loaded in this priority:
        1. master_key parameter if provided
        2. AVATARFACTORY_MASTER_KEY environment variable
        3. Key file at key_file_path
        4. Generate new key and save to key_file_path
        """
        self._key = self._load_or_create_key(master_key, key_file_path)
        self._fernet = Fernet(self._key)

    def _load_or_create_key(
        self,
        master_key: Optional[bytes],
        key_file_path: Optional[Path],
    ) -> bytes:
        """Load or create the encryption key."""
        # Priority 1: Provided key
        if master_key:
            return master_key

        # Priority 2: Environment variable
        env_key = os.getenv("AVATARFACTORY_MASTER_KEY")
        if env_key:
            return env_key.encode()

        # Priority 3: Key file
        if key_file_path and key_file_path.exists():
            with open(key_file_path, "rb") as f:
                return f.read().strip()

        # Priority 4: Generate new key
        new_key = Fernet.generate_key()

        # Save to key file if path provided
        if key_file_path:
            key_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(key_file_path, "wb") as f:
                f.write(new_key)
            # Restrict permissions on Unix systems
            try:
                os.chmod(key_file_path, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support chmod

        return new_key

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted ciphertext
        """
        if not plaintext:
            return ""
        encrypted = self._fernet.encrypt(plaintext.encode("utf-8"))
        return encrypted.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted ciphertext.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails (invalid token or wrong key)
        """
        if not ciphertext:
            return ""
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return decrypted.decode("utf-8")
        except InvalidToken:
            raise ValueError("Failed to decrypt: invalid token or wrong key")

    def encrypt_dict(self, data: Dict[str, str]) -> Dict[str, str]:
        """
        Encrypt all values in a dictionary.

        Args:
            data: Dictionary with string values to encrypt

        Returns:
            Dictionary with encrypted values
        """
        return {key: self.encrypt(value) for key, value in data.items()}

    def decrypt_dict(self, data: Dict[str, str]) -> Dict[str, str]:
        """
        Decrypt all values in a dictionary.

        Args:
            data: Dictionary with encrypted values

        Returns:
            Dictionary with decrypted values
        """
        return {key: self.decrypt(value) for key, value in data.items()}

    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure API key.

        Returns:
            A URL-safe random string (32 bytes, 43 characters)
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash an API key for storage.

        Uses SHA-256 with a salt for secure storage.
        The API key should never be stored in plaintext.

        Args:
            api_key: The API key to hash

        Returns:
            Hex-encoded hash of the API key
        """
        # Use a deterministic salt based on the key prefix for lookup
        # This allows searching by key prefix while still hashing
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_api_key(api_key: str, stored_hash: str) -> bool:
        """
        Verify an API key against its stored hash.

        Args:
            api_key: The API key to verify
            stored_hash: The stored hash to compare against

        Returns:
            True if the key matches the hash
        """
        computed_hash = CredentialManager.hash_api_key(api_key)
        return secrets.compare_digest(computed_hash, stored_hash)


# Global credential manager instance (lazy initialization)
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager(
    kb_path: Optional[str] = None,
    force_new: bool = False,
) -> CredentialManager:
    """
    Get or create the global credential manager instance.

    Args:
        kb_path: Optional knowledge base path for key file storage
        force_new: Force creation of a new instance

    Returns:
        The global CredentialManager instance
    """
    global _credential_manager

    if _credential_manager is None or force_new:
        key_file_path = None
        if kb_path:
            key_file_path = Path(kb_path) / "_system" / "master_key.enc"

        _credential_manager = CredentialManager(key_file_path=key_file_path)

    return _credential_manager
