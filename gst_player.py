#!/usr/bin/env python3

import logging
import queue
import threading
from time import monotonic

import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst  # type: ignore # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GstPlayer")

Gst.init(None)


state_map = {
    Gst.State.NULL: 'STOP',
    Gst.State.READY: 'STOP',
    Gst.State.PAUSED: 'PAUSED',
    Gst.State.PLAYING: 'PLAYING',
    None: 'STOP'
}

class GstPlayer(threading.Thread):
    CHUNK_SIZE = 4096
    PIPELINE = 'appsrc name=src ! decodebin ! autoaudiosink'
    EVENT_TIMEOUT_SECS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.command_queue = queue.Queue()
        self.play_confirmed_e = threading.Event()
        self.stop_confirmed_e = threading.Event()
        self.stop_confirmed_e.set()

        self.pipeline: Gst.Pipeline = None
        self.get_chunk_hook = None
        self.track_ended_hook = lambda: None

        self.show_stats = False

    def run(self):
        while True:
            cmd = self.command_queue.get()
            logger.debug(f"Processing command: {cmd}")
            match cmd:
                case 'CONFIGURED':
                    self.activate_stream()
                case 'STOP':
                    if self.deactivate_stream():
                        threading.Thread(target=self.track_ended_hook).start()
                case 'SHUTDOWN':
                    self.deactivate_stream()
                    break
                case _:
                    logger.warning(f"Unexpected command: {cmd}")

    def setup_pipeline(self):
        retval = Gst.parse_launch(self.PIPELINE)
        self.appsrc = retval.get_by_name('src')
        self.appsrc.set_property('format', Gst.Format.TIME)
        self.appsrc.set_property('block', True)
        self.appsrc.set_property('is-live', True)
        self.appsrc.set_property('max-bytes', 8192)
        self.appsrc.connect('need-data', self.on_need_data)
        return retval

    def activate_stream(self):
        self.last_time = None
        self.stop_confirmed_e.clear()
        self.pipeline = self.setup_pipeline()
        self.pipeline.set_state(Gst.State.PLAYING)
        self.play_confirmed_e.set()
        logger.info("Playing...")

    def deactivate_stream(self):
        if not self.pipeline:
            return False

        self.play_confirmed_e.clear()
        self.appsrc.disconnect_by_func(self.on_need_data)
        self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None
        self.stop_confirmed_e.set()
        logger.info("Stopped.")
        return True

    def on_need_data(self, src, length):
        assert self.get_chunk_hook

        chunk_size = length if length > 0 else self.CHUNK_SIZE
        if not (chunk := self.get_chunk_hook(chunk_size)):
            src.emit('end-of-stream')
            logger.info("Stream exhaused.")
            self.command_queue.put('STOP')
            return

        buf = Gst.Buffer.new_allocate(None, len(chunk), None)
        buf.fill(0, chunk)
        src.emit('push-buffer', buf)

        if self.show_stats:
            self.print_stats(len(chunk))

    def print_stats(self, chunk_size):
        if self.last_time:
            elapsed = monotonic() - self.last_time
            if elapsed > 0:
                bitrate = (chunk_size) / elapsed / 1000  # kB/s
                print(f"\rbitrate: {bitrate:.2f} kB/s    ", end='', flush=True)
        self.last_time = monotonic()

    def configure(self, get_chunk_hook, track_ended_hook=None):
        self.get_chunk_hook = get_chunk_hook
        self.track_ended_hook = track_ended_hook or (lambda: None)
        self.stop_confirmed_e.clear()
        self.command_queue.put('CONFIGURED')

    def stop(self):
        if self.stop_confirmed_e.is_set():
            return True

        self.command_queue.put('STOP')
        retval = self.stop_confirmed_e.wait(self.EVENT_TIMEOUT_SECS)
        logger.debug(f"stop confirmed: {retval}")
        return retval

    def pause(self):
        assert self.is_playing()
        self.pipeline.set_state(Gst.State.PAUSED)

    def resume(self):
        assert self.is_playing()
        self.pipeline.set_state(Gst.State.PLAYING)

    def get_state(self):
        if self.pipeline is None:
            return 'STOP'

        state = self.pipeline.get_state(1 * Gst.SECOND)
        logger.debug("{} -> {}".format(state.state.value_name, state.pending.value_name))

        return state_map.get(state.state)

    def is_playing(self):
        return self.play_confirmed_e.is_set()

    def confirm_play_starts(self):
        retval = self.play_confirmed_e.wait(self.EVENT_TIMEOUT_SECS)
        logger.debug(f"play confirmed: {retval}")
        return retval

    def shutdown(self):
        if self.is_playing():
            self.stop()

        self.command_queue.put('SHUTDOWN')
        self.join()
        logger.info("Shutdown complete.")
