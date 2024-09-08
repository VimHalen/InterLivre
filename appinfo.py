"""
InterLivre, audiobook splicer

App metadata

Copyright (C) 2024 VimHalen
See LICENSE for license information.
InterLivreApp@gmail.com
"""

APP_NAME = "InterLivre"
AUTHOR = "VimHalen"
COPYRIGHT = "2024"
VERSION = "2024.09.07"
CONTACT = "InterLivreApp@gmail.com"
LICENSE_FILE = "LICENSE"
LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.en.html"
DEPENDENCY_LICENSE_INFO = "dependency-license-info.txt"
DEPENDENCY_URLS = {
    "FFmpeg":   {"home":    "https://www.ffmpeg.org",
                 "license": "https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html"},
    "LAME":     {"home":    "https://www.mp3dev.org",
                 "license": "https://lame.sourceforge.io/license.txt"},
    "NumPy":    {"home":    "https://numpy.org",
                 "license": "https://numpy.org/doc/stable/license.html"},
    "PyPubSub": {"home":    "https://pypubsub.readthedocs.io/en/v4.0.3/index.html",
                 "license": "https://pypubsub.readthedocs.io/en/v4.0.3/about.html"},
    "SciPy":    {"home":    "https://scipy.org",
                 "license": "https://github.com/scipy/scipy/blob/main/LICENSE.txt"},
    "wxPython": {"home":    "https://wxpython.org",
                 "license": "https://wxpython.org/pages/license/index.html"},
}
PNAMEOUT = "4548c2725652751a797ff2b39ee996c3138d747b714d5dddb6f7dc635fa9fb23"