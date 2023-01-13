from __future__ import annotations

import os.path
import shutil
from pathlib import Path


class _TmpDir:
    def __init__(self, path: str | os.PathLike = 'tmp', keep: bool = False):
        self.path = Path(path).absolute()
        self.keep = keep

        self.clean = self.path
        for parent in self.path.parents:
            if parent.exists():
                break
            self.clean = parent

    def __enter__(self):
        self.path.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.keep:
            shutil.rmtree(self.clean)

    def loc(self, *args: str | os.PathLike) -> Path:
        return Path(self.path, *args)


class _TmpChdir:
    def __init__(self, location: str | os.PathLike):
        self.origin = os.getcwd()
        self.target = location

    def __enter__(self):
        os.chdir(self.target)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.origin)


class _TmpFile:
    def __init__(self, filename: str | os.PathLike):
        self.path = Path(filename)
        self.data: bytes | None = None
        if self.path.exists():
            with open(self.path, 'rb') as old_file:
                self.data = old_file.read()
        self.file = None

    class FileHandler:
        def __init__(self, path: Path, data: bytes | None):
            self.path = path.absolute()
            self.data = data

        def write(self, data: bytes | str, append: bool = False):
            mode = 'a' if append else 'w'
            kwargs = {}
            if isinstance(data, bytes): 
                mode += 'b'
            else:
                kwargs['encoding'] = 'utf-8'
            with open(self.path, mode, **kwargs) as file:
                file.write(data)

        def copy(self, from_path: str | os.PathLike):
            shutil.copy(from_path, self.path)

    def __enter__(self):
        return _TmpFile.FileHandler(self.path, self.data)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.data is not None:
            with open(self.path, 'wb') as file:
                file.write(self.data)
        else:
            os.remove(self.path)

tmpdir = _TmpDir
tmpcd = _TmpChdir
tmpfile = _TmpFile