from getpass import getpass

from app.services.passwords import hash_password


def main() -> None:
    password = getpass("Admin password: ")
    confirmation = getpass("Confirm admin password: ")
    if not password:
        raise SystemExit("Password cannot be empty.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    encoded = hash_password(password)
    print("Add this single-quoted value to your .env file:")
    print(f"ADMIN_PASSWORD_HASH='{encoded}'")


if __name__ == "__main__":
    main()
