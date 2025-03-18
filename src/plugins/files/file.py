import os

class File():
    def __init__(self, file: str, folder: str, window: str):
        self.file = file
        self.folder = folder
        self.window = window
        filename = file.replace("%s\\" % folder, "")
        self.relative = "%s" % (filename)

    def get_window(self):
        return self.window

    def get_folder(self):
        return self.folder

    def get_file_name(self):
        return self.relative

    def get_full_path(self):
        return self.file

    def get_extension(self):
        ext = os.path.splitext(self.file)[1]
        return ext
