"""
InterLivre, audiobook splicer
Copyright (C) 2024 VimHalen
See LICENSE for license information.
InterLivreApp@gmail.com
"""

from pubsub import pub
import utils
from ilmodel import ILModel
from ilbookview import ILView
from audiotools import AudioConvertor
from interleaver import Interleaver
from os.path import join as pjoin
from threading import Thread, Event
from queue import Queue
from time import sleep
from appinfo import *


class ILViewController:

    def __init__(self):
        # Create the model
        self.model = ILModel()

        # Create progress bar attrs
        self.status = (0, "")
        self.cancel_event = Event()
        self.status_queue = Queue()

        # Subscribe to events
        pub.subscribe(self.OnSrc1Changing, "Src1Changing")
        pub.subscribe(self.OnSrc2Changing, "Src2Changing")
        pub.subscribe(self.OnSrcFilesSelectedChanging, "SrcFilesSelectedChanging")
        pub.subscribe(self.OnDstChanging, "DstChanging")
        pub.subscribe(self.OnDstNameChanging, "DstNameChanging")
        pub.subscribe(self.OnDstSampleRateChanging, "DstSampleRateChanging")
        pub.subscribe(self.OnDstFileFormatChanging, "DstFileFormatChanging")
        pub.subscribe(self.OnSegmentRangeChanging, "SegmentRangeChanging")
        pub.subscribe(self.OnWriteSegmentsChanging, "WriteSegmentsChanging")
        pub.subscribe(self.OnFileManagerError, "FileManagerError")
        pub.subscribe(self.OnConvert, "Convert")

        # Create the view
        self.mainview = ILView(APP_NAME)
        self.mainview.Start()

    # region Run
    def OnConvert(self):
        """Starts a thread to splice audiobooks together and updates the progress bar with status messages."""
        self.cancel_event.clear()
        self.mainview.frame.StartProgress()
        t = Thread(target=self.splice_books)
        t.start()
        user_cancelled = False
        latest_status = (1, "Preparing")
        while latest_status[0] < 100 and not user_cancelled:
            # Update progress status message and percentage with any new messages in the queue
            while not self.status_queue.empty():
                latest_status = self.status_queue.get()
            # Break if user wants to cancel the operation
            user_cancelled = self.mainview.frame.UpdateProgressStatus(min(latest_status[0], 99), latest_status[1])
            if user_cancelled:
                self.cancel_event.set()
                break
            # Sleep for a short amount of time
            sleep(0.05)
        t.join()
        self.mainview.frame.EndProgress(user_cancelled)

    def splice_books(self):
        """Interleaves audiobooks chapter by chapter."""
        if self.model.is_each_dir_valid is False:
            return
        # region convert input files
        convertor = AudioConvertor(self.model.tmp_audio_format)
        self.status_queue.put((1, "Creating temporary workspace"))
        self.model.create_workspace()
        self.status_queue.put((2, "Converting input files"))
        self.model.filemanager.convert_tmp_files(convertor, status_queue=self.status_queue, cancel=self.cancel_event)
        if utils.is_cancelled(self.cancel_event):
            return
        filelist = self.model.filemanager.get_input_files(self.model.filemanager.src1_tmp, self.model.filemanager.src2_tmp)
        self.status_queue.put((99, "Done converting input files"))

        book1_files = filelist[0]
        book2_files = filelist[1]
        book1_tmp = self.model.filemanager.src1_tmp
        book2_tmp = self.model.filemanager.src2_tmp
        dst_tmp = self.model.filemanager.dst_tmp
        section_count = min(len(book1_files), len(book2_files))

        # Create segments directories
        segdir = ""
        if self.model.write_segments:
            segment_dirs = []
            for i in range(0, section_count):
                segment_dirs.append(utils.strip_extension(self.model.get_output_filename(self.model.dst_name, i + 1, section_count)))
            segdir = self.model.filemanager.create_segments_directory(segment_dirs)

        # Interleave the chapters
        interleaver = Interleaver(min_seg_seconds=self.model.seg_size_min,
                                   max_seg_seconds=self.model.seg_size_max,
                                   should_write_segments=self.model.write_segments,
                                   segments_path=segdir,
                                   dst_name=self.model.dst_name,
                                   status_queue=self.status_queue,
                                   cancel=self.cancel_event)

        for i in range(0, section_count):
            progress = (i / section_count) * 100.0
            status_msg = f"Processing chapters {i + 1}/{section_count}"
            utils.update_progress(self.status_queue, progress, status_msg)
            if utils.is_cancelled(self.cancel_event):
                return
            book1_section_path = pjoin(book1_tmp, book1_files[i])
            book2_section_path = pjoin(book2_tmp, book2_files[i])
            out_section_path = pjoin(dst_tmp, self.model.get_tmp_output_filename(self.model.dst_name, i + 1, section_count))
            interleaver.dst_name = utils.strip_extension(self.model.get_output_filename(self.model.dst_name, i + 1, section_count))
            interleaver.interleave(book1_section_path, book2_section_path, out_section_path, status_msg)
        utils.update_progress(self.status_queue, 1, "Converting interleaved audio to selected output format")
        convertor.output_format.file_format = self.model.dst_audio_format.file_format
        convertor.output_format.sample_rate = self.model.dst_audio_format.sample_rate
        self.model.filemanager.convert_output_files(convertor, cleanup=True, cleanup_string="tmp_", status_queue=self.status_queue)
        if utils.is_cancelled(self.cancel_event):
            return
        self.status_queue.put((100, "Finished!"))

    # endregion

    def OnSrc1Changing(self, dir_str):
        self.model.filemanager.src1_dir = dir_str

    def OnSrc2Changing(self, dir_str):
        self.model.filemanager.src2_dir = dir_str

    def OnSrcFilesSelectedChanging(self, files):
        self.model.filemanager.src_files_selected = files

    def OnDstChanging(self, dir_str):
        self.model.filemanager.dst_dir = dir_str

    def OnDstNameChanging(self, name):
        self.model.dst_name = name

    def OnDstSampleRateChanging(self, sample_rate):
        self.model.dst_audio_format.sample_rate = sample_rate

    def OnDstFileFormatChanging(self, file_format):
        self.model.dst_audio_format.file_format = file_format

    def OnSegmentRangeChanging(self, srange):
        self.model.seg_size_min = srange[0]
        self.model.seg_size_max = srange[1]

    def OnWriteSegmentsChanging(self, should_write_segments):
        self.model.write_segments = should_write_segments

    def OnFileManagerError(self, error):
        pass
