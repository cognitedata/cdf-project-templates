import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

TEST_DIR_ROOT = Path(__file__).resolve().parent

SUPPORTED_TOOLKIT_VERSIONS = [
    "0.1.0b1",
    "0.1.0b2",
    "0.1.0b3",
    "0.1.0b4",
    "0.1.0b5",
    "0.1.0b6",
]


@contextlib.contextmanager
def chdir(new_dir: Path) -> Iterator[None]:
    """
    Change directory to new_dir and return to the original directory when exiting the context.

    Args:
        new_dir: The new directory to change to.

    """
    current_working_dir = Path.cwd()
    os.chdir(new_dir)

    try:
        yield

    finally:
        os.chdir(current_working_dir)