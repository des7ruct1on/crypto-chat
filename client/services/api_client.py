import json
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s :: %(message)s'
)
logger = logging.getLogger("SecureChat")


class ApiClient:

    def __init__(self, server_url="http://localhost:8000"):
        self.server_url = server_url
        self.http = requests.Session()
        self.request_timeout = 15

    def _send_api_request(self, http_method, api_path, **options):
        full_url = f"{self.server_url}{api_path}"
        try:
            response = self.http.request(
                method=http_method,
                url=full_url,
                timeout=self.request_timeout,
                **options
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout occurred for {http_method} {full_url}")
            raise TimeoutError(f"Server request timed out: {full_url}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection failed to {self.server_url}")
            raise ConnectionError(f"Unable to connect to server")
        except requests.exceptions.HTTPError as err:
            logger.error(
                f"HTTP Error {err.response.status_code} - "
                f"{http_method} {full_url}: {err.response.text}"
            )
            raise err
        except requests.exceptions.RequestException as err:
            logger.error(f"Request error: {http_method} {full_url} - {err}")
            raise err
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {http_method} {full_url}")
            raise ValueError("Received malformed JSON response")

    def register(self, username: str, password: str):
        payload = {"username": username, "password": password}
        return self._send_api_request(
            "post",
            "/auth/register",
            json=payload
        )

    def login(self, username: str, password: str):
        credentials = {"username": username, "password": password}
        return self._send_api_request(
            "post",
            "/auth/login",
            json=credentials
        )

    def create_chat(self, user_id, algorithm, mode, padding):
        chat_data = {
            "user_id": user_id,
            "algorithm": algorithm,
            "encryption_mode": mode,
            'padding_mode': padding
        }
        return self._send_api_request(
            "post",
            "/chat/create",
            json=chat_data
        )

    def join_chat(self, chat_id, user_id):
        join_data = {"chat_id": chat_id, "user_id": user_id}
        return self._send_api_request(
            "post",
            "/chat/join",
            json=join_data
        )

    def leave_chat(self, chat_id, user_id):
        leave_data = {"chat_id": chat_id, "user_id": user_id}
        return self._send_api_request(
            "post",
            "/chat/leave",
            json=leave_data
        )

    def close_chat(self, chat_id, user_id):
        close_data = {"chat_id": chat_id, "user_id": user_id}
        return self._send_api_request(
            "post",
            "/chat/close",
            json=close_data
        )

    def get_dh_params(self, chat_id):
        return self._send_api_request(
            "get",
            f"/key/{chat_id}/dh_params"
        )

    def store_public_key(self, chat_id, user_id, public_key):
        key_data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "public_key": public_key
        }
        return self._send_api_request(
            "post",
            "/key/public_key",
            json=key_data
        )

    def get_participant_key(self, chat_id, user_id):
        query_params = {"user_id": user_id}
        return self._send_api_request(
            "get",
            f"/key/{chat_id}/participant_key",
            params=query_params
        )

    def get_encryption_status(self, chat_id, user_id):
        status_params = {"chat_id": chat_id, "user_id": user_id}
        return self._send_api_request(
            "get",
            f"/chat/{chat_id}/{user_id}/encryption_status",
            params=status_params
        )

    def send_message(
            self,
            chat_id,
            user_id,
            encrypted_message,
            iv_nonce,
            encryption_mode,
            padding_mode,
            timestamp,
            is_file=False,
            file_name=None
    ):
        message_payload = {
            "chat_id": chat_id,
            "user_id": user_id,
            "encrypted_message": encrypted_message,
            "iv_nonce": iv_nonce,
            "encryption_mode": encryption_mode,
            "padding_mode": padding_mode,
            "is_file": is_file,
            "file_name": file_name if is_file else None,
            "timestamp": timestamp
        }
        return self._send_api_request(
            "post",
            "/message/send",
            json=message_payload
        )