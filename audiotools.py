"""
InterLivre, audiobook splicer
Copyright (C) 2024 VimHalen
See LICENSE for license information.
InterLivreApp@gmail.com
"""

import logging
from os.path import isfile
from pubsub import pub
import utils
import subprocess
import json

# Supported AudioFormat parameters
SAMPLE_RATES = (8000, 16000, 24000, 32000, 44100, 48000, 96000)
BIT_DEPTHS = (16, 32)
CHANNEL_COUNTS = (1, 2)
FILE_FORMATS = ('wav', 'mp3')

class AudioFormat:
    """Audio format parameters (e.g. sample rate, bit depth, channel counts, and file type)."""

    def __init__(self, sample_rate=48000, bit_depth=16, channels=1, file_format='wav'):
        self._sample_rate = sample_rate
        self._channels = channels
        self._bit_depth = bit_depth
        self._file_format = file_format

    # region Properties
    @property
    def sample_rate(self):
        """int: Sample rate in hz."""
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, sample_rate):
        if sample_rate in SAMPLE_RATES:
            self._sample_rate = sample_rate
            pub.sendMessage("SampleRateChanged", sample_rate=self.sample_rate)
        else:
            self.handle_property_error(f"""Invalid sample rate ({sample_rate}). 
                                       Supported sample rates: {SAMPLE_RATES}.""")

    @property
    def channels(self):
        """int: Channel count."""
        return self._channels

    @channels.setter
    def channels(self, channels):
        if channels in CHANNEL_COUNTS:
            self._channels = channels
            pub.sendMessage("ChannelsChanged", channels=self.channels)
        else:
            self.handle_property_error(f"""Invalid channel count ({channels}).
                                       Supported channel counts: {CHANNEL_COUNTS}.""")

    @property
    def bit_depth(self):
        """int: Bit depth"""
        return self._bit_depth

    @bit_depth.setter
    def bit_depth(self, bit_depth):
        if bit_depth in BIT_DEPTHS:
            self._bit_depth = bit_depth
            pub.sendMessage("AudioFormatChanged", bit_depth=self.bit_depth)
        else:
            self.handle_property_error(f"""Invalid bit depth ({bit_depth}).
                                       Supported bit depths: {BIT_DEPTHS}.""")

    @property
    def file_format(self):
        """str: File format extension."""
        return self._file_format

    @file_format.setter
    def file_format(self, file_format):
        if file_format in FILE_FORMATS:
            self._file_format = file_format
            pub.sendMessage("AudioFormatChanged", file_format=self._file_format)
        else:
            self.handle_property_error(f"""Invalid file format ({file_format}).
                                       Supported formats: {FILE_FORMATS}.""")
    # endregion

    def handle_property_error(self, err_str):
        """Notifies observers that a ModelError has occurred.

        Args:
            err_str (str): Property error description
        """
        pub.sendMessage("ModelError", error=err_str)

    @classmethod
    def bit_depth_to_string(cls, bit_depth):
        """Returns the bit depth as a string recognized by ffmpeg"""
        if bit_depth == 16:
            return 's16'
        if bit_depth == 32:
            return 's32'
        else:
            # TODO - handle more types
            return 's16'

    @classmethod
    def bit_depth_from_string(cls, bit_depth_string):
        """Returns bit depth as an int from an ffmpeg sample_format string"""
        if bit_depth_string == 's16':
            return 16
        if bit_depth_string == 's32':
            return 32
        else:
            return -1

    @classmethod
    def channel_count_to_display_string(cls, channel_count):
        """Returns the channel count as a string."""
        if channel_count == 1:
            return "mono"
        elif channel_count == 2:
            return "stereo"
        else:
            return "unknown"

    def equals(self, af):
        """Returns True if all class properties match.

        Args:
            af (AudioFormat): audio format to compare with self for equality.
        """
        return self.sample_rate == af.sample_rate and self.bit_depth == af.bit_depth and self.channels == af.channels and self.file_format == af.file_format


class AudioConvertor:
    """Convert audio files on disk into a given format using FFmpeg via subprocess.

    Attributes:
        output_format (AudioFormat): Output audio format to use when converting audio files.
    """

    def __init__(self, output_format):
        self.output_format = output_format

    # region info
    def get_sample_rate(self, in_path):
        """Get the sample rate of an audio file."""
        return self.probe(in_path)['sample_rate']

    def get_channel_count(self, in_path):
        """Get the channel count of an audio file."""
        return self.probe(in_path)['channels']

    def get_bit_depth(self, in_path):
        """Get the bit depth of an audio file."""
        return AudioFormat.bit_depth_from_string(self.probe(in_path)['sample_fmt'])

    def get_audio_format(self, in_path):
        """Returns an AudioFormat object describing an audio file on disk.

        Args:
            in_path (str): Path to an audio file on disk.
        """
        info = self.probe(in_path)
        sr = int(info['sample_rate'])
        ch = info['channels']
        bt = AudioFormat.bit_depth_from_string(info['sample_fmt'])
        ext = utils.get_extension(in_path)
        return AudioFormat(sr, bt, ch, ext)

    def convert(self, in_path, out_path):
        """Convert an input file into the chosen output format.

        Uses FFmpeg to convert a file on disk into the output format set in the output_format attribute via subprocess.
        The FFmpeg options include the '-y' flag, which enables overwriting existing files.

        Args:
            in_path (str): Path to the input audio file to convert.
            out_path (str): Path to the output audio file to write.
        """
        if isfile(in_path) is False:
            raise FileNotFoundError(f"Couldn't find input file {in_path}")
        if utils.get_extension(in_path) not in FILE_FORMATS:
            raise ValueError("Invalid input file extension")
        if utils.get_extension(out_path) not in FILE_FORMATS:
            raise ValueError("Invalid output file extension")
        try:
            args = [utils.resource_path("ffmpeg", dbg="./ffmpeg"),
                    '-i', in_path,
                    '-ac', str(self.output_format.channels),
                    '-ar', str(self.output_format.sample_rate),
                    '-sample_fmt', AudioFormat.bit_depth_to_string(self.output_format.bit_depth),
                    '-loglevel', 'quiet',
                    out_path, '-y']
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.communicate()
        except Exception as e:
            logging.exception(e)

    def probe(self, in_path):
        """Reads audio file metadata using ffprobe via subprocess.

        Args:
            in_path (str): Path to the input audio file.

        Returns:
            The first 'streams' dictionary instance from ffprobe.
        """
        args = [utils.resource_path("./ffprobe", dbg="./ffmpeg"), '-show_format', '-show_streams', '-of', 'json', in_path]
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return json.loads(out.decode('utf-8'))['streams'][0]
    # endregion
