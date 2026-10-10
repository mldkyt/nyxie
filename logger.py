import logging
import os.path

nyxie_logger = logging.getLogger("akabot")
nyxie_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

nyxie_logger.setLevel(logging.DEBUG)

if not os.path.exists("logs"):
    os.mkdir("logs")

file_handler = logging.FileHandler(filename="logs/akabot.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(nyxie_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(nyxie_formatter)

nyxie_logger.addHandler(file_handler)
nyxie_logger.addHandler(console_handler)
