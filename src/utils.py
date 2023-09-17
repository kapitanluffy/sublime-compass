import sublime
import os
import subprocess
from typing import List
from ..utils import plugin_settings
from . import File

def list_files(directory = "."):
    settings = plugin_settings()
    ripgrep = str(settings.get("ripgrep_path", ""))

    if ripgrep == "" or os.path.exists(ripgrep) is False:
        return None

    command = [settings["ripgrep_path"], "--files", directory]

    try:
        # Run the command and capture the output
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # This makes sure the output is treated as text (str) rather than bytes
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.returncode != 0:
            print(result.stderr)

        return result.stdout.splitlines()
    except Exception as e:
        print(f"An error occurred: {e}")


def parse_listed_files(window: sublime.Window):
    folders = window.folders()
    items: List[File] = []

    for folder in folders:
        files = list_files(folder)

        if files is None:
            return None

        for file in files:
            items.append(File(file, folder))

        return items
