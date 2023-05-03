import sqlite3
from cryptography.fernet import Fernet

class ApiKeysDatabaseService:
    def __init__(self, encryption_key: str, db_name: str = "api_keys.db"):
        self._db_name = db_name
        self._init_database()
        self._fernet = Fernet(encryption_key)

    def _init_database(self):
        connection = sqlite3.connect(self._db_name)
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                api_key TEXT
            )
            """
        )

        connection.commit()
        connection.close()

    def get_api_key(self, user_id: int) -> str:
        connection = sqlite3.connect(self._db_name)
        cursor = connection.cursor()

        cursor.execute(f"SELECT api_key FROM users WHERE user_id={user_id}")
        encrypted_api_key = cursor.fetchone()

        connection.close()

        if encrypted_api_key:
            decrypted_api_key = self._fernet.decrypt(encrypted_api_key[0].encode()).decode()
            return decrypted_api_key
        else:
            return None

    def store_api_key(self, user_id, api_key: str):
        encrypted_api_key = self._fernet.encrypt(api_key.encode()).decode()

        connection = sqlite3.connect(self._db_name)
        cursor = connection.cursor()

        cursor.execute(
            "INSERT OR REPLACE INTO users (user_id, api_key) VALUES (?, ?)",
            (user_id, encrypted_api_key)
        )

        connection.commit()
        connection.close()
