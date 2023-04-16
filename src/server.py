import asyncio
import hashlib
import json
import re
from typing import Any, Optional, Callable

from src import settings
from src.models import User, Chat, Message, RequestSchema


class Server:
    def __init__(
        self,
        host: str = settings.SERVER_HOST,
        port: int = settings.SERVER_PORT,
        msg_batch_size: int = settings.MSG_BATCH_SIZE,
    ):
        """Init server"""
        self.host = host
        self.port = port
        self.clients = []
        self.connected_users: dict[str, User] = {}
        self.chats: list[Chat] = [Chat(name="main")]
        self.status_code_map: dict[int, str] = {
            200: '200 OK',
            400: '400 Bad Request',
            401: '401 Unauthorized',
            404: '404 Not Found',
        }
        self.endpoint_map = {
            "POST/connect/": self.connect,
            "POST/send/": self.send,
            "POST/send_to/": self.send,
            "GET/status/": self.status,
            "GET/messages/": self.messages,
        }
        self.endpoint_params_regex_map = {
            "GET/messages/": {
                "regex": r'/chats/([^/]+)/messages/',
                "params": ["chat_name"],
            },
        }
        # Message batch size
        self.msg_batch_size = msg_batch_size

    async def send(self, request: RequestSchema) -> str:
        """Send message to main chat."""
        # Get user token
        user_token: str = request.headers.get("token")
        # Get user data
        if user_data := self.connected_users.get(user_token):
            # Get message
            message = request.data.get("message")
            new_message: Message = Message(user=user_data, text=message)
            # Add new message in main chat
            main_chat: Chat = await self._get_main_chat()
            main_chat.messages.append(new_message)
            # Prepare response
            return await self._parse_response(200, {"message": new_message.text})
        # Return error
        return await self._parse_response(401, {'error': 'User not found'})

    async def connect(self, request: RequestSchema) -> str:
        """Connect user to chat."""
        # Get user token
        user_token: str = request.headers.get("token")
        # Check if user already connected
        if not self.connected_users.get(user_token):
            user: User = User(**request.data)
            user_token: str = await self.get_data_hash(user=user)
            self.connected_users[user_token] = user
            main_chat: Chat = await self._get_main_chat()
            main_chat.members.append(user)
        # Return user token
        return await self._parse_response(200, {"token": user_token})

    async def status(self, request: RequestSchema) -> str:
        """Get chat statuses for user."""
        # Get user token
        user_token: str = request.headers.get("token")
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
        return await self._parse_response(401, {'error': 'User not found'})

    async def messages(self, request: RequestSchema) -> str:
        """Get messages for user."""
        # Get chat name
        chat_name: str = request.params.get("chat_name")
        # Get user token
        user_token: str = request.headers.get("token")
        # Get user data
        user_data = self.connected_users.get(user_token)
        # Get chat
        chat = await self._get_specific_chat(chat_name)
        # Get messages
        if user_last_message := user_data.last_message:
            messages = [
                message
                for number, message in enumerate(chat.messages)
                if all((
                    message.created_at > user_last_message.created_at,
                    number < self.msg_batch_size,
                ))
            ]
        else:
            messages = chat.messages[:self.msg_batch_size]
        # Prepare response
        messages = [
            {
                "user": message.user.login,
                "text": message.text,
                "created_at": message.created_at,
            }
            for message in messages
        ]
        return await self._parse_response(200, {"messages": messages})

    async def handle_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        address = writer.get_extra_info('peername')
        print("======================================")
        print(f"Start serving {address}")

        # Get endpoint
        method, target_endpoint, params = await self._get_target_endpoint(reader=reader)
        if target_endpoint:
            # Get headers
            headers: dict[str, str] = await self._parse_headers(reader=reader)
            content_length: int = int(headers.get("Content-Length", 0))
            user_token: Optional[str] = headers.get("Authorization", None)
            # Check that content length is not None
            if method == "GET" or content_length:
                # Call endpoint
                body = await self._parse_request_body(reader=reader, content_length=content_length)
                request: RequestSchema = RequestSchema(
                    headers={"token": user_token},
                    data=body,
                    params=params,
                )
                response: str = await target_endpoint(request)
            else:
                # Raise bad request data
                response = await self._parse_response(400, {'error': 'Invalid request'})
        else:
            # Raise not found endpoint
            response = await self._parse_response(404, {'error': 'Endpoint not found'})
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
        srv = await asyncio.start_server(
            self.handle_request,
            host=self.host,
            port=self.port,
        )
        async with srv:
            print(f"Server started at {self.host}:{self.port}")
            await srv.serve_forever()

    async def _get_specific_chat(self, chat_name: str) -> Optional[Chat]:
        """Get specific chat."""
        chat = [chat for chat in self.chats if chat.name == chat_name]
        return chat[0] if chat else None

    async def _get_main_chat(self) -> Chat:
        """Get main chat."""
        return self.chats[0]

    async def _parse_response(self, code: int, data: dict[str, Any]) -> str:
        """Parse response data to string."""
        response = f"HTTP/1.1 {self.status_code_map.get(code)}\r\n"
        response += "Content-Type: application/json; charset=utf-8\r\n"
        response += "\r\n"
        response += json.dumps(data)
        return response

    async def _get_target_endpoint(self, reader: asyncio.StreamReader) -> tuple[str, Optional[Callable], dict]:
        """Get target endpoint from request line."""
        # Get request line
        request_line = await reader.readline()
        method, path, protocol = request_line.decode().strip().split(' ')
        print(f"{method}: {self.host}:{self.port}{path}")
        # Get endpoint key
        path_parts = path.split('/')
        endpoint_key = f"{method}/{path_parts[-2]}/"
        # Get params
        params = await self._parse_params(path=path, endpoint_key=endpoint_key) if len(path_parts) > 2 else {}
        # Return endpoint
        return method, self.endpoint_map.get(endpoint_key), params

    async def _parse_params(self, path: str, endpoint_key: str) -> dict[str, Any]:
        """Parse params from path."""
        if params_regex := self.endpoint_params_regex_map.get(endpoint_key):
            match = re.match(params_regex.get('regex', ''), path)
            return {
                param_name: match.group(number)
                for number, param_name in enumerate(params_regex.get('params'), start=1)
            }
        return {}

    @staticmethod
    async def _parse_request_body(reader: asyncio.StreamReader, content_length: int) -> dict:
        """Parse request body."""
        body = await reader.read(content_length)
        return json.loads(body.decode()) if body else {}

    @staticmethod
    async def _parse_headers(reader: asyncio.StreamReader) -> dict[str, str]:
        """Parse request headers."""
        headers: dict[str, str] = {}
        while True:
            header = await reader.readline()
            if header == b'\r\n':
                break
            key, value = header.decode().strip().split(': ')
            headers[key] = value
        return headers

    @staticmethod
    async def get_data_hash(user: User) -> str:
        """Get user data hash."""
        return hashlib.sha256(f"{user.login}{user.password}".encode()).hexdigest()


if __name__ == '__main__':
    """Run server."""
    server = Server()
    asyncio.run(server.run())
