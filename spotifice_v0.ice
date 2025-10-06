[["underscore"]]
#include <Ice/Identity.ice>

module Spotifice {
    class TrackInfo {
        string id;
        string title;
    };

    sequence<byte> AudioChunk;
    sequence<TrackInfo> TrackInfoSeq;

    exception Error {
        optional(1) string item;
        string reason;
    };

    exception TrackError extends Error{};
    exception StreamError extends Error{};
    exception BadReference extends Error{};
    exception BadIdentity extends Error{};
    exception PlayerError extends Error{};
    exception IOError extends Error{};

    interface MusicLibrary {
        TrackInfoSeq get_all_tracks() throws IOError;
        TrackInfo get_track_info(string track_id) throws IOError, TrackError;
    };

    interface StreamManager {
        void start_stream(string track_id, Ice::Identity media_render_id)
            throws TrackError, BadIdentity;
        void stop_stream(Ice::Identity media_render_id);
        AudioChunk get_audio_chunk(Ice::Identity media_render_id, int chunk_size)
            throws IOError, StreamError;
    };

    interface MediaServer extends MusicLibrary, StreamManager {};

    interface PlaybackController {
        void play() throws TrackError, StreamError, PlayerError, BadReference;
        idempotent void stop();
    };

    interface ContentManager {
        void load_track(string track_id) throws TrackError, StreamError;
        TrackInfo get_current_track();
    };

    interface RenderConnectivity {
        void bind_media_server(MediaServer* media_server) throws BadReference;
        void unbind_media_server();
    };

    interface MediaRender extends PlaybackController, ContentManager, RenderConnectivity {};
};
