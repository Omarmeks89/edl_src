"""Module contains toolchain tools for EDL translator"""

import pathlib
from typing import Any

from yaml import safe_load

from src.exceptions import SetupError

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

SETUP_FILE_PATH: str = "setup.yml"


def load_setup_data() -> dict[str, Any]:
    """load setup.yml for initial setup

    Returns:
        file content: dict[str, Any]

    Raises:
        SetupError: if no file or invalid config file
    """
    path = f"{pathlib.Path().cwd()}/{SETUP_FILE_PATH}"
    if not pathlib.Path(path).exists():
        raise SetupError("setup.yml not exists")

    with open(path, "r", encoding="utf-8") as file:
        return safe_load(file)
