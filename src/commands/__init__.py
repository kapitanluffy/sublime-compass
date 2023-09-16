from ...reloader import reload

reload("src.commands", ["close", "move", "build_stack"])

from .close import CompassCloseCommand
from .move import CompassMoveCommand
from .build_stack import CompassBuildStackCommand

__all__ = [
    "CompassCloseCommand",
    "CompassMoveCommand",
    "CompassBuildStackCommand"
]
