# InterLivre: Interleave audiobooks

## Getting Started

* [Download InterLivre](https://github.com/vimhalen/InterLivre/releases/latest)
* [Demo Video](https://www.youtube.com/watch?v=kZqpZ60LSZA)

## About InterLivre

InterLivre is a desktop application for combining audiobook recordings.
InterLivre takes two recordings of an audiobook, each in a different language, 
and creates a new version that switches back and forth between the two recordings every so often.

### Limitations

* Background music: InterLivre works by finding quiet moments in the recordings, 
when the narrators take a breath, and uses
those moments as points for switching from one recording to another. It won't work well
if the recordings have background music playing because there won't be regularly-occurring quiet moments.
* Synchronization: The two recordings can get out of sync from one another.
If one narrator reads with a lot of variation in speed and the other doesn't, then one
recording may get ahead of the other. I've found it to be tolerable in the books I've tried,
but it's not ideal.
* Volume levels: There are no gain adjustments applied to the input recordings. If one input recording is louder than
the other, then that will be true for the output recording too.  

## Disclaimers
I wrote InterLivre over a couple of weekends in summer, 2024. It's a quick hobby project and mainly for my own use.
I'm posting it in case it can be helpful to anyone else. It's very lightly tested software... 

## Dependencies
InterLivre makes use of the following opensource and free libraries/packages:

* [FFmpeg](https://www.ffmpeg.org)
  * [FFmpeg license page](https://www.ffmpeg.org/legal.html)
  * [LGPL-2.1](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
* [LAME](https://www.mp3dev.org)
  * [LAME license page](https://lame.sourceforge.io/license.txt)
* [NumPy](https://numpy.org)
  * [NumPy license page](https://numpy.org/doc/stable/license.html)
* [PyPubSub](https://pypubsub.readthedocs.io/en/v4.0.3/index.html)
  * [PyPubSub license page](https://pypubsub.readthedocs.io/en/v4.0.3/about.html)
* [SciPy](https://scipy.org)
  * [SciPy license page](https://github.com/scipy/scipy/blob/main/LICENSE.txt)
* [wxPython](https://wxpython.org)
    * [wxPython license page](https://wxpython.org/pages/license/index.html)
