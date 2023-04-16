import asyncio
import hashlib
import json
import re
from typing import Any, Callable

from src import settings
from src.models import Chat, Message, RequestSchema, User


class Server:
    def __init__(
        self,
        host: str | None = settings.SERVER_HOST,
        port: int = settings.SERVER_PORT,
        msg_batch_size: int = settings.MSG_BATCH_SIZE,
    ):
        """Init server"""
        self.host = host
        self.port = port
        self.connected_users: dict[str, User] = {}
        self.chats: list[Chat] = [Chat(name=settings.MAIN_CHAT_NAME)]  # type: ignore
        self.status_code_map: dict[int, str] = {
            200: "200 OK",
            400: "400 Bad Request",
            401: "401 Unauthorized",
            404: "404 Not Found",
        }
        self.endpoint_map = {
            "POST/connect/": self.connect,
            "POST/send/": self.send,
            "POST/send_to/": self.send_to,
            "GET/status/": self.status,
            "GET/messages/": self.messages,
        }
        self.endpoint_params_regex_map = {
            "GET/messages/": {
                "regex": r"/chats/([^/]+)/messages/",
                "params": ["chat_name"],
            },
        }
        # Message batch size
        self.msg_batch_size = msg_batch_size

    async def send_to(self, request: RequestSchema) -> str:
        """Send message to main chat."""
        # Get user token
        user_token: str = request.headers.get("token")  # type: ignore
        # Get user data
        if sender_user := self.connected_users.get(user_token):
            users: list[User] = [
                user
                for user in self.connected_users.values()
                if user.login == request.data.get("user_login")
            ]
            if not users:
                return await self._parse_response(404, {"error": "User not found"})
            # Get receiver user
            receiver_user = users[0]
            # Add new message in main chat
            message = request.data.get("message")
            chat = await self._get_or_create_chat(sender_user, receiver_user)
            chat.messages.append(Message(user=sender_user, text=message))  # type: ignore
            # Prepare response
            return await self._parse_response(200, {"message": message})
        # Return error
        return await self._parse_response(401, {"error": "User not found"})

    async def send(self, request: RequestSchema) -> str:
        """Send message to main chat."""
        # Get user token
        user_token: str = request.headers.get("token")  # type: ignore
        # Get user data
        if sender_user := self.connected_users.get(user_token):
            # Add new message in main chat
            message = request.data.get("message")
            main_chat: Chat = await self._get_main_chat()
            main_chat.messages.append(Message(user=sender_user, text=message))  # type: ignore
            # Prepare response
            return await self._parse_response(200, {"message": message})
        # Return error
        return await self._parse_response(401, {"error": "User not found"})

    async def connect(self, request: RequestSchema) -> str:
        """Connect user to chat."""
        # Get user token
        user_token: str = request.headers.get("token")  # type: ignore
        # Check if user already connected
        if not self.connected_users.get(user_token):
            user: User = User(**request.data)
            new_user_token: str = await self.get_data_hash(user=user)
            self.connected_users[new_user_token] = user
            main_chat: Chat = await self._get_main_chat()
            main_chat.members.append(user)
            return await self._parse_response(200, {"token": new_user_token})
        # Return user token
        return await self._parse_response(200, {"token": user_token})

    async def status(self, request: RequestSchema) -> str:
        """Get chat statuses for user."""
        # Get user token
        user_token: str = request.headers.get("token")  # type: ignore
        # Get user data
        if user_data := self.connected_users.get(user_token):
            # Prepare user's chats
            response_data: dict[str, list[str]] = {}
            for chat in self.chats:
                member_logins: list[str] = [member.login for member in chat.members]
                if user_data.login in member_logins:
                    response_data[chat.name] = member_logins
            # Prepare response
            return await self._parse_response(200, response_data)
        # Return error
        return await self._parse_response(401, {"error": "User not found"})

    async def messages(self, request: RequestSchema) -> str:
        """Get messages for user."""
        # Get chat name
        chat_name: str = request.params.get("chat_name")  # type: ignore
        # Get user token
        user_token: str = request.headers.get("token")  # type: ignore
        # Get user data
        user_data = self.connected_users.get(user_token)
        # Get chat
        chat = await self._get_specific_chat(chat_name)
        if not chat:
            return await self._parse_response(404, {"error": "Chat not found"})
        # Get messages
        if user_last_message := user_data.last_chat_message_map[chat_name]:  # type: ignore
            messages = [
                message
                for number, message in enumerate(chat.messages)  # type: ignore
                if all(
                    (
                        message.created_at > user_last_message.created_at,
                        number < self.msg_batch_size,
                    )
                )
            ]
        else:
            messages = chat.messages[: self.msg_batch_size]  # type: ignore
            # Save last message
            if messages:
                user_data.last_chat_message_map[chat_name] = messages[-1]  # type: ignore
        # Prepare response
        response_data = {
            "messages": [
                {
                    "user": message.user.login,
                    "text": message.text,
                    "created_at": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for message in messages
            ]
        }
        return await self._parse_response(200, response_data)

    async def handle_request(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Handle user's request."""
        address = writer.get_extra_info("peername")
        print("======================================")
        print(f"Start serving {address}")

        # Get endpoint
        method, target_endpoint, params = await self._get_target_endpoint(reader=reader)
        if target_endpoint:
            # Get headers
            headers: dict[str, str] = await self._parse_headers(reader=reader)
            content_length: int = int(headers.get("Content-Length", 0))
            user_token: str | None = headers.get("Authorization", None)
            # Check that content length is not None
            if method == "GET" or content_length:
                # Call endpoint
                body = await self._parse_request_body(
                    reader=reader, content_length=content_length
                )
                request: RequestSchema = RequestSchema(
                    headers={"token": user_token},
                    data=body,
                    params=params,
                )
                response: str = await target_endpoint(request)
            else:
                # Raise bad request data
                response = await self._parse_response(400, {"error": "Invalid request"})
        else:
            # Raise not found endpoint
            response = await self._parse_response(404, {"error": "Endpoint not found"})
        # Send response
        print("============== RESPONSE ==============")
        print(f"Response: {response}")
        print("======================================")
        writer.write(response.encode())
        await writer.drain()
        # Close connection
        print(f"Stop serving {address}")
        print("======================================")
        writer.close()

    async def run(self):
        """Run server."""
        srv = await asyncio.start_server(
            self.handle_request,
            host=self.host,
            port=self.port,
        )
        async with srv:
            print(f"Server started at {self.host}:{self.port}")
            await srv.serve_forever()

    async def _get_specific_chat(self, chat_name: str) -> Chat | None:
        """Get specific chat."""
        chat = [chat for chat in self.chats if chat.name == chat_name]
        return chat[0] if chat else None

    async def _get_main_chat(self) -> Chat:
        """Get main chat."""
        return self.chats[0]

    async def _get_or_create_chat(self, sender_user: User, receiver_user: User) -> Chat:
        """Get or create chat."""
        members = [sender_user, receiver_user]
        chat_name: str = "+".join(
            [
                member.login
                for member in sorted(members, key=lambda member: member.login)
            ]
        )
        chats: list[Chat] = [chat for chat in self.chats if chat.name == chat_name]
        if chats:
            # Return existing chat
            return chats[0]
        # Create new chat
        new_chat = Chat(name=chat_name, members=members)
        self.chats.append(new_chat)
        # Save chat in last message map
        sender_user.last_chat_message_map[chat_name] = None
        receiver_user.last_chat_message_map[chat_name] = None
        return new_chat

    async def _parse_response(self, code: int, data: dict[str, Any]) -> str:
        """Parse response data to string."""
        response = f"HTTP/1.1 {self.status_code_map.get(code)}\r\n"
        response += "Content-Type: application/json; charset=utf-8\r\n"
        response += "\r\n"
        response += json.dumps(data)
        return response

    async def _get_target_endpoint(
        self, reader: asyncio.StreamReader
    ) -> tuple[str, Callable | None, dict]:
        """Get target endpoint from request line."""
        # Get request line
        request_line = await reader.readline()
        method, path, protocol = request_line.decode().strip().split(" ")
        print(f"{method}: {self.host}:{self.port}{path}")
        # Get endpoint key
        path_parts = path.split("/")
        endpoint_key = f"{method}/{path_parts[-2]}/"
        # Get params
        params = (
            await self._parse_params(path=path, endpoint_key=endpoint_key)
            if len(path_parts) > 2
            else {}
        )
        # Return endpoint
        return method, self.endpoint_map.get(endpoint_key), params

    async def _parse_params(self, path: str, endpoint_key: str) -> dict[str, Any]:
        """Parse params from path."""
        if params_regex := self.endpoint_params_regex_map.get(endpoint_key):
            match = re.match(params_regex.get("regex", ""), path)  # type: ignore
            return {
                param_name: match.group(number)
                for number, param_name in enumerate(params_regex.get("params"), start=1)  # type: ignore
            }
        return {}

    @staticmethod
    async def _parse_request_body(
        reader: asyncio.StreamReader, content_length: int
    ) -> dict:
        """Parse request body."""
        body = await reader.read(content_length)
        return json.loads(body.decode()) if body else {}

    @staticmethod
    async def _parse_headers(reader: asyncio.StreamReader) -> dict[str, str]:
        """Parse request headers."""
        headers: dict[str, str] = {}
        while True:
            header = await reader.readline()
            if header == b"\r\n":
                break
            key, value = header.decode().strip().split(": ")
            headers[key] = value
        return headers

    @staticmethod
    async def get_data_hash(user: User) -> str:
        """Get user data hash."""
        return hashlib.sha256(f"{user.login}{user.password}".encode()).hexdigest()


if __name__ == "__main__":
    """Run server."""
    server = Server()
    asyncio.run(server.run())
