# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION.
# SPDX-License-Identifier: Apache-2.0
#

import ctypes
import os
import sys

PREFERRED_LOAD_FLAG = ctypes.RTLD_LOCAL


def _load_system_installation(soname: str):
    """Try to dlopen() the library indicated by ``soname``
    Raises ``OSError`` if library cannot be loaded.
    """
    return ctypes.CDLL(soname, PREFERRED_LOAD_FLAG)


def _load_wheel_installation(soname: str):
    """Try to dlopen() the library indicated by ``soname``

    Returns ``None`` if the library cannot be loaded.
    """
    pkg_dir = os.path.dirname(__file__)
    # On Windows, check both bin/ and lib/ since CMake may install DLLs
    # to either location depending on the project's install rules.
    search_dirs = (["bin", "lib"] if sys.platform == "win32" else ["lib64"])
    for subdir in search_dirs:
        lib = os.path.join(pkg_dir, subdir, soname)
        if os.path.isfile(lib):
            return ctypes.CDLL(lib, PREFERRED_LOAD_FLAG)
    return None


def _add_dll_directories():
    """On Windows, add DLL directories so .pyd files can find native libraries."""
    if sys.platform != "win32":
        return
    pkg_dir = os.path.dirname(__file__)
    for subdir in ("bin", "lib"):
        dll_dir = os.path.join(pkg_dir, subdir)
        if os.path.isdir(dll_dir):
            os.add_dll_directory(dll_dir)


def load_library():
    """Dynamically load rapids_logger and its dependencies"""
    # On Windows, register DLL directories so that extension modules (.pyd)
    # can resolve their native library dependencies.
    _add_dll_directories()

    prefer_system_installation = (
        os.getenv("RAPIDS_LOGGER_PREFER_SYSTEM_LIBRARY", "false").lower()
        != "false"
    )

    soname = "rapids_logger.dll" if sys.platform == "win32" else "librapids_logger.so"
    logger_lib = None
    if prefer_system_installation:
        # Prefer a system library if one is present to
        # avoid clobbering symbols that other packages might expect, but if no
        # other library is present use the one in the wheel.
        try:
            logger_lib = _load_system_installation(soname)
        except OSError:
            logger_lib = _load_wheel_installation(soname)
    else:
        # Prefer the libraries bundled in this package. If they aren't found
        # (which might be the case in builds where the library was prebuilt before
        # packaging the wheel), look for a system installation.
        try:
            logger_lib = _load_wheel_installation(soname)
            if logger_lib is None:
                logger_lib = _load_system_installation(soname)
        except OSError:
            # If none of the searches above succeed, just silently return None
            # and rely on other mechanisms (like RPATHs on other DSOs) to
            # help the loader find the library.
            pass

    # The caller almost never needs to do anything with this library, but no
    # harm in offering the option since this object at least provides a handle
    # to inspect where libcudf was loaded from.
    return logger_lib
