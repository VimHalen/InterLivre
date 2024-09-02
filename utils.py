"""
InterLivre, audiobook splicer

Utility functions

Copyright (C) 2024 VimHalen
See LICENSE for license information.
InterLivreApp@gmail.com
"""

import logging
import sys
from os import listdir, pardir
from os.path import isfile, abspath, basename, join as pjoin
from numpy import linspace


# region files
def list_files_with_extension(dir_path, extension):
    """Returns a list of files in a directory with the given extension."""
    file_list = list_files(dir_path)
    return [f for f in file_list if f.split('.')[-1] == extension]


def list_files(dir_path):
    """Returns a list of files in a directory"""
    if dir_path is None or dir_path == "":
        return []
    return [f for f in listdir(dir_path) if isfile(pjoin(dir_path, f))]


def get_extension(file_path):
    """Returns everything after last '.' character in file_path argument"""
    return file_path.split('.')[-1]


def strip_extension(file_path):
    """Returns everything before last '.' character in file_path argument"""
    tok = file_path.split('.')[:-1]
    return '.'.join(tok)


def get_parent_directory(file_path):
    """Strips the last element from a path"""
    return abspath(pjoin(file_path, pardir))
# endregion


# region audio
def float_to_int16(x):
    # Clamp
    res = max(-1.0, min(x, 1.0))
    # Normalize
    res = (x + 1.0) * 0.5
    # Scale to int16
    res *= 65535
    res -= 32678
    res = int(round(res))
    return res


def apply_lin_env(buffer, start, end, start_gain, end_gain):
    """Applies a linear envelope to buffer in place from [start, end)."""
    fade_time = end - start
    env = linspace(start_gain, end_gain, num=fade_time)
    for i in range(0, fade_time):
        buffer[i + start] *= env[i]

# endregion


# region other
def is_blank(s):
    return s is None or not s or s.isspace() is True


def clamp(x, lo, hi):
    return min(max(x, lo), hi)


def update_progress(status_queue, progress, msg):
    """Adds a new progress percent and status message to the queue"""
    if status_queue is not None:
        p = int(clamp(progress, 1, 99))
        status_queue.put((p, msg))


def is_cancelled(cancel):
    """Returns True if audiobook splicing has been cancelled"""
    if cancel is not None:
        return cancel.is_set()
# endregion


# region packaging
# Modified the following function from Masoud Rahimi on StackOverflow (https://stackoverflow.com/a/57134187)
def resource_path(relative_path, dbg="."):
    if hasattr(sys, '_MEIPASS'):
        return pjoin(sys._MEIPASS, relative_path)
    elif hasattr(sys, '_MEIPASS2'):
        return pjoin(sys._MEIPASS2, relative_path)
    return pjoin(abspath(dbg), relative_path)


# Snagged the following function from Rainer Niemann on StackOverflow (https://stackoverflow.com/a/72060275)
def resource_path_alternate(relative_path, dbg="."):
    try:
        base_path = sys._MEIPASS
    except Exception as e:
        base_path = abspath(dbg)
        logging.exception(e)

    return pjoin(base_path, relative_path)
# endregion
