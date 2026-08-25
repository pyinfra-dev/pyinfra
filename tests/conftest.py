from pathlib import Path
from unittest.mock import patch

import pyinfra_testing.operations
import pyinfra_testing.util
from pyinfra_testing.util import patch_files as _patch_files


class patch_files(_patch_files):
    """
    Extend ``pyinfra_testing.util.patch_files`` to also patch ``pathlib.Path``
    methods, now that pyinfra itself uses pathlib for local filesystem access.
    """

    def __enter__(self):
        patch_self = self

        def _path_exists(p):
            return patch_self.exists(str(p))

        def _path_is_file(p):
            return patch_self.isfile(str(p))

        def _path_is_dir(p):
            return patch_self.isdir(str(p))

        def _path_is_symlink(p):
            return patch_self.islink(str(p))

        def _path_mkdir(p, mode=0o777, parents=False, exist_ok=False):
            return True

        self._path_patches = [
            patch.object(Path, "exists", new=_path_exists),
            patch.object(Path, "is_file", new=_path_is_file),
            patch.object(Path, "is_dir", new=_path_is_dir),
            patch.object(Path, "is_symlink", new=_path_is_symlink),
            patch.object(Path, "mkdir", new=_path_mkdir),
        ]

        for patched in self._path_patches:
            patched.start()

        return super().__enter__()

    def __exit__(self, type_, value, traceback):
        try:
            super().__exit__(type_, value, traceback)
        finally:
            for patched in self._path_patches:
                patched.stop()


# ``pyinfra_testing.operations`` imports ``patch_files`` by value, so patch
# both module namespaces.
pyinfra_testing.util.patch_files = patch_files
pyinfra_testing.operations.patch_files = patch_files
