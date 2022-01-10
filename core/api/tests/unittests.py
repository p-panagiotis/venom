import os

import pytest

from core import venom


class TestRunner(object):

    def __init__(self, config="pytest.ini"):
        self.config = config
        self.config_path = self.get_config_path()
        self.packages = self.get_packages(packages=venom.API_PACKAGES)

    def run(self):
        args = ["-v", "-c", self.config_path] + self.packages
        pytest.main(args)
        return True

    def get_config_path(self):
        for root, dirs, files in os.walk("."):
            for filename in files:
                if filename != self.config:
                    continue
                conf_path = os.path.join(root, self.config)
                return conf_path
        return None

    @staticmethod
    def get_packages(packages):
        tests_packages = []
        for package in packages:
            for root, dirs, files in os.walk(package):
                for filename in files:
                    if filename != "tests.py":
                        continue

                    tests_packages.append(root)
        return tests_packages
