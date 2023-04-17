import enum


class ClientCommandEnum(enum.Enum):
    """Client CLI commands"""
    SEND = 'send'
    SEND_TO = 'send_to'
    STATUS = 'status'
    MESSAGES = 'messages'
    CLOSE = 'close'

    @classmethod
    def get_cli_commands(cls) -> list[str]:
        return [command.value for command in cls]
