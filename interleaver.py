"""
InterLivre, audiobook splicer

Main audiobook segmentation and interleaving functionality

Copyright (C) 2024 VimHalen
See LICENSE for license information.
InterLivreApp@gmail.com
"""

import numpy as np
from scipy.io import wavfile as wav
import utils


class Interleaver:
    """Combines two audiobooks by interleaving."""

    SHOULD_CONTINUE = True

    def __init__(self,
                 sample_rate=48000,
                 is_stereo=False,
                 min_seg_seconds=5,
                 max_seg_seconds=20,
                 noise_threshold_ratio=0.03052,
                 should_write_segments=False,
                 segments_path="InterLivre_Segments",
                 dst_name="out",
                 status_queue=None,
                 cancel=None):
        self.sample_rate = sample_rate
        self.min_seg_len = min_seg_seconds * sample_rate
        self.max_seg_len = max_seg_seconds * sample_rate
        # TODO - magic number, assumes samples are always 16bit
        self.noise_threshold = int(round(32767.0 * noise_threshold_ratio))
        self.channel_cnt = 2 if is_stereo else 1
        self.should_write_segments = should_write_segments
        self.segments_path = segments_path
        self.dst_name = dst_name
        # Used by ILViewController thread for progress bar and status messages
        self.status_queue = status_queue
        self.status_msg = ""
        self.cancel_event = cancel

    def read(self, file_path):
        """Read a 48k, mono or stereo wav file from disk.

        Args:
            file_path (str): path to the file on disk.

        Returns:
            numpy array: buffer of audio samples read from file_path.

        Raises:
            ValueError: If sample rate != 48000 or channel count is not mono or stereo.
        """
        file_sr, buf = wav.read(file_path)
        if file_sr != self.sample_rate:
            raise ValueError(f'Invalid sample rate, expected {self.sample_rate}')
        if buf.ndim != self.channel_cnt:
            raise ValueError(f'Invalid channel count, expected {"stereo" if self.channel_cnt == 2 else "mono"}')
        return buf

    def update_progress(self, progress):
        """Update the progress queue.

        Args:
            progress (int): Percent complete for current operation.

        Returns:
            bool: True if interleaving process should continue.
        """
        utils.update_progress(self.status_queue, progress, self.status_msg)
        return not utils.is_cancelled(self.cancel_event)

    def interleave(self, src_path_1, src_path_2, dst_path, status_msg=""):
        """Interleave audiobook chapters into a new combined file and write it to disk.

        Reads wav files from disk for the corresponding chapters from each source, segments the chapters into sections,
        interleaves the sections to create a new combined chapter, and writes the new version to disk.

        Args:
            src_path_1 (str): Path to book 1 chapter
            src_path_2 (str): Path to book 2 chapter
            dst_path (str): Output path for combined chapter
            status_msg (str): Start of the message to be displayed by the progress dialogue. (e.g. 'file 1/24')
        """

        # Segment Src 1
        src1 = self.read(src_path_1)
        self.status_msg = f"{status_msg}, segmenting source 1"
        split_points_1 = self.segment(src1)

        # Segment Src 2
        src2 = self.read(src_path_2)
        self.status_msg = f"{status_msg}, segmenting source 2"
        split_points_2 = self.segment(src2)

        # Assemble new file
        self.status_msg = f"{status_msg}, interleaving audio"
        spliced_audio = self.assemble_segments(src1, src2, split_points_1, split_points_2)
        wav.write(dst_path, self.sample_rate, spliced_audio.astype(np.int16))

    # region Segmentation

    def find_start_point(self, buffer, threshold=1000, step_size=480):
        """Returns index of first sample over the given amplitude threshold using a given step size."""
        for i in range(0, len(buffer), step_size):
            if abs(buffer[i]) > threshold:
                while i > 0:
                    i -= 1
                    if buffer[i] < threshold:
                        return i + 1
        return -1

    def find_end_point(self, buffer, threshold=1000, step_size=480):
        """Returns index of last sample over the given amplitude threshold using a given step size."""
        for i in reversed(range(0, len(buffer), step_size)):
            if abs(buffer[i]) > threshold:
                while i < len(buffer):
                    i += 1
                    if buffer[i] < threshold:
                        return i - 1
        return 0

    def find_split_point(self, buffer, start=0, end=np.inf, threshold=1000, sample_stride=1):
        """Finds the longest window of silence in buffer[start:end]

        Args:
            buffer (np.array): Audio data.
            start (int): Index in buffer to begin search.
            end (int): Index in buffer to stop search.
            threshold (int): Noise gate threshold.

        Returns:
            A tuple containing the start, middle, and end indices in buffer describing the longest window of silence
        """
        if end == np.inf:
            end = len(buffer)
        max_gap = 0
        start_idx = start
        end_idx = start
        i = start
        while i < end:
            curr_start = i
            # Increment i by some small stride until the next sample over the threshold
            # If the stride is too large, this adds a chance of error by matching speaker frequency
            while i < end and abs(buffer[i]) < threshold:
                i += 6
            # Update the start and end points for the window of silence
            curr_end = i
            curr_max = curr_end - curr_start
            # Update the result variables when a new max gap is found
            if curr_max > max_gap:
                max_gap = curr_max
                start_idx = curr_start
                end_idx = curr_end
            i += sample_stride
        # Return a tuple containing the split point, start point, and end point
        mid_idx = int((end_idx - start_idx) / 2) + start_idx
        return start_idx, mid_idx, end_idx

    def segment(self, buffer):
        """Returns a list of suitable points at which to switch from the current audiobook to another"""
        # Filename vars
        segment_count = 0
        split_points = []
        speech_start_idx = self.find_start_point(buffer, self.noise_threshold)
        speech_end_idx = self.find_end_point(buffer, self.noise_threshold)

        # Trim leading silence
        if speech_start_idx > self.sample_rate * 2:
            split_points.append(speech_start_idx - self.sample_rate)
        else:
            split_points.append(0)

        # Segmentation loop
        # i should actually start at speech_start_idx. However, using split_points[0] instead because I prefer that
        # the first segment is a bit shorter than normal. It will likely be the introduction to the book or chapter.
        i = split_points[0]
        while (i + self.max_seg_len) < speech_end_idx:
            window_start = min(i + self.min_seg_len, len(buffer))
            window_end = min(i + self.max_seg_len, len(buffer))
            start, split, end = self.find_split_point(buffer, window_start, window_end, self.noise_threshold, 360)
            # Fade in/out around split point
            utils.apply_lin_env(buffer, start, split, 1.0, 0.0)
            utils.apply_lin_env(buffer, split, end, 0.0, 1.0)
            split_points.append(split)
            segment_count += 1
            i = end
            if self.update_progress(i / len(buffer) * 100.0) != Interleaver.SHOULD_CONTINUE:
                return

        # Trim leading silence
        if (len(buffer) - speech_end_idx) > (self.sample_rate * 2):
            split_points.append(speech_end_idx + self.sample_rate)
        else:
            split_points.append(len(buffer))

        return split_points

    # endregion

    def append_segment(self, dst_book, segment, isSrc1, seg_idx, total_idx):
        if self.should_write_segments:
            src_str = "src1" if isSrc1 else "src2"
            segment_name = f"{self.dst_name}_{total_idx:06d}_{src_str}_{seg_idx:06d}.wav"
            seg_path = utils.pjoin(self.segments_path, self.dst_name)
            seg_path = utils.pjoin(seg_path, segment_name)
            wav.write(seg_path, self.sample_rate, segment.astype(np.int16))
        return np.append(dst_book, segment)

    def assemble_segments(self, src1, src2, splits1, splits2, status_msg=""):
        """Interleaves audio from two sources using the given split points"""
        res = np.array([])
        i = 0

        # Trim off any leading or trailing silence
        leading_silence_1 = splits1[0]
        leading_silence_2 = splits2[0]
        trailing_silence_1 = len(src1) - splits1[-1]
        trailing_silence_2 = len(src2) - splits2[-1]
        endpoints_silence_1 = leading_silence_1 + trailing_silence_1
        endpoints_silence_2 = leading_silence_2 + trailing_silence_2
        src1_len = len(src1) - endpoints_silence_1
        src2_len = len(src2) - endpoints_silence_2
        src1_seg_cnt = len(splits1) - 1
        src2_seg_cnt = len(splits2) - 1
        src1_curr_idx = 1
        src2_curr_idx = 1
        total_segments = 1
        src2_ratio = float(splits2[src2_curr_idx] - endpoints_silence_2) / float(src2_len)

        while src1_curr_idx < src1_seg_cnt:
            # Read and append src1 segment
            seg_start = splits1[src1_curr_idx - 1]
            seg_end = splits1[src1_curr_idx]
            seg1 = src1[seg_start:seg_end]
            res = self.append_segment(res, seg1, True, src1_curr_idx, total_segments)

            # Update src1 counters
            src1_ratio = float(seg_end - endpoints_silence_1) / float(src1_len)
            src1_curr_idx += 1
            total_segments += 1

            while src1_ratio > src2_ratio and src2_curr_idx < src2_seg_cnt:
                # Read and append source 2 segment
                seg_start = splits2[src2_curr_idx - 1]
                seg_end = splits2[src2_curr_idx]
                seg2 = src2[seg_start:seg_end]
                res = self.append_segment(res, seg2, False, src2_curr_idx, total_segments)

                # Update src2 counters
                src2_curr_idx += 1
                src2_ratio = float(splits2[src2_curr_idx] - endpoints_silence_2) / float(src2_len)
                total_segments += 1

            # Update state so GUI can update its progress bar
            if self.update_progress((src1_ratio + src2_ratio) * 50.0) != Interleaver.SHOULD_CONTINUE:
                return

        # Append remaining src2 segments up to the penultimate segment
        while src2_curr_idx < src2_seg_cnt:
            seg_start = splits2[src2_curr_idx-1]
            seg_end = splits2[src2_curr_idx]
            seg2 = src2[seg_start:seg_end]
            res = self.append_segment(res, seg2, False, src2_curr_idx, total_segments)
            src2_curr_idx += 1
            total_segments += 1

        # Append the final segments
        seg1 = src1[splits1[-2]:splits1[-1]]
        res = self.append_segment(res, seg1, True, src1_curr_idx, total_segments)
        seg2 = src2[splits2[-2]:splits2[-1]]
        res = self.append_segment(res, seg2, False, src2_curr_idx, total_segments+1)

        return res
