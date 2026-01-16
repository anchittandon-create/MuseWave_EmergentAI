import { useState, useEffect, useCallback } from "react";
import { Button } from "../components/ui/button";
import { Music, Disc, Play, Pause, Download, Filter } from "lucide-react";
import axios from "axios";
import { API } from "../App";

export default function DashboardPage({ user }) {
  const [filter, setFilter] = useState("all");
  const [data, setData] = useState({ songs: [], albums: [] });
  const [loading, setLoading] = useState(true);
  const [playingTrack, setPlayingTrack] = useState(null);
  const [audioRef, setAudioRef] = useState(null);
  const [expandedAlbum, setExpandedAlbum] = useState(null);

  useEffect(() => {
    fetchDashboard();
  }, [user.id]);

  const fetchDashboard = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/${user.id}`);
      setData(response.data);
    } catch (error) {
      console.error("Failed to fetch dashboard:", error);
    } finally {
      setLoading(false);
    }
  };

  const playTrack = useCallback((trackUrl, trackId) => {
    if (audioRef) {
      audioRef.pause();
    }
    if (playingTrack === trackId) {
      setPlayingTrack(null);
      return;
    }
    const audio = new Audio(trackUrl);
    audio.play();
    audio.onended = () => setPlayingTrack(null);
    setAudioRef(audio);
    setPlayingTrack(trackId);
  }, [audioRef, playingTrack]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const totalSongs = data.songs.length;
  const totalAlbums = data.albums.length;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-muted-foreground">Loading your music...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8" data-testid="dashboard-page">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Your Dashboard</h1>
          <p className="text-muted-foreground">
            All your created music in one place
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="p-6 rounded-xl bg-card border border-white/5" data-testid="songs-stat">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Music className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalSongs}</p>
                <p className="text-sm text-muted-foreground">Standalone Songs</p>
              </div>
            </div>
          </div>
          <div className="p-6 rounded-xl bg-card border border-white/5" data-testid="albums-stat">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Disc className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalAlbums}</p>
                <p className="text-sm text-muted-foreground">Albums</p>
              </div>
            </div>
          </div>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2 mb-6" data-testid="filter-section">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <div className="flex gap-2">
            {["all", "songs", "albums"].map((f) => (
              <Button
                key={f}
                variant={filter === f ? "default" : "ghost"}
                size="sm"
                onClick={() => setFilter(f)}
                className={filter === f ? "bg-primary text-primary-foreground" : ""}
                data-testid={`filter-${f}`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        {/* Empty State */}
        {totalSongs === 0 && totalAlbums === 0 && (
          <div className="text-center py-16" data-testid="empty-state">
            <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-6">
              <Music className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-xl font-semibold mb-2">No music yet</h3>
            <p className="text-muted-foreground mb-6">
              Create your first track to see it here
            </p>
            <Button
              onClick={() => window.location.href = "/create"}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
              data-testid="create-first-btn"
            >
              Create Music
            </Button>
          </div>
        )}

        {/* Songs Section */}
        {(filter === "all" || filter === "songs") && data.songs.length > 0 && (
          <div className="mb-12" data-testid="songs-section">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Music className="w-5 h-5 text-primary" />
              Songs
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.songs.map((song) => (
                <div
                  key={song.id}
                  className="group p-4 rounded-xl bg-card border border-white/5 hover:border-white/10 transition-all"
                  data-testid={`song-card-${song.id}`}
                >
                  <div className="relative aspect-square mb-4 rounded-lg overflow-hidden">
                    <img
                      src={song.cover_art_url}
                      alt={song.title}
                      className="w-full h-full object-cover"
                    />
                    <button
                      onClick={() => playTrack(song.audio_url, song.id)}
                      className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      data-testid={`play-song-${song.id}`}
                    >
                      {playingTrack === song.id ? (
                        <Pause className="w-12 h-12 text-white" />
                      ) : (
                        <Play className="w-12 h-12 text-white" />
                      )}
                    </button>
                  </div>
                  <h3 className="font-semibold truncate mb-1">{song.title}</h3>
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span className="font-mono">{formatTime(song.duration_seconds)}</span>
                    <span>{formatDate(song.created_at)}</span>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {song.genres?.slice(0, 3).map((genre) => (
                      <span
                        key={genre}
                        className="text-xs px-2 py-0.5 rounded-full bg-secondary text-muted-foreground"
                      >
                        {genre}
                      </span>
                    ))}
                  </div>
                  <a
                    href={song.audio_url}
                    download
                    className="mt-4 flex items-center justify-center gap-2 w-full py-2 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors text-sm"
                    data-testid={`download-song-${song.id}`}
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Albums Section */}
        {(filter === "all" || filter === "albums") && data.albums.length > 0 && (
          <div data-testid="albums-section">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Disc className="w-5 h-5 text-primary" />
              Albums
            </h2>
            <div className="space-y-4">
              {data.albums.map((album) => (
                <div
                  key={album.id}
                  className="rounded-xl bg-card border border-white/5 overflow-hidden"
                  data-testid={`album-card-${album.id}`}
                >
                  {/* Album Header */}
                  <button
                    onClick={() => setExpandedAlbum(expandedAlbum === album.id ? null : album.id)}
                    className="w-full p-4 flex items-center gap-4 hover:bg-white/5 transition-colors"
                    data-testid={`expand-album-${album.id}`}
                  >
                    <img
                      src={album.cover_art_url}
                      alt={album.title}
                      className="w-20 h-20 rounded-lg object-cover"
                    />
                    <div className="flex-1 text-left">
                      <h3 className="font-semibold text-lg">{album.title}</h3>
                      <p className="text-sm text-muted-foreground">
                        {album.songs?.length || 0} tracks • {formatDate(album.created_at)}
                      </p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {album.genres?.slice(0, 3).map((genre) => (
                          <span
                            key={genre}
                            className="text-xs px-2 py-0.5 rounded-full bg-secondary text-muted-foreground"
                          >
                            {genre}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="text-muted-foreground">
                      {expandedAlbum === album.id ? "▲" : "▼"}
                    </div>
                  </button>

                  {/* Album Tracks */}
                  {expandedAlbum === album.id && (
                    <div className="border-t border-white/5 animate-fade-in" data-testid={`album-tracks-${album.id}`}>
                      {album.songs?.map((track, index) => (
                        <div
                          key={track.id}
                          className="flex items-center gap-4 p-4 hover:bg-white/5 transition-colors border-b border-white/5 last:border-b-0"
                        >
                          <span className="w-8 text-center text-muted-foreground font-mono text-sm">
                            {index + 1}
                          </span>
                          <button
                            onClick={() => playTrack(track.audio_url, track.id)}
                            className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center hover:bg-primary/20 transition-colors"
                            data-testid={`play-track-${track.id}`}
                          >
                            {playingTrack === track.id ? (
                              <Pause className="w-4 h-4" />
                            ) : (
                              <Play className="w-4 h-4" />
                            )}
                          </button>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium truncate">{track.title}</p>
                          </div>
                          <span className="text-sm text-muted-foreground font-mono">
                            {formatTime(track.duration_seconds)}
                          </span>
                          <a
                            href={track.audio_url}
                            download
                            className="p-2 rounded-lg hover:bg-white/5 transition-colors"
                            data-testid={`download-track-${track.id}`}
                          >
                            <Download className="w-4 h-4 text-muted-foreground" />
                          </a>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export { DashboardPage };
