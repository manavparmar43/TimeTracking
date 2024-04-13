import logging
import logging.config
import os
from datetime import date

if not os.path.exists("logs"):
    os.makedirs("logs")

log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logging.conf")
logging.config.fileConfig(
    log_file_path,
    disable_existing_loggers=False,
    defaults={"logfilename": f"logs/{date.today()}.log"},
)

file_logger = logging.getLogger("simpleFileLogger")
console_logger = logging.getLogger("simpleConsoleLogger")
