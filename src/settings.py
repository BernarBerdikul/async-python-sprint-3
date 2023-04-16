import os

from dotenv import load_dotenv

load_dotenv()


SERVER_HOST = os.getenv("SERVER_HOST")
SERVER_PORT = int(os.getenv("SERVER_PORT"))
MSG_BATCH_SIZE = int(os.getenv("MSG_BATCH_SIZE"))