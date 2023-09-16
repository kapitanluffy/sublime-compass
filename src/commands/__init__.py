from ...reloader import reload

reload("src.commands", ["close", "move"])

from .close import CompassCloseCommand
from .move import CompassMoveCommand

__all__ = [
    "CompassCloseCommand",
    "CompassMoveCommand"
]
