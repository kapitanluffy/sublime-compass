import os

class File():
    def __init__(self, file, folder):
        self.file = file
        self.folder = folder
        filename = file.replace("%s\\" % folder, "")
        self.relative = "%s" % (filename)

    def get_folder(self):
        return self.folder

    def get_file_name(self):
        return self.relative

    def get_full_path(self):
        return self.file

    def get_extension(self):
        ext = os.path.splitext(self.file)[1]
        return ext
