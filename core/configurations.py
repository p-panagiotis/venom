import os

import yaml


class Configuration(object):

    def __init__(self, filename=None):
        self.filename = filename
        self.cfg = dict()
        self.default_cfg = dict()
        self.external_cfg = dict()
        self.external_cfg_path = os.path.join("./conf", filename) if filename else None

        for root, dirs, files in os.walk("."):
            for filename in files:
                if filename != "configs.yml":
                    continue

                with open(os.path.join(root, filename)) as f:
                    self.default_cfg.update(**yaml.load(f, Loader=yaml.SafeLoader))

        if self.filename and os.path.exists(self.external_cfg_path):
            with open(self.external_cfg_path) as f:
                self.external_cfg = yaml.load(f, Loader=yaml.SafeLoader)

        self.cfg = self.default_cfg.copy()
        self.cfg.update(self.external_cfg)

    def __getitem__(self, key):
        return self.cfg[key]

    def __getattr__(self, key):
        return self.cfg[key]
