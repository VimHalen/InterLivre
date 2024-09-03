"""
InterLivre, audiobook splicer
Copyright (C) 2024 VimHalen
See LICENSE for license information.
InterLivreApp@gmail.com
"""

from pubsub import pub
import utils
from filemanager import FileManager
from audiotools import AudioFormat
from interleaver import Interleaver


class ILModel:

    def __init__(self):
        self.filemanager = FileManager(input_file_formats=['wav', 'mp3'])
        self._dst_audio_format = AudioFormat(48000, 16, 1, 'wav')
        self.tmp_audio_format = AudioFormat(48000, 16, 1, 'wav')
        self._dst_name = None
        self.intersplicer = Interleaver()
        self._is_each_dir_valid = False
        self._seg_size_min = 5
        self._seg_size_max = 18
        self._write_segments = False
        pub.subscribe(self.OnNotifyPropertyChanged, "NotifyPropertyChanged")

    @property
    def is_each_dir_valid(self):
        req_files = [self.filemanager.src1_dir, self.filemanager.src2_dir, self.filemanager.dst_dir, self.dst_name]
        res = True
        for f in req_files:
            if utils.is_blank(f):
                res = False
        if res != self._is_each_dir_valid:
            self._is_each_dir_valid = res
            pub.sendMessage("NotifyPropertyChanged", prop="is_each_dir_valid")
            pub.sendMessage("IsEachDirValidChanged", is_ready=res)

    @property
    def dst_name(self):
        return self._dst_name

    @dst_name.setter
    def dst_name(self, name):
        if name != self._dst_name:
            self._dst_name = name
            pub.sendMessage("NotifyPropertyChanged", prop="dst_name")
            pub.sendMessage("DstNameChanged", text=name)

    @property
    def dst_audio_format(self):
        return self._dst_audio_format

    @dst_audio_format.setter
    def dst_audio_format(self, val):
        if self._dst_audio_format.equals(val) is False:
            self._dst_audio_format = val
            pub.sendMessage("NotifyPropertyChanged", prop="dst_audio_format")

    @property
    def seg_size_min(self):
        return self._seg_size_min

    @seg_size_min.setter
    def seg_size_min(self, val):
        if val != self._seg_size_min and hasattr(self, '_seg_size_max') and self._seg_size_max > val:
            self._seg_size_min = val
            pub.sendMessage("SegmentRangeChanged", srange=[self._seg_size_min, self._seg_size_max])
            pub.sendMessage("NotifyPropertyChanged", prop="seg_size_min")

    @property
    def seg_size_max(self):
        return self._seg_size_max

    @seg_size_max.setter
    def seg_size_max(self, val):
        if val != self._seg_size_max and (self, '_seg_size_min') and self._seg_size_min < val:
            self._seg_size_max = val
            pub.sendMessage("SegmentRangeChanged", srange=[self._seg_size_min, self._seg_size_max])
            pub.sendMessage("NotifyPropertyChanged", prop="seg_size_max")

    @property
    def write_segments(self):
        return self._write_segments

    @write_segments.setter
    def write_segments(self, val):
        if val != self._write_segments:
            self._write_segments = val
            pub.sendMessage("WriteSegmentsChanged", should_write_segments=self._write_segments)
            pub.sendMessage("NotifyPropertyChanged", prop="write_segments")

    def OnNotifyPropertyChanged(self, prop):
        """Quick hack to update properties"""
        is_each_dir_valid = self.is_each_dir_valid
        if prop == "src1_dir" or prop == "src2_dir":
            filelist = self.filemanager.src_file_list

    def get_tmp_output_filename(self, filename_prefix, idx, section_count):
        return self.get_output_filename(f"tmp_{filename_prefix}", idx, section_count)

    def get_output_filename(self, filename_prefix, idx, section_count):
        res = filename_prefix
        if section_count > 99:
            res += f"_{idx:05d}"
        elif section_count > 1:
            res += f"_{idx:02d}"
        res += ".wav"
        return res

    def create_workspace(self):
        src_files = self.filemanager.src_files_selected
        self.filemanager.create_tmp_workspace()
        self.filemanager.copy_to_workspace(src_files)
