# InterLivre: Interleave audiobooks

## Getting Started

* [Download InterLivre](https://github.com/vimhalen/InterLivre/releases/latest)
* [Demo Video](https://www.youtube.com/watch?v=kZqpZ60LSZA)

## About InterLivre

InterLivre is a desktop application for combining audiobook recordings.
InterLivre takes two recordings of an audiobook, each in a different language, 
and creates a new version that switches back and forth between the two recordings every so often.

### Motivation

I've been practicing French during my commute to work by listening to podcasts for 
intermediate-level French language learners.
The podcasts are all on the short side though and I thought it would be fun to try
listening to something longer in French, like a novel.

I chose a novel that I've already read several times in English, so I know the story well, and gave it a try. 
It turned out to be a bit too difficult for me to follow the French version entirely on its own without getting lost.
Some parts were fine, but others were tricky, and I would lose track of the story here and there
unless I really tried hard to stay focused.

I thought it would be helpful if I could switch back and forth between the English and French versions of the book while listening. 
That way, it would be easier to stay engaged with the story. 
That's why I made InterLivre.

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
I wrote InterLivre over a couple of weekends in summer, 2024. It's a quick hobby project and primarily meant for my own use.
I'm posting it in case it can be helpful to anyone else. Be warned, it's very lightly tested software... 
use it at your own risk!

Also, I don't know if listening to interleaved audiobooks like this will be a particularly effective way of practising or not. 
I'm experimenting with it. So far, I've listened to two interleaved novels and I think
this is helpful for me, but it's still too early to know.

## Dependencies
InterLivre makes use of the following libraries/packages, which are open source and free (and awesome):

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