import logging
import os

if not os.path.exists("logs"):
    os.mkdir("logs")

obsidian_logger = logging.getLogger("obsidian")
obsidian_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

obsidian_logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(
    filename="logs/nekona.log", mode="a", encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(obsidian_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(obsidian_formatter)

obsidian_logger.addHandler(file_handler)
obsidian_logger.addHandler(console_handler)

obsidian_logger.info("Logger initialized")
