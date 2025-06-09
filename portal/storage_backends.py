from django.core.files.storage import Storage

class BlockedLocalStorage(Storage):
    def _open(self, name, mode='rb'):
        raise NotImplementedError("Local storage is disabled.")

    def _save(self, name, content):
        raise NotImplementedError("Local storage is disabled.")
