import logging
import os

if not os.path.exists("logs"):
    os.mkdir("logs")

ai_logger = logging.getLogger("ai")
ai_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

ai_logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(
    filename="logs/nekona.log", mode="a", encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(ai_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(ai_formatter)

ai_logger.addHandler(file_handler)
ai_logger.addHandler(console_handler)

ai_logger.info("Logger initialized")
