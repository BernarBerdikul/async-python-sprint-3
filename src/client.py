import asyncio
import logging
from typing import Any

from aiohttp import ClientSession

from src import settings

logger = logging.getLogger(__name__)


class Client:
    """Client for chat server."""

    def __init__(
        self,
        user_data: dict[str, Any],
        server_host: str | None = settings.SERVER_HOST,
        server_port: int = settings.SERVER_PORT,
    ):
        """Init client"""
        self.server_host = server_host
        self.server_port = server_port
        self.server_path = f"http://{self.server_host}:{self.server_port}"  # noqa
        self.is_session_active = False
        # User data
        self.user_token = None
        self.user_data = user_data

    @property
    def headers(self) -> dict[str, Any]:
        """Get headers for request."""
        if self.user_token:
            return {
                "Authorization": self.user_token,
            }
        return {}

    async def send(self, message: str) -> None:
        """Send message to main chat."""
        endpoint = f"{self.server_path}/send/"
        try:
            async with ClientSession() as session:
                data = {
                    "message": message,
                }
                async with session.post(
                    url=endpoint,
                    json=data,
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    logger.info(f"Request [{response.status}]: {data}")
        except Exception as e:
            logger.error(e)

    async def send_to(self, login: str, message: str) -> None:
        """Send message to specific user."""
        endpoint = f"{self.server_path}/send_to/"
        try:
            async with ClientSession() as session:
                data = {
                    "user_login": login,
                    "message": message,
                }
                async with session.post(
                    url=endpoint,
                    json=data,
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    logger.info(f"Request [{response.status}]: {data}")
        except Exception as e:
            logger.error(e)

    async def status(self) -> None:
        """Get chat status."""
        endpoint = f"{self.server_path}/status/"
        try:
            async with ClientSession() as session:
                async with session.get(
                    url=endpoint,
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    logger.info(f"Request [{response.status}]: {data}")
        except Exception as e:
            logger.error(e)

    async def messages(self, chat_name: str) -> None:
        """Get messages from chat."""
        endpoint = f"{self.server_path}/chats/{chat_name}/messages/"
        try:
            async with ClientSession() as session:
                async with session.get(
                    url=endpoint,
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    logger.info(f"Request [{response.status}]: {data}")
        except Exception as e:
            logger.error(e)

    async def connect(self) -> None:
        """Connect to server"""
        endpoint = f"{self.server_path}/connect/"
        self.is_session_active = True
        logger.info("Connecting to server...")
        try:
            async with ClientSession() as session:
                async with session.post(
                    url=endpoint,
                    json=self.user_data,
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    logger.info(f"Request [{response.status}]: {data}")
                    # Save token
                    self.user_token = data.get("token")
        except Exception as e:
            self.is_session_active = False
            logger.error(e)
        logger.info("Connected to server")

    async def command_listener(self) -> None:
        """Listen for user commands"""
        logger.info(
            "Listening for CLI commands... (send, send_to, status, messages, close)"
        )
        while self.is_session_active:
            try:
                command = input("Enter command: ")
                if command == "send":
                    # Endpoint: /send/
                    message = input("Enter message: ")
                    await self.send(message=message)
                if command == "send_to":
                    # Endpoint: /send_to/
                    login = input("Enter login: ")
                    message = input("Enter message: ")
                    await self.send_to(login=login, message=message)
                elif command == "status":
                    # Endpoint: /status/
                    await self.status()
                elif command == "messages":
                    # Endpoint: /chats/{chat_name}/messages/
                    chat_name = input("Enter chat's name: ")
                    await self.messages(chat_name=chat_name)
                elif command == "close":
                    self.is_session_active = False
            except Exception as e:
                logger.error(e)
        logger.info("Stopped listening for CLI commands...")

    async def run(self):
        """Run client"""
        await self.connect()
        await asyncio.gather(self.command_listener())


if __name__ == "__main__":
    """Run client."""
    client = Client(
        user_data={
            "login": "user_1",
            "password": "123456",
        },
    )
    asyncio.run(client.run())
