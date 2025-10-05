#!/usr/bin/env python3

from time import sleep

import Ice

Ice.loadSlice('-I{} spotifice_v0.ice'.format(Ice.getSliceDir()))
import Spotifice  # type: ignore # noqa: E402


def main(ic):
    proxy = ic.stringToProxy('mediaServer1:tcp -p 10000')
    server = Spotifice.MediaServerPrx.checkedCast(proxy)
    if not server:
        raise RuntimeError('Invalid proxy for MediaServer')

    proxy = ic.stringToProxy('mediaRender1:tcp -p 10001')
    render = Spotifice.MediaRenderPrx.checkedCast(proxy)
    if not render:
        raise RuntimeError('Invalid proxy for MediaRender')

    print("Fetching all tracks...")
    tracks = server.get_all_tracks()
    for t in tracks:
        print(f"- {t.id}: {t.title}")

    if not tracks:
        print("No tracks found.")
        return

    print(f"Requesting info for track {tracks[0].id}")
    print(f"Track info: {tracks[0].id} - {tracks[0].title}")
    print("Loading track into MediaRender...")

    render.bind_media_server(server)
    render.stop()

    render.load_track(tracks[0].id)
    render.play()
    sleep(5)  # Let it play for 5 seconds

    render.stop()
    render.load_track(tracks[1].id)
    render.play()
    sleep(3)


if __name__ == '__main__':
    with Ice.initialize() as communicator:
        main(communicator)
