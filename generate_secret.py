#!/usr/bin/env python3
"""
Generate a secure secret key for MindAid
"""

import secrets

def generate_secret_key(length: int = 32) -> str:
    """Generate a cryptographically secure secret key"""
    return secrets.token_hex(length)

if __name__ == "__main__":
    print("🔐 MindAid Secret Key Generator")
    print("=" * 40)

    secret_key = generate_secret_key()
    print(f"Generated Secret Key: {secret_key}")
    print()
    print("📋 Add this to your .env file:")
    print(f"SECRET_KEY={secret_key}")
    print()
    print("⚠️  Keep this key secure and never commit it to version control!")
