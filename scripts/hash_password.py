#!/usr/bin/env python3
"""Generate a bcrypt hash for FINEAS_OWNER_PASSWORD_HASH.

Usage:
    python scripts/hash_password.py
    # prompts for a password and prints the hash to stdout.
"""
import getpass
import sys

from passlib.context import CryptContext


def main() -> None:
    pw = getpass.getpass("New owner password: ")
    confirm = getpass.getpass("Confirm password: ")
    if pw != confirm:
        sys.exit("Passwords do not match.")
    if len(pw) < 8:
        sys.exit("Password must be at least 8 characters.")
    ctx = CryptContext(schemes=["bcrypt"])
    print("\nPaste this into .env as FINEAS_OWNER_PASSWORD_HASH:\n")
    print(ctx.hash(pw))


if __name__ == "__main__":
    main()
