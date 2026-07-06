import logging
import os

if not os.path.exists("logs"):
    os.mkdir("logs")

lunamon_logger = logging.getLogger("Lunamon")
lunamon_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

lunamon_logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(
    filename="logs/nekona.log", mode="a", encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(lunamon_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(lunamon_formatter)

lunamon_logger.addHandler(file_handler)
lunamon_logger.addHandler(console_handler)

lunamon_logger.info("Logger initialized")
