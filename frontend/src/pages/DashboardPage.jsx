import { useState, useEffect, useCallback } from "react";
import { Button } from "../components/ui/button";
import { Music, Disc, Play, Pause, Download, Filter, Calendar, Clock, Loader2, Film, X } from "lucide-react";
import axios from "axios";
import { API } from "../App";
import { toast } from "sonner";
import { MasterDashboardPage } from "./MasterDashboardPage";

const MASTER_ADMIN_MOBILE = "9873945238";

export default function DashboardPage({ user }) {
  if (user?.mobile === MASTER_ADMIN_MOBILE) {
    return <MasterDashboardPage user={user} />;
  }

  return <UserDashboardContent user={user} />;
}

function UserDashboardContent({ user }) {
  const [filter, setFilter] = useState("all");
  const [data, setData] = useState({ songs: [], albums: [] });
  const [loading, setLoading] = useState(true);
  const [playingTrack, setPlayingTrack] = useState(null);
  const [audioRef, setAudioRef] = useState(null);
  const [expandedAlbum, setExpandedAlbum] = useState(null);
  const [generatingVideo, setGeneratingVideo] = useState({});
  const [downloadingAlbum, setDownloadingAlbum] = useState({});
  const [videoModal, setVideoModal] = useState(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/dashboard/${user.id}`);
      // Sort songs by created_at descending (newest first)
      const sortedSongs = (response.data.songs || []).sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      // Sort albums by created_at descending (newest first)
      const sortedAlbums = (response.data.albums || []).sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      ).map((album) => ({
        ...album,
        songs: (album.songs || []).sort(
          (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)
        ),
      }));
      setData({ songs: sortedSongs, albums: sortedAlbums });
    } catch (error) {
      console.error("Failed to fetch dashboard:", error);
    } finally {
      setLoading(false);
    }
  }, [user.id]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const playTrack = useCallback((trackUrl, trackId) => {
    if (audioRef) audioRef.pause();
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

  const formatTime = (s) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;
  
  const formatDate = (dateStr) => new Date(dateStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric"
  });

  const downloadAlbum = async (albumId, albumTitle) => {
    try {
      setDownloadingAlbum((prev) => ({ ...prev, [albumId]: true }));
      const response = await axios.get(`${API}/albums/${albumId}/download?user_id=${user.id}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${albumTitle}.zip`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("Album downloaded successfully!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to download album");
      console.error("Download error:", error);
    } finally {
      setDownloadingAlbum((prev) => ({ ...prev, [albumId]: false }));
    }
  };

  const generateAlbumVideos = async (albumId) => {
    try {
      setGeneratingVideo((prev) => ({ ...prev, [albumId]: true }));
      const response = await axios.post(`${API}/albums/${albumId}/generate-videos?user_id=${user.id}`);
      
      // Refresh data to show video URLs
      await fetchDashboard();
      
      const msg = response.data?.message || `Generated videos for ${response.data.total_videos_generated} songs!`;
      toast.success(msg, { duration: 5000 });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to generate videos");
      console.error("Video generation error:", error);
    } finally {
      setGeneratingVideo((prev) => ({ ...prev, [albumId]: false }));
    }
  };

  const generateSongVideo = async (songId) => {
    try {
      setGeneratingVideo((prev) => ({ ...prev, [songId]: true }));
      const response = await axios.post(`${API}/songs/${songId}/generate-video?user_id=${user.id}`);
      
      await fetchDashboard();
      const msg = response.data?.message || "Video generated successfully!";
      toast.success(msg, response.data?.status === "processing" ? { duration: 5000 } : {});
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to generate video");
      console.error("Video generation error:", error);
    } finally {
      setGeneratingVideo((prev) => ({ ...prev, [songId]: false }));
    }
  };

  const totalSongs = data.songs.length;
  const totalAlbums = data.albums.length;
  const totalTracks = totalSongs + data.albums.reduce((acc, a) => acc + (a.songs?.length || 0), 0);

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
    <div className="min-h-screen p-6 lg:p-10" data-testid="dashboard-page">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <h1 className="font-display text-3xl lg:text-4xl font-bold tracking-tight mb-2">Your Dashboard</h1>
          <p className="text-muted-foreground">All your created music in one place</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-10">
          {[
            { icon: Music, label: "Singles", value: totalSongs, color: "from-primary/20 to-primary/5" },
            { icon: Disc, label: "Albums", value: totalAlbums, color: "from-blue-500/20 to-blue-500/5" },
            { icon: Clock, label: "Total Tracks", value: totalTracks, color: "from-purple-500/20 to-purple-500/5" },
          ].map((stat, i) => (
            <div
              key={i}
              className="p-6 rounded-2xl glass card-hover"
              data-testid={`${stat.label.toLowerCase()}-stat`}
            >
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center`}>
                  <stat.icon className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <p className="text-3xl font-bold font-display">{stat.value}</p>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Filter */}
        <div className="flex items-center gap-3 mb-8" data-testid="filter-section">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <div className="flex gap-2">
            {["all", "songs", "albums"].map((f) => (
              <Button
                key={f}
                variant={filter === f ? "default" : "ghost"}
                size="sm"
                onClick={() => setFilter(f)}
                className={`rounded-full ${filter === f ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}
                data-testid={`filter-${f}`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        {/* Empty State */}
        {totalSongs === 0 && totalAlbums === 0 && (
          <div className="text-center py-20" data-testid="empty-state">
            <div className="w-20 h-20 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-6">
              <Music className="w-10 h-10 text-muted-foreground" />
            </div>
            <h3 className="text-2xl font-semibold mb-3">No music yet</h3>
            <p className="text-muted-foreground mb-8 max-w-md mx-auto">
              Create your first track and it will appear here. Let's make some music!
            </p>
            <Button
              onClick={() => window.location.href = "/create"}
              className="btn-primary glow-primary-sm rounded-full h-12 px-8"
              data-testid="create-first-btn"
            >
              <Music className="w-4 h-4 mr-2" />
              Create Your First Track
            </Button>
          </div>
        )}

        {/* Songs */}
        {(filter === "all" || filter === "songs") && data.songs.length > 0 && (
          <div className="mb-12" data-testid="songs-section">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Music className="w-4 h-4 text-primary" />
              </div>
              Singles
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {data.songs.map((song) => (
                <div
                  key={song.id}
                  className="group rounded-2xl glass card-hover overflow-hidden"
                  data-testid={`song-card-${song.id}`}
                >
                  {/* Cover */}
                  <div className="relative aspect-square">
                    <img src={song.cover_art_url} alt={song.title} className="w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                    <button
                      onClick={() => playTrack(song.audio_url, song.id)}
                      className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      data-testid={`play-song-${song.id}`}
                    >
                      <div className="w-16 h-16 rounded-full bg-primary/90 flex items-center justify-center shadow-lg glow-primary">
                        {playingTrack === song.id ? <Pause className="w-7 h-7 text-primary-foreground" /> : <Play className="w-7 h-7 text-primary-foreground ml-1" />}
                      </div>
                    </button>
                    {/* Duration badge */}
                    <div className="absolute bottom-3 right-3 px-2 py-1 rounded-md bg-black/50 backdrop-blur text-xs font-mono">
                      {formatTime(song.duration_seconds)}
                    </div>
                  </div>

                  {/* Info */}
                  <div className="p-5">
                    <h3 className="font-semibold truncate mb-1">{song.title}</h3>
                    {song.lyrics && <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{song.lyrics}</p>}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
                      <Calendar className="w-3 h-3" />
                      {formatDate(song.created_at)}
                    </div>
                    <div className="flex flex-wrap gap-1.5 mb-4">
                      {song.genres?.slice(0, 2).map((g) => (
                        <span key={g} className="text-xs px-2 py-0.5 rounded-full bg-secondary">{g}</span>
                      ))}
                    </div>
                    {/* Accuracy Percentage */}
                    {song.accuracy_percentage && (
                      <div className="mb-4 p-2.5 rounded-lg bg-gradient-to-r from-primary/10 to-blue-500/10">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-primary">Match Accuracy</span>
                          <span className="text-xs font-bold text-primary">{song.accuracy_percentage}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-primary to-blue-500 transition-all duration-300"
                            style={{ width: `${song.accuracy_percentage}%` }}
                          />
                        </div>
                      </div>
                    )}
                    <div className="flex gap-2">
                      {song.video_url ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="flex-1 gap-2 h-10"
                          onClick={() => setVideoModal({ url: song.video_url, title: song.title, thumbnail: song.video_thumbnail })}
                          data-testid={`watch-video-song-${song.id}`}
                        >
                          <Film className="w-4 h-4" />
                          Watch Video
                        </Button>
                      ) : song.video_status === "processing" ? (
                        <Button size="sm" variant="ghost" className="flex-1 gap-2 h-10" disabled>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Processing...
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="flex-1 gap-2 h-10"
                          onClick={() => generateSongVideo(song.id)}
                          disabled={generatingVideo[song.id]}
                          data-testid={`generate-video-song-${song.id}`}
                        >
                          {generatingVideo[song.id] ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Film className="w-4 h-4" />
                          )}
                          {generatingVideo[song.id] ? "Creating..." : "Video"}
                        </Button>
                      )}
                      <a
                        href={song.audio_url}
                        download
                        className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-secondary hover:bg-secondary/80 transition-colors text-sm font-medium"
                        data-testid={`download-song-${song.id}`}
                      >
                        <Download className="w-4 h-4" />
                        Download
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Albums */}
        {(filter === "all" || filter === "albums") && data.albums.length > 0 && (
          <div data-testid="albums-section">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Disc className="w-4 h-4 text-blue-500" />
              </div>
              Albums
            </h2>
            <div className="space-y-4">
              {data.albums.map((album) => (
                <div
                  key={album.id}
                  className="rounded-2xl glass overflow-hidden"
                  data-testid={`album-card-${album.id}`}
                >
                  {/* Header */}
                  <div className="p-5">
                    <button
                      onClick={() => setExpandedAlbum(expandedAlbum === album.id ? null : album.id)}
                      className="w-full flex items-center gap-5 hover:opacity-80 transition-opacity text-left"
                      data-testid={`expand-album-${album.id}`}
                    >
                      <img src={album.cover_art_url} alt={album.title} className="w-20 h-20 rounded-xl object-cover shadow-lg flex-shrink-0" />
                      <div className="flex-1 text-left">
                        <h3 className="font-semibold text-lg">{album.title}</h3>
                        <p className="text-sm text-muted-foreground">
                          {album.songs?.length || 0} tracks • {formatDate(album.created_at)}
                        </p>
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {album.genres?.slice(0, 3).map((g) => (
                            <span key={g} className="text-xs px-2 py-0.5 rounded-full bg-secondary">{g}</span>
                          ))}
                        </div>
                      </div>
                      <div className={`text-muted-foreground transition-transform ${expandedAlbum === album.id ? "rotate-180" : ""}`}>
                        ▼
                      </div>
                    </button>

                    {/* Action Buttons */}
                    <div className="flex gap-2 mt-4">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="flex-1 gap-2"
                        onClick={() => downloadAlbum(album.id, album.title)}
                        disabled={downloadingAlbum[album.id]}
                        data-testid={`download-album-${album.id}`}
                      >
                        {downloadingAlbum[album.id] ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Download className="w-4 h-4" />
                        )}
                        {downloadingAlbum[album.id] ? "Downloading..." : "Download All"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="flex-1 gap-2"
                        onClick={() => generateAlbumVideos(album.id)}
                        disabled={generatingVideo[album.id]}
                        data-testid={`generate-videos-album-${album.id}`}
                      >
                        {generatingVideo[album.id] ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Film className="w-4 h-4" />
                        )}
                        {generatingVideo[album.id] ? "Generating..." : "Generate Videos"}
                      </Button>
                    </div>
                  </div>

                  {/* Tracks */}
                  {expandedAlbum === album.id && (
                    <div className="border-t border-white/5 animate-fade-in" data-testid={`album-tracks-${album.id}`}>
                      {album.songs?.map((track, i) => (
                        <div
                          key={track.id}
                          className="px-5 py-4 hover:bg-white/[0.02] transition-colors border-b border-white/5 last:border-b-0"
                        >
                          <div className="flex items-start gap-4">
                            <span className="w-8 text-center text-muted-foreground font-mono text-sm pt-2">{i + 1}</span>
                            <button
                              onClick={() => playTrack(track.audio_url, track.id)}
                              className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center hover:bg-primary/20 transition-colors flex-shrink-0 mt-1"
                              data-testid={`play-track-${track.id}`}
                            >
                              {playingTrack === track.id ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                            </button>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{track.title}</p>
                              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground mt-1">
                                <span>{formatDate(track.created_at || album.created_at)}</span>
                                <span>•</span>
                                <span className="font-mono">{formatTime(track.duration_seconds || 0)}</span>
                                {track.vocal_languages?.length > 0 && (
                                  <>
                                    <span>•</span>
                                    <span>{track.vocal_languages.join(", ")}</span>
                                  </>
                                )}
                              </div>
                              {track.genres?.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-2">
                                  {track.genres.slice(0, 4).map((genre) => (
                                    <span key={genre} className="text-[10px] px-2 py-0.5 rounded-full bg-secondary">
                                      {genre}
                                    </span>
                                  ))}
                                </div>
                              )}
                              {track.lyrics && (
                                <p className="text-xs text-muted-foreground line-clamp-2 mt-2">{track.lyrics}</p>
                              )}
                            </div>
                            <div className="flex items-center gap-1 flex-shrink-0">
                              {track.video_url ? (
                                <button
                                  onClick={() => setVideoModal({ url: track.video_url, title: track.title, thumbnail: track.video_thumbnail })}
                                  className="p-2 rounded-lg hover:bg-white/5 transition-colors"
                                  title="Watch video"
                                  data-testid={`watch-video-track-${track.id}`}
                                >
                                  <Film className="w-4 h-4 text-primary" />
                                </button>
                              ) : track.video_status === "processing" ? (
                                <button className="p-2 rounded-lg" title="Processing..." disabled>
                                  <Loader2 className="w-4 h-4 text-muted-foreground animate-spin" />
                                </button>
                              ) : (
                                <button
                                  onClick={() => generateSongVideo(track.id)}
                                  className="p-2 rounded-lg hover:bg-white/5 transition-colors"
                                  title="Generate video"
                                  disabled={generatingVideo[track.id]}
                                  data-testid={`generate-video-track-${track.id}`}
                                >
                                  {generatingVideo[track.id] ? (
                                    <Loader2 className="w-4 h-4 text-muted-foreground animate-spin" />
                                  ) : (
                                    <Film className="w-4 h-4 text-muted-foreground hover:text-primary" />
                                  )}
                                </button>
                              )}
                              <a
                                href={track.audio_url}
                                download
                                className="p-2 rounded-lg hover:bg-white/5 transition-colors"
                                data-testid={`download-track-${track.id}`}
                              >
                                <Download className="w-4 h-4 text-muted-foreground" />
                              </a>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Video Modal */}
        {videoModal && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
            onClick={() => setVideoModal(null)}
          >
            <div
              className="relative max-w-4xl w-full bg-card rounded-2xl overflow-hidden shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() => setVideoModal(null)}
                className="absolute top-4 right-4 z-10 p-2 rounded-full bg-black/50 hover:bg-black/70 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
              <div className="p-4 border-b border-white/5">
                <h3 className="font-semibold truncate pr-12">{videoModal.title}</h3>
              </div>
              <video
                src={videoModal.url}
                poster={videoModal.thumbnail}
                controls
                autoPlay
                className="w-full aspect-video bg-black"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export { DashboardPage };
