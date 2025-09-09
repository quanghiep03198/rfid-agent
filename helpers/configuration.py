from configparser import ConfigParser
from enum import Enum
from os import path
from typing import Any, Callable

from helpers.logger import logger

# from pathlib import Path


class ConfigSection(Enum):
    READER = "READER"


__cfg_file__ = path.abspath(
    path.join(path.dirname(path.abspath(__file__)), "../.config")
)
if not path.exists(__cfg_file__):
    with open(__cfg_file__, "w", encoding="utf-8") as configfile:
        configfile.write(f"[{ConfigSection.READER.value}]\n")
        configfile.write("uhf_reader_tcp_ip = \n")
        configfile.write("uhf_reader_tcp_port = 8160\n")
        configfile.write("uhf_reader_ant = 1\n")
        configfile.write("uhf_reader_power = 10")
__configs__ = ConfigParser()
__configs__.read(filenames=__cfg_file__)


class ConfigService:
    @staticmethod
    def get_conf(
        section: str,
        key: str,
        default: Any = None,
        serializer: Callable[[str], Any] | None = None,
    ) -> str:
        if __configs__.has_option(section, key):
            value = __configs__.get(section, key, fallback=default)
            if serializer and callable(serializer):
                return serializer(value)
            return value

        logger.warning(f"Config key {key} not found in section {section}")
        return default

    @staticmethod
    def set_conf(section: ConfigSection, key: str, value: Any) -> None:
        # section = section if section is not None else ConfigSection.READER.value
        __configs__.set(section, key, str(value))
        with open(file=__cfg_file__, mode="w", encoding="utf-8") as file:
            __configs__.write(file)
