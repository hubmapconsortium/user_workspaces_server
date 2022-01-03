from user_workspaces_server.controllers.storagemethods.abstract_storage import AbstractStorage
import os


class LocalFileSystemStorage(AbstractStorage):
    def create_dir(self, path):
        os.makedirs(os.path.join(self.root_dir, path), exist_ok=True)

    def get_dir_size(self, path):
        total = 0
        full_path = os.path.join(self.root_dir, path)
        try:
            for entry in os.scandir(full_path):
                if entry.is_file():
                    # if it's a file, use stat() function
                    total += entry.stat().st_size
                elif entry.is_dir():
                    # if it's a directory, recursively call this function
                    total += self.get_dir_size(entry.path)
        except NotADirectoryError:
            # if `directory` isn't a directory, get the file size then
            return os.path.getsize(full_path)
        except PermissionError:
            # if for whatever reason we can't open the folder, return 0
            return 0
        return total

    def get_dir_tree(self, path):
        return os.fwalk(os.path.join(path))

