"""
Module for reading config files (xknx.yaml).

* it will parse the given file
* and add the found devices to the devies vector of XKNX.
"""
from enum import Enum
import logging

from .config_v1 import ConfigV1
from .yaml_loader import load_yaml

logger = logging.getLogger("xknx.log")


class Version(Enum):
    """The used xknx.yaml structure version."""

    VERSION_1 = 1
    VERSION_2 = 2


class Config:
    """Class for parsing xknx.yaml."""

    def __init__(self, xknx):
        """Initialize Config class."""
        self.xknx = xknx

    def read(self, file="xknx.yaml"):
        """Read config."""
        logger.debug("Reading %s", file)
        doc = load_yaml(file)
        self.parse(doc)

    @staticmethod
    def parse_version(doc):
        """Parse the version of the xknx.yaml."""
        if "version" in doc:
            return Version(doc["version"])
        return Version.VERSION_1

    def parse(self, doc):
        """Parse the config from the YAML."""
        version = Config.parse_version(doc)
        if version is Version.VERSION_1:
            ConfigV1(xknx=self.xknx).parse(doc)
        elif version is Version.VERSION_2:
            raise NotImplementedError("Version 2 not yet implemented.")
