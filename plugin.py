from .utils import *
from .src import *

def plugin_loaded():
    reset_plugin_state()
    load()
