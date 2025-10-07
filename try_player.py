#! /usr/bin/env python3

import time

from gst_player import GstPlayer

player = GstPlayer()
player.show_stats = True
player.start()

with open('test/media/4s.mp3', 'rb') as fd:
    player.configure(fd.read)
    player.confirm_play_starts()
    while player.is_playing():
        time.sleep(0.5)

    player.stop()

player.shutdown()
