#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

import Ice
from Ice import identityToString as id2str

Ice.loadSlice('-I{} spotifice_v0.ice'.format(Ice.getSliceDir()))
import Spotifice  # type: ignore # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MediaServer")


class StreamState:
    def __init__(self, track_id, filepath):
        self.track_id = track_id

        try:
            self.file = open(filepath, 'rb')
        except Exception as e:
            raise Spotifice.IOError(filepath, f"Error opening media file: {e}")

    def close(self):
        try:
            if self.file:
                self.file.close()
        except Exception as e:
            logger.error(f"Error closing file for track '{self.track_id}': {e}")

    def __repr__(self):
        return f"<StreamState track_id:'{self.track_id}'>"


class MediaServerI(Spotifice.MediaServer):
    def __init__(self, media_dir):
        self.media_dir = media_dir
        self.tracks = {}
        self.active_streams = {}  # media_render_id -> StreamState
        self.load_media()

    def ensure_track_exists(self, track_id):
        if track_id not in self.tracks:
            raise Spotifice.TrackError(track_id, "Track not found")

    def load_media(self):
        for filepath in sorted(Path(self.media_dir).iterdir()):
            if not filepath.is_file() or filepath.suffix.lower() != ".mp3":
                continue

            track_id = filepath.name
            title = filepath.stem
            info = Spotifice.TrackInfo(id=track_id, title=title)
            self.tracks[track_id] = (info, str(filepath))
            logger.info(f"Loaded track '{track_id}'")

        logger.info(f"Total tracks loaded: {len(self.tracks)}")

    # ---- MusicLibrary ----
    def get_all_tracks(self, current=None):
        return [info for info, _ in self.tracks.values()]

    def get_track_info(self, track_id, current=None):
        self.ensure_track_exists(track_id)
        return self.tracks[track_id][0]

    # ---- StreamManager ----
    def start_stream(self, track_id, media_render_id, current=None):
        self.ensure_track_exists(track_id)

        if not media_render_id.name:
            raise Spotifice.BadIdentity(id2str(media_render_id), "Invalid renderer ID")

        key = id2str(media_render_id)
        _, filepath = self.tracks[track_id]
        self.active_streams[key] = StreamState(track_id, filepath)

        logger.info("Started stream for track '{}' on renderer '{}'".format(
            track_id, id2str(media_render_id)))

    def stop_stream(self, media_render_id, current=None):
        key = id2str(media_render_id)
        stream_state = self.active_streams.pop(key, None)
        if stream_state:
            stream_state.close()

        logger.info(f"Stopped stream for renderer '{key}'")

    def get_audio_chunk(self, media_render_id, chunk_size, current=None):
        key = id2str(media_render_id)
        if key not in self.active_streams:
            raise Spotifice.StreamError(key, "No started stream for renderer")

        stream_state = self.active_streams[key]
        try:
            data = stream_state.file.read(chunk_size)
            if not data:
                logger.info(f"Track exhausted: '{stream_state.track_id}'")
                self.stop_stream(media_render_id, current)
            return data
        except Exception as e:
            raise Spotifice.IOError(
                stream_state.track_id, f"Error reading file: {e}")


def main(ic):
    properties = ic.getProperties()
    media_dir = properties.getPropertyWithDefault(
        'MediaServer.Content', 'media')
    servant = MediaServerI(Path(media_dir))

    adapter = ic.createObjectAdapter("MediaServerAdapter")
    proxy = adapter.add(servant, ic.stringToIdentity("mediaServer1"))
    logger.info(f"MediaServer: {proxy}")

    adapter.activate()
    ic.waitForShutdown()

    logger.info("Shutdown")


if __name__ == "__main__":
    try:
        with Ice.initialize(sys.argv[1]) as communicator:
            main(communicator)
    except KeyboardInterrupt:
        logger.info("Server interrupted by user.")
