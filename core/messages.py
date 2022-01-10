import os
from configparser import ConfigParser


class Messages(object):

    def __init__(self):
        self.section = "default"
        self.messages = dict()
        config = ConfigParser()

        for root, dirs, files in os.walk("."):
            for filename in files:
                if filename != "messages.ini":
                    continue

                filepath = os.path.join(root, filename)
                config.read(filepath)

                if not config.has_section(section=self.section):
                    continue

                package = root.replace(os.path.sep, ".").strip(".")
                configs = config._sections[self.section]
                for k, v in configs.items():
                    self.messages[f"{package}.{k}"] = v

    def __getitem__(self, key):
        return self.messages[key]
