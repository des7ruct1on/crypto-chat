import logging
import sqlite3
from pathlib import Path

from crypto.base.modes import PaddingMode, CipherMode
from utils.constants import EncryptionAlgorithm

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("secret-chat")

class Database:
    
    def __init__(self, user_id: str, filename ="secret-chat.db"):
        self.user_id = user_id

        base_dir = Path("data")
        user_dir = base_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = user_dir / filename

        self.init_db()
        self.migrate_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys = ON;")

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id TEXT PRIMARY KEY,
            algorithm TEXT NOT NULL,
            mode TEXT NOT NULL,
            padding TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            is_creator BOOLEAN NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            chat_id TEXT,
            sender TEXT, -- user_id of sender
            timestamp TEXT,
            encrypted_message TEXT, -- base64 encoded
            decrypted_message TEXT, -- Store decrypted for display
            iv_nonce TEXT, -- base64 encoded
            encryption_mode TEXT,
            padding_mode TEXT,
            is_file BOOLEAN DEFAULT 0,
            file_name TEXT,
            file_path TEXT, -- Path where the decrypted file is stored locally
            file_bytes BLOB,
            FOREIGN KEY (chat_id) REFERENCES chats (chat_id) ON DELETE CASCADE -- Cascade delete
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            chat_id TEXT PRIMARY KEY,
            shared_key TEXT, -- base64 encoded AES key
            p TEXT,
            g TEXT,
            private_key TEXT,
            public_key TEXT,
            other_public_key TEXT,
            FOREIGN KEY (chat_id) REFERENCES chats (chat_id) ON DELETE CASCADE -- Cascade delete
        )
        ''')

        conn.commit()
        conn.close()
    
    def migrate_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("PRAGMA table_info(chats)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'mode' not in columns:
                cursor.execute("ALTER TABLE chats ADD COLUMN mode TEXT NOT NULL DEFAULT 'CBC'")
            if 'padding' not in columns:
                cursor.execute("ALTER TABLE chats ADD COLUMN padding TEXT NOT NULL DEFAULT 'PKCS7'")
                
            conn.commit()
            logger.info("Database migration completed successfully")
        except sqlite3.Error as e:
            logger.error(f"Database migration failed: {e}")
            raise
        finally:
            conn.close()

    def save_chat(self, chat_id, algorithm, mode, padding, created_at, status, is_creator):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO chats 
            (chat_id, algorithm, mode, padding, created_at, status, is_creator)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                chat_id, 
                algorithm.name if hasattr(algorithm, 'name') else str(algorithm),
                mode.name if hasattr(mode, 'name') else str(mode),
                padding.name if hasattr(padding, 'name') else str(padding),
                created_at, 
                status, 
                int(is_creator)
            ))
            conn.commit()
            logger.info(f"Saved chat {chat_id} to DB. Algorithm: {algorithm}, Mode: {mode}, Padding: {padding}")
        except sqlite3.Error as e:
            logger.error(f"Error saving chat {chat_id}: {e}")
            raise
        finally:
            conn.close()

    def update_chat_status(self, chat_id, status):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            UPDATE chats SET status = ? WHERE chat_id = ?
            ''', (status, chat_id))
            conn.commit()
            logger.info(f"Updated status for chat {chat_id} to {status}.")
        except sqlite3.Error as e:
            logger.error(f"Error updating status for chat {chat_id}: {e}")
        finally:
            conn.close()

    def save_message(self, message_id, chat_id, sender, timestamp, encrypted_message,
                       decrypted_message, iv_nonce, encryption_mode, padding_mode,
                       is_file=False, file_name=None, file_path=None, file_bytes=None):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO messages
            (message_id, chat_id, sender, timestamp, encrypted_message, decrypted_message,
             iv_nonce, encryption_mode, padding_mode, is_file, file_name, file_path, file_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (message_id, chat_id, sender, timestamp, encrypted_message, decrypted_message,
                  iv_nonce, encryption_mode, padding_mode, is_file, file_name, file_path, file_bytes))
            conn.commit()
            logger.debug(f"Saved message {message_id} for chat {chat_id}.")
        except sqlite3.Error as e:
            logger.error(f"Error saving message {message_id} for chat {chat_id}: {e}")
        finally:
            conn.close()

    def save_keys(self, chat_id, shared_key, p, g, private_key, public_key, other_public_key):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO keys
            (chat_id, shared_key, p, g, private_key, public_key, other_public_key)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                chat_id,
                shared_key,
                str(p) if p is not None else None,
                str(g) if g is not None else None,
                str(private_key) if private_key is not None else None,
                str(public_key) if public_key is not None else None,
                str(other_public_key) if other_public_key is not None else None
            ))
            conn.commit()
            logger.info(f"Saved keys for chat {chat_id}.")
        except sqlite3.Error as e:
            logger.error(f"Error saving keys for chat {chat_id}: {e}")
        finally:
            conn.close()

    def get_chats(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        chats_data = []
        try:
            cursor.execute('''
            SELECT chat_id, algorithm, mode, padding, created_at, status, is_creator FROM chats
            ''')
            chats = cursor.fetchall()
            chats_data = [
                {
                    "chat_id": chat[0],
                    "algorithm": EncryptionAlgorithm[chat[1]],
                    "mode": CipherMode[chat[2]],
                    "padding": PaddingMode[chat[3]],
                    "created_at": chat[4],
                    "status": chat[5],
                    "is_creator": bool(chat[6])
                }
                for chat in chats
            ]
        except sqlite3.Error as e:
            logger.error(f"Error getting chats: {e}")
        finally:
            conn.close()
        return chats_data

    def get_messages(self, chat_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        messages_data = []
        try:
            cursor.execute('''
            SELECT message_id, sender, timestamp, decrypted_message, is_file, file_name, file_path, file_bytes
            FROM messages
            WHERE chat_id = ?
            ORDER BY timestamp ASC
            ''', (chat_id,))
            messages = cursor.fetchall()
            messages_data = [
                {
                    "message_id": msg[0],
                    "sender": msg[1],
                    "timestamp": msg[2],
                    "text": msg[3],
                    "is_file": bool(msg[4]),
                    "file_name": msg[5],
                    "file_path": msg[6],
                    "file_bytes": bytes(msg[7]) if msg[7] else None
                }
                for msg in messages
            ]
        except sqlite3.Error as e:
            logger.error(f"Error getting messages for chat {chat_id}: {e}")
        finally:
            conn.close()
        return messages_data

    def get_chat_key(self, chat_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        key_data = None
        try:
            cursor.execute('''
            SELECT shared_key, p, g, private_key, public_key, other_public_key
            FROM keys
            WHERE chat_id = ?
            ''', (chat_id,))
            key_row = cursor.fetchone()
            if key_row:
                key_data = {
                    "shared_key": key_row[0],
                    "p": int(key_row[1]) if key_row[1] else None,
                    "g": int(key_row[2]) if key_row[2] else None,
                    "private_key": int(key_row[3]) if key_row[3] else None,
                    "public_key": int(key_row[4]) if key_row[4] else None,
                    "other_public_key": int(key_row[5]) if key_row[5] else None
                }
        except sqlite3.Error as e:
            logger.error(f"Error getting keys for chat {chat_id}: {e}")
        finally:
            conn.close()
        return key_data

    def delete_chat(self, chat_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM chats WHERE chat_id = ?', (chat_id,))
            conn.commit()
            logger.info(f"Deleted chat {chat_id} and related data from DB.")
        except sqlite3.Error as e:
            logger.error(f"Error deleting chat {chat_id}: {str(e)}")
        finally:
            conn.close()
    
    def get_chat_encryption_params(self, chat_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            SELECT algorithm, mode, padding FROM chats WHERE chat_id = ?
            ''', (chat_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "algorithm": EncryptionAlgorithm[row[0]],
                    "mode": CipherMode[row[1]],
                    "padding": PaddingMode[row[2]]
                }
            else:
                logger.warning(f"No encryption params found for chat_id {chat_id}")
                return None
        except sqlite3.Error as e:
            logger.error(f"Error fetching encryption params for chat_id {chat_id}: {e}")
            return None
        finally:
            conn.close()

    def close_db(self):
        pass
