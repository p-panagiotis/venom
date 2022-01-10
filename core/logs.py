import logging
import logging.handlers
import os
import sys

from core import venom


class Logger(object):

    def __init__(self):
        self.fmt = "%(asctime)s - %(levelname)s - %(message)s"
        self.level = logging.INFO
        self.date_fmt = "%Y-%m-%d %H:%M:%S"
        self.max_bytes = 10485760
        self.backup_count = 20
        self.log_filename = "venom.log"

        # create logs directory
        logs_folder_path = venom.cfg["core.logs.folder_path"]
        if not os.path.exists(logs_folder_path):
            os.makedirs(logs_folder_path)

        # logging handlers
        self.stream_handler = logging.StreamHandler(sys.stdout)
        self.rotating_file_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(venom.cfg["core.logs.folder_path"], self.log_filename),
            backupCount=self.backup_count,
            maxBytes=self.max_bytes
        )
        self.handlers = [self.stream_handler, self.rotating_file_handler]

    def configure(self):
        config = dict(level=self.level, format=self.fmt, datefmt=self.date_fmt, handlers=self.handlers)
        logging.basicConfig(**config)
        return self
