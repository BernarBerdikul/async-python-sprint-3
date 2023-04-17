import asyncio
import logging
from typing import Any

from aiohttp import ClientSession
from aiohttp.client_exceptions import ServerTimeoutError, ClientConnectorError

from src.settings import settings
from src.enums import ClientCommandEnum

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
        except (ServerTimeoutError, ClientConnectorError) as e:
            logger.exception(e)

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
        except (ServerTimeoutError, ClientConnectorError) as e:
            logger.exception(e)

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
        except (ServerTimeoutError, ClientConnectorError) as e:
            logger.exception(e)

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
        except (ServerTimeoutError, ClientConnectorError) as e:
            logger.exception(e)

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
        except (ServerTimeoutError, ClientConnectorError) as e:
            self.is_session_active = False
            logger.exception(e)
        logger.info("Connected to server")

    async def command_listener(self) -> None:
        """Listen for user commands"""
        allowed_commands = ", ".join(ClientCommandEnum.get_cli_commands())
        logger.info(f"Listening for CLI commands... ({allowed_commands})")
        while self.is_session_active:
            command = input("Enter command: ")
            if command == ClientCommandEnum.SEND.value:
                # Endpoint: /send/
                message = input("Enter message: ")
                await self.send(message=message)
            if command == ClientCommandEnum.SEND_TO.value:
                # Endpoint: /send_to/
                login = input("Enter login: ")
                message = input("Enter message: ")
                await self.send_to(login=login, message=message)
            elif command == ClientCommandEnum.STATUS.value:
                # Endpoint: /status/
                await self.status()
            elif command == ClientCommandEnum.MESSAGES.value:
                # Endpoint: /chats/{chat_name}/messages/
                chat_name = input("Enter chat's name: ")
                await self.messages(chat_name=chat_name)
            elif command == ClientCommandEnum.CLOSE.value:
                self.is_session_active = False
        logger.info("Stopped listening for CLI commands...")

    async def run(self):
        """Run client"""
        await self.connect()
        # listen CLI commands
        await asyncio.gather(self.command_listener())


if __name__ == "__main__":
    """Run client."""
    login = input("Enter user's login: ")
    password = input("Enter user's password: ")
    client = Client(
        user_data={
            "login": login,
            "password": password,
        },
    )
    asyncio.run(client.run())
