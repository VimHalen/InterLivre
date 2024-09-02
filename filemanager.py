"""
InterLivre, audiobook splicer

File read/write utilities

Copyright (C) 2024 VimHalen
See LICENSE for license information.
InterLivreApp@gmail.com
"""

import logging
from os import mkdir, remove, rename
from os.path import isdir, join as pjoin
from pubsub import pub
from shutil import copy
import utils

ERR_SRC_MATCH = "Source 1 directory matches source 2 directory. Choose a different location."
ERR_NOT_FOUND = "Directory not found"
ERR_OK = "OK"

class FileManager:
    """File manager for creating tmp workspace, copying files, and naming output files"""
    def __init__(self, src1_dir=None, src2_dir=None, dst_dir=None, input_file_formats=['wav']):
        self._src1_dir = src1_dir
        self._src2_dir = src2_dir
        self._dst_dir = dst_dir
        self.input_file_formats = input_file_formats
        self.error_string = None
        self._src_file_list = []
        self._src_files_selected = None
        self.segments_directory = "InterLivre_Segments"

    # region Properties
    @property
    def src1_dir(self):
        """str: Path to a directory containing the book 1 audio files."""
        return self._src1_dir

    @src1_dir.setter
    def src1_dir(self, src):
        if isdir(src) is False:
            if src == "":
                self._src1_dir = ""
            else:
                self.handle_path_error(ERR_NOT_FOUND, src)
        elif self._src1_dir != src:
            self._src1_dir = src
            pub.sendMessage("NotifyPropertyChanged", prop="src1_dir")
            pub.sendMessage("Src1Changed", path=self._src1_dir)

    @property
    def src2_dir(self):
        """str: Path to a directory containing the book 2 audio files."""
        return self._src2_dir

    @src2_dir.setter
    def src2_dir(self, src):
        if isdir(src) is False:
            if src == "":
                self._src2_dir = ""
            else:
                self.handle_path_error(ERR_NOT_FOUND, src)
        elif self._src2_dir != src:
            self._src2_dir = src
            pub.sendMessage("NotifyPropertyChanged", prop="src2_dir")
            pub.sendMessage("Src2Changed", path=self._src2_dir)

    @property
    def dst_dir(self):
        """str: Path to a directory to write output audio files combining books 1 and 2."""
        return self._dst_dir

    @dst_dir.setter
    def dst_dir(self, dst):
        if isdir(dst) is False:
            if dst == "":
                self._dst_dir = ""
            else:
                self.handle_path_error(ERR_NOT_FOUND, dst)
        elif self._dst_dir != dst:
            self._dst_dir = dst
            pub.sendMessage("NotifyPropertyChanged", prop="dst_dir")
            pub.sendMessage("DstChanged", path=self._dst_dir)

    @property
    def src_file_list(self):
        """list(list(str)): Input audio files found in src1 and src2 dirs.
         src_file_list[0] is a list of src1 files and src_file_list[1] is a list of src2 files."""
        file_list = self.get_input_files(self.src1_dir, self.src2_dir)
        if file_list != self._src_file_list:
            self._src_file_list = file_list
            pub.sendMessage("NotifyPropertyChanged", prop="src_file_list")
            pub.sendMessage("SrcFileListChanged", files=self._src_file_list)

    @src_file_list.setter
    def src_file_list(self, value):
        if value != self._src_file_list:
            self._src_file_list = value
            pub.sendMessage("NotifyPropertyChanged", prop="src_file_list")
            pub.sendMessage("SrcFileListChanged", files=self._src_file_list)

    @property
    def src_files_selected(self):
        """list(list(str)): list of input audio files that have been selected to include in the output audiobook.
        src_files_selected[0] is a list of src1 files and src_files_selected[1] is a list of src2 files."""
        return self._src_files_selected

    @src_files_selected.setter
    def src_files_selected(self, value):
        if value != self._src_files_selected:
            self._src_files_selected = value
            pub.sendMessage("NotifyPropertyChanged", prop="src_files_selected")
            pub.sendMessage("SrcFilesSelectedChanged", files=self._src_files_selected)
    # endregion

    def handle_path_error(self, err_str, path):
        """Notifies observers that a path-related error has occurred."""
        self.error_string = err_str + f" ({path})"
        pub.sendMessage("FileManagerError", error=err_str)

    def get_input_files(self, dir1, dir2):
        """Validates paths and get input file lists.

        Args:
            dir1 (str): Path to the directory containing the src 1 audio files.
            dir2 (str): Path to the directory containing the src 2 audio files.

        Returns:
            2d list of strings for all valid input files found in the src directories.
            Element 0 contains the src1 file list and element 1 contains the src2 file list.
        """
        src1_files = []
        src2_files = []
        for ftype in self.input_file_formats:
            src1_files += utils.list_files_with_extension(dir1, ftype)
            src2_files += utils.list_files_with_extension(dir2, ftype)
        src1_files.sort(key=str.lower)
        src2_files.sort(key=str.lower)
        return [src1_files, src2_files]

    def get_output_tmp_files(self):
        """Returns a list of tmp output wav files that are ready to be converted into the final output files."""
        dst_files = utils.list_files_with_extension(self.dst_tmp, 'wav')
        dst_files.sort(key=str.lower)
        return dst_files

    def __create_dir(self, parent, dir_name, cleanup=False, cleanup_string=None):
        """Creates a directory at a given path.

        If the directory already exists, optionally remove pre-existing files with a filename containing a given string.

        Args:
            parent (str): Path to location to create the directory.
            dir_name (str): Name of new directory.
            cleanup (bool): If True, remove any pre-existing files in the directory containing cleanup_string.
            cleanup_string (str): Remove files with a filename containing this string if cleanup is True.

        Returns:
            str: Path to the created directory
        """
        res = pjoin(parent, dir_name)
        if isdir(res) is not True:
            try:
                mkdir(res)
            except Exception as e:
                self.handle_path_error(f"Failed to create directory", dir_name)
                logging.exception(e)
        elif cleanup is True and cleanup_string is not None:
            for f in utils.list_files(res):
                if cleanup_string in f:
                    remove(pjoin(res, f))
        return res

    def create_segments_directory(self, subdirs):
        """Creates a directory to store individual audio segments.

        Args:
            subdirs (list (str)): Directory names for each chapter to create within the segments directory.

        Returns:
            str: Path to the segments directory.
        """
        res = self.__create_dir(self.dst_dir, self.segments_directory)
        for sd in subdirs:
            self.__create_dir(res, sd)
        return res

    def create_tmp_workspace(self):
        """Creates a temporary workspace within the dst_dir."""
        self.tmp = self.__create_dir(self.dst_dir, 'interlivre-tmp')
        self.src1_tmp = self.__create_dir(self.tmp, 'book1', cleanup=True, cleanup_string="tmp")
        self.src2_tmp = self.__create_dir(self.tmp, 'book2', cleanup=True, cleanup_string="tmp")
        self.dst_tmp = self.__create_dir(self.tmp, 'interleaved', cleanup=True, cleanup_string="tmp")

    def copy_to_workspace(self, filelists):
        """Copies input audio files into the tmp workspace and prepends 'tmp_' to the filenames.

        Args:
            filelists (list(list(str))): List of src 1 audio files and a list of src 2 audio files.
        """
        src_dirs = [self.src1_dir, self.src2_dir]
        tmp_dirs = [self.src1_tmp, self.src2_tmp]
        for i, filelist in enumerate(filelists):
            for f in filelist:
                src_path = pjoin(src_dirs[i], f)
                dst_path = pjoin(tmp_dirs[i], f'tmp_{f}')
                copy(src_path, dst_path)
            filelist.sort(key=str.lower)

    def convert_tmp_files(self, convertor, status_queue=None, cancel=None):
        """Converts input tmp files into the correct audio file format for interleaving (48k, 16b, mono, wav)."""
        tmp_files = self.get_input_files(self.src1_tmp, self.src2_tmp)
        tmp_dirs = [self.src1_tmp, self.src2_tmp]
        file_cnt = len(tmp_files[0]) + len(tmp_files[1])

        for i, files in enumerate(tmp_files):
            for j, f in enumerate(files):
                if cancel is not None:
                    if cancel.is_set():
                        # Return if user has manually cancelled the operation
                        return
                if status_queue is not None:
                    # Update the status to be displayed in the progress dialogue
                    progress = ((j + (i * len(files))) / file_cnt) * 100.0
                    # Strip off the leading "tmp"
                    file_display_str = f[4:]
                    utils.update_progress(status_queue, progress, f"Converting file {j + (i * len(files)) + 1}/{file_cnt}")
                fpath = pjoin(tmp_dirs[i], f)
                auformat = convertor.get_audio_format(fpath)
                if convertor.output_format.equals(auformat) is False:
                    # Do the audio format conversion and remove the old pre-converted tmp file
                    preconvert = pjoin(tmp_dirs[i], f"preconvert_{f}")
                    rename(pjoin(tmp_dirs[i], f), preconvert)
                    fwav = f'{utils.strip_extension(f)}.wav'
                    inpath = pjoin(tmp_dirs[i], preconvert)
                    outpath = pjoin(tmp_dirs[i], fwav)
                    convertor.convert(inpath, outpath)
                    try:
                        remove(inpath)
                    except Exception as e:
                        utils.update_progress(status_queue, progress, f"Couldn't find {inpath}, continuing")
                        logging.exception(e)

    def convert_output_files(self, convertor, cleanup=False, cleanup_string=None, status_queue=None, cancel=None):
        """Converts output files into the set output format while copying the files to the final dst directory."""
        files = self.get_output_tmp_files()
        file_cnt = len(files)
        ex = convertor.output_format.file_format
        for i, f in enumerate(files):
            if cancel is not None:
                if cancel.is_set():
                    return
            # Strip the "tmp_" prefix from the tmp file name
            out_str = f[4:]
            if status_queue is not None:
                progress = (i / file_cnt) * 100.0
                utils.update_progress(status_queue, progress, f"Converting file {i}/{file_cnt}")
            f_in = pjoin(self.dst_tmp, f)
            f_out = pjoin(self.dst_dir, f'{utils.strip_extension(out_str)}.{ex}')
            convertor.convert(f_in, f_out)
            if cleanup is True and cleanup_string is not None:
                if cleanup_string in f:
                    remove(f_in)
