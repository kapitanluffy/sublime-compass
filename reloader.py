import importlib
import sys
from os.path import basename, dirname

def reload(prefix, modules=[""]):
    directory = basename(dirname(__file__))
    prefix = "%s.%s." % (directory, prefix)

    for module in modules:
        module = (prefix + module).rstrip(".")
        if module in sys.modules:
            importlib.reload(sys.modules[module])

reload("src")

from .src import *
