import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Music, Disc, Download, Filter, Calendar, Clock, Loader2, Film, X, Search, FileText, ChevronDown } from "lucide-react";
import axios from "axios";
import { API } from "../App";
import { toast } from "sonner";
import { MasterDashboardPage } from "./MasterDashboardPage";

const MASTER_ADMIN_MOBILE = "9873945238";

const SORT_OPTIONS = [
  { value: "created_at", label: "Date" },
  { value: "title", label: "Title" },
  { value: "duration_seconds", label: "Duration" },
];

const formatTime = (value) => {
  const seconds = Number(value || 0);
  if (!seconds) return "0:00";
  const mins = Math.floor(seconds / 60);
  const rem = seconds % 60;
  return `${mins}:${String(rem).padStart(2, "0")}`;
};

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const trackMatchesSearch = (track, searchText) => {
  if (!searchText) return true;
  const haystack = [
    track.title,
    track.music_prompt,
    track.artist_inspiration,
    ...(Array.isArray(track.genres) ? track.genres : []),
    ...(Array.isArray(track.vocal_languages) ? track.vocal_languages : []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(searchText.toLowerCase());
};

const compareByField = (a, b, field) => {
  if (field === "created_at") {
    return new Date(a?.created_at || 0).getTime() - new Date(b?.created_at || 0).getTime();
  }
  if (field === "duration_seconds") {
    return Number(a?.duration_seconds || 0) - Number(b?.duration_seconds || 0);
  }
  return String(a?.[field] || "").localeCompare(String(b?.[field] || ""));
};

export default function DashboardPage({ user }) {
  if (user?.mobile === MASTER_ADMIN_MOBILE) {
    return <MasterDashboardPage user={user} />;
  }

  return <UserDashboardContent user={user} />;
}

function UserDashboardContent({ user }) {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  const [data, setData] = useState({ songs: [], albums: [] });
  const [loading, setLoading] = useState(true);
  const [expandedAlbum, setExpandedAlbum] = useState(null);
  const [generatingVideo, setGeneratingVideo] = useState({});
  const [downloadingAlbum, setDownloadingAlbum] = useState({});
  const [mediaModalTrack, setMediaModalTrack] = useState(null);
  const [detailsModal, setDetailsModal] = useState(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/dashboard/${user.id}`);
      const sortedSongs = (response.data.songs || []).sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      const sortedAlbums = (response.data.albums || [])
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .map((album) => ({
          ...album,
          songs: (album.songs || []).sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)),
        }));
      setData({ songs: sortedSongs, albums: sortedAlbums });
    } catch (error) {
      console.error("Failed to fetch dashboard:", error);
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, [user.id]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

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
      toast.success("Album downloaded successfully");
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
      await fetchDashboard();
      const msg = response.data?.message || `Generated videos for ${response.data.total_videos_generated} songs`;
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
      const msg = response.data?.message || "Video generated successfully";
      toast.success(msg, response.data?.status === "processing" ? { duration: 5000 } : {});
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to generate video");
      console.error("Video generation error:", error);
    } finally {
      setGeneratingVideo((prev) => ({ ...prev, [songId]: false }));
    }
  };

  const filteredSongs = useMemo(() => {
    return [...data.songs]
      .filter((song) => trackMatchesSearch(song, search))
      .sort((a, b) => {
        const diff = compareByField(a, b, sortField);
        return sortOrder === "asc" ? diff : -diff;
      });
  }, [data.songs, search, sortField, sortOrder]);

  const filteredAlbums = useMemo(() => {
    return [...data.albums]
      .filter((album) => {
        if (!search) return true;
        const titleMatch = String(album.title || "").toLowerCase().includes(search.toLowerCase());
        const songMatch = (album.songs || []).some((song) => trackMatchesSearch(song, search));
        return titleMatch || songMatch;
      })
      .sort((a, b) => {
        const diff = compareByField(a, b, sortField);
        return sortOrder === "asc" ? diff : -diff;
      });
  }, [data.albums, search, sortField, sortOrder]);

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
        <div className="mb-10">
          <h1 className="font-display text-3xl lg:text-4xl font-bold tracking-tight mb-2">Your Dashboard</h1>
          <p className="text-muted-foreground">All your created music in one place</p>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            { icon: Music, label: "Singles", value: totalSongs, color: "from-primary/20 to-primary/5" },
            { icon: Disc, label: "Albums", value: totalAlbums, color: "from-blue-500/20 to-blue-500/5" },
            { icon: Clock, label: "Total Tracks", value: totalTracks, color: "from-purple-500/20 to-purple-500/5" },
          ].map((stat, i) => (
            <div key={i} className="p-6 rounded-2xl glass card-hover" data-testid={`${stat.label.toLowerCase()}-stat`}>
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

        <div className="glass rounded-2xl p-4 mb-8" data-testid="filter-section">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <Filter className="w-4 h-4 text-muted-foreground" />
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
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="md:col-span-2 relative">
              <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search title, prompt, genre, language..."
                className="pl-9"
              />
            </div>
            <select
              value={sortField}
              onChange={(e) => setSortField(e.target.value)}
              className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value)}
              className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>
        </div>

        {totalSongs === 0 && totalAlbums === 0 && (
          <div className="text-center py-20" data-testid="empty-state">
            <div className="w-20 h-20 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-6">
              <Music className="w-10 h-10 text-muted-foreground" />
            </div>
            <h3 className="text-2xl font-semibold mb-3">No music yet</h3>
            <p className="text-muted-foreground mb-8 max-w-md mx-auto">
              Create your first track and it will appear here.
            </p>
            <Button
              onClick={() => (window.location.href = "/create")}
              className="btn-primary glow-primary-sm rounded-full h-12 px-8"
              data-testid="create-first-btn"
            >
              <Music className="w-4 h-4 mr-2" />
              Create Your First Track
            </Button>
          </div>
        )}

        {(filter === "all" || filter === "songs") && filteredSongs.length > 0 && (
          <div className="mb-12" data-testid="songs-section">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Music className="w-4 h-4 text-primary" />
              </div>
              Singles
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredSongs.map((song) => (
                <div key={song.id} className="rounded-2xl glass card-hover overflow-hidden" data-testid={`song-card-${song.id}`}>
                  <div className="relative aspect-square">
                    <img src={song.cover_art_url} alt={song.title} className="w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                    <div className="absolute bottom-3 right-3 px-2 py-1 rounded-md bg-black/50 backdrop-blur text-xs font-mono">
                      {formatTime(song.duration_seconds)}
                    </div>
                  </div>

                  <div className="p-5">
                    <h3 className="font-semibold truncate mb-1">{song.title}</h3>
                    {song.music_prompt && (
                      <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{song.music_prompt}</p>
                    )}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
                      <Calendar className="w-3 h-3" />
                      {formatDate(song.created_at)}
                    </div>
                    <div className="flex flex-wrap gap-1.5 mb-4">
                      {song.genres?.slice(0, 3).map((g) => (
                        <span key={g} className="text-xs px-2 py-0.5 rounded-full bg-secondary">{g}</span>
                      ))}
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="gap-2 h-10"
                        onClick={() => setMediaModalTrack(song)}
                      >
                        <Music className="w-4 h-4" />
                        Play Media
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="gap-2 h-10"
                        onClick={() => setDetailsModal({ type: "track", data: song })}
                      >
                        <FileText className="w-4 h-4" />
                        See All Details
                      </Button>
                      <a
                        href={`${API}/songs/${song.id}/download?user_id=${user.id}`}
                        className="flex items-center justify-center gap-2 py-2.5 rounded-xl bg-secondary hover:bg-secondary/80 transition-colors text-sm font-medium"
                        data-testid={`download-song-${song.id}`}
                      >
                        <Download className="w-4 h-4" />
                        Audio
                      </a>
                      {song.video_url ? (
                        <a
                          href={`${API}/songs/${song.id}/download-video?user_id=${user.id}`}
                          className="flex items-center justify-center gap-2 py-2.5 rounded-xl bg-secondary hover:bg-secondary/80 transition-colors text-sm font-medium"
                        >
                          <Download className="w-4 h-4" />
                          Video
                        </a>
                      ) : song.video_status === "processing" ? (
                        <Button size="sm" variant="ghost" className="h-10" disabled>
                          <Loader2 className="w-4 h-4 animate-spin" />
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-10 gap-2"
                          onClick={() => generateSongVideo(song.id)}
                          disabled={generatingVideo[song.id]}
                          data-testid={`generate-video-song-${song.id}`}
                        >
                          {generatingVideo[song.id] ? <Loader2 className="w-4 h-4 animate-spin" /> : <Film className="w-4 h-4" />}
                          Video
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(filter === "all" || filter === "albums") && filteredAlbums.length > 0 && (
          <div data-testid="albums-section">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Disc className="w-4 h-4 text-blue-500" />
              </div>
              Albums
            </h2>
            <div className="space-y-4">
              {filteredAlbums.map((album) => (
                <div key={album.id} className="rounded-2xl glass overflow-hidden" data-testid={`album-card-${album.id}`}>
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
                      <ChevronDown className={`text-muted-foreground transition-transform ${expandedAlbum === album.id ? "rotate-180" : ""}`} />
                    </button>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-4">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="gap-2"
                        onClick={() => downloadAlbum(album.id, album.title)}
                        disabled={downloadingAlbum[album.id]}
                        data-testid={`download-album-${album.id}`}
                      >
                        {downloadingAlbum[album.id] ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        {downloadingAlbum[album.id] ? "Downloading" : "Download All"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="gap-2"
                        onClick={() => generateAlbumVideos(album.id)}
                        disabled={generatingVideo[album.id]}
                        data-testid={`generate-videos-album-${album.id}`}
                      >
                        {generatingVideo[album.id] ? <Loader2 className="w-4 h-4 animate-spin" /> : <Film className="w-4 h-4" />}
                        {generatingVideo[album.id] ? "Generating" : "Generate Videos"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="gap-2"
                        onClick={() => setMediaModalTrack({ ...album.songs?.[0], title: `${album.title} (Album Preview)` })}
                        disabled={!album.songs?.length}
                      >
                        <Music className="w-4 h-4" />
                        Play Media
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="gap-2"
                        onClick={() => setDetailsModal({ type: "album", data: album })}
                      >
                        <FileText className="w-4 h-4" />
                        See All Details
                      </Button>
                    </div>
                  </div>

                  {expandedAlbum === album.id && (
                    <div className="border-t border-white/5 animate-fade-in" data-testid={`album-tracks-${album.id}`}>
                      {(album.songs || []).map((track, i) => (
                        <div key={track.id} className="px-5 py-4 hover:bg-white/[0.02] transition-colors border-b border-white/5 last:border-b-0">
                          <div className="flex items-start gap-4">
                            <span className="w-8 text-center text-muted-foreground font-mono text-sm pt-2">{i + 1}</span>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{track.title}</p>
                              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground mt-1">
                                <span>{formatDate(track.created_at || album.created_at)}</span>
                                <span>•</span>
                                <span className="font-mono">{formatTime(track.duration_seconds || 0)}</span>
                              </div>
                              {track.genres?.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-2">
                                  {track.genres.slice(0, 4).map((genre) => (
                                    <span key={genre} className="text-[10px] px-2 py-0.5 rounded-full bg-secondary">{genre}</span>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="grid grid-cols-2 gap-2 w-[220px]">
                              <Button size="sm" variant="ghost" onClick={() => setMediaModalTrack(track)}>
                                Play
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setDetailsModal({ type: "track", data: track })}>
                                Details
                              </Button>
                              <a href={`${API}/songs/${track.id}/download?user_id=${user.id}`} className="inline-flex items-center justify-center text-xs rounded-md bg-secondary h-9 hover:bg-secondary/80">
                                Audio
                              </a>
                              {track.video_url ? (
                                <a href={`${API}/songs/${track.id}/download-video?user_id=${user.id}`} className="inline-flex items-center justify-center text-xs rounded-md bg-secondary h-9 hover:bg-secondary/80">
                                  Video
                                </a>
                              ) : (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => generateSongVideo(track.id)}
                                  disabled={generatingVideo[track.id]}
                                >
                                  {generatingVideo[track.id] ? <Loader2 className="w-3 h-3 animate-spin" /> : "Video"}
                                </Button>
                              )}
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

        {mediaModalTrack && (
          <TrackMediaModal
            track={mediaModalTrack}
            userId={user.id}
            onClose={() => setMediaModalTrack(null)}
          />
        )}

        {detailsModal && (
          <DetailsModal
            record={detailsModal.data}
            type={detailsModal.type}
            onClose={() => setDetailsModal(null)}
          />
        )}
      </div>
    </div>
  );
}

function TrackMediaModal({ track, userId, onClose }) {
  const audioRef = useRef(null);
  const durationLimit = Number(track?.duration_seconds || 0);

  const handleAudioTimeUpdate = () => {
    if (!audioRef.current || !durationLimit) return;
    if (audioRef.current.currentTime >= durationLimit) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div className="relative max-w-3xl w-full bg-card rounded-2xl overflow-hidden shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="absolute top-4 right-4 z-10 p-2 rounded-full bg-black/50 hover:bg-black/70 transition-colors">
          <X className="w-5 h-5" />
        </button>
        <div className="p-4 border-b border-white/5">
          <h3 className="font-semibold truncate pr-12">{track.title}</h3>
          <p className="text-xs text-muted-foreground mt-1">Track duration: {formatTime(track.duration_seconds)}</p>
        </div>

        <div className="p-4 space-y-4 max-h-[75vh] overflow-y-auto">
          {track.audio_url && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Audio Player</p>
              <audio
                ref={audioRef}
                src={track.audio_url}
                controls
                onTimeUpdate={handleAudioTimeUpdate}
                className="w-full"
              />
              <a
                href={`${API}/songs/${track.id}/download?user_id=${userId}`}
                className="inline-flex items-center gap-2 text-sm px-3 py-2 rounded-lg bg-secondary hover:bg-secondary/80"
              >
                <Download className="w-4 h-4" />
                Download Audio
              </a>
            </div>
          )}

          {track.video_url ? (
            <div className="space-y-2">
              <p className="text-sm font-medium">Video Player</p>
              <video src={track.video_url} poster={track.video_thumbnail} controls className="w-full aspect-video bg-black rounded-xl" />
              <a
                href={`${API}/songs/${track.id}/download-video?user_id=${userId}`}
                className="inline-flex items-center gap-2 text-sm px-3 py-2 rounded-lg bg-secondary hover:bg-secondary/80"
              >
                <Download className="w-4 h-4" />
                Download Video
              </a>
            </div>
          ) : (
            <div className="rounded-lg border border-white/10 bg-secondary/30 p-3 text-sm text-muted-foreground">
              Video is not ready for this track yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailsModal({ record, type, onClose }) {
  const fields = [
    ["Title", record?.title],
    ["Music Prompt", record?.music_prompt],
    ["Genres", Array.isArray(record?.genres) ? record.genres.join(", ") : "-"],
    ["Duration", type === "track" ? formatTime(record?.duration_seconds) : `${record?.songs?.length || 0} tracks`],
    ["Vocal Languages", Array.isArray(record?.vocal_languages) ? record.vocal_languages.join(", ") : "-"],
    ["Lyrics", record?.lyrics],
    ["Artist Inspiration", record?.artist_inspiration],
    ["Video Style", record?.video_style],
    ["Generation Provider", record?.generation_provider],
    ["Created", formatDate(record?.created_at)],
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div className="relative max-w-4xl w-full bg-card rounded-2xl overflow-hidden shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="absolute top-4 right-4 z-10 p-2 rounded-full bg-black/50 hover:bg-black/70 transition-colors">
          <X className="w-5 h-5" />
        </button>
        <div className="p-4 border-b border-white/5">
          <h3 className="font-semibold truncate pr-12">See All Details: {record?.title || "Untitled"}</h3>
          <p className="text-xs text-muted-foreground mt-1">{type === "album" ? "Album Details" : "Track Details"}</p>
        </div>

        <div className="p-4 max-h-[75vh] overflow-y-auto space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {fields.map(([label, value]) => (
              <div key={label} className="rounded-lg border border-white/10 bg-secondary/20 p-3">
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">{label}</p>
                <p className="text-sm whitespace-pre-wrap break-words">{value || "-"}</p>
              </div>
            ))}
          </div>

          {type === "album" && Array.isArray(record?.songs) && record.songs.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-semibold">Album Songs (All Inputs)</p>
              {record.songs.map((song, idx) => (
                <div key={song.id || `${idx}-${song.title}`} className="rounded-lg border border-white/10 bg-secondary/20 p-3">
                  <p className="text-sm font-medium">{idx + 1}. {song.title || `Track ${idx + 1}`}</p>
                  <p className="text-xs text-muted-foreground mt-1">Prompt: {song.music_prompt || "-"}</p>
                  <p className="text-xs text-muted-foreground">Genres: {(song.genres || []).join(", ") || "-"}</p>
                  <p className="text-xs text-muted-foreground">Languages: {(song.vocal_languages || []).join(", ") || "-"}</p>
                  <p className="text-xs text-muted-foreground">Duration: {formatTime(song.duration_seconds || 0)}</p>
                  <p className="text-xs text-muted-foreground line-clamp-3">Lyrics: {song.lyrics || "-"}</p>
                </div>
              ))}
            </div>
          )}

          <div className="rounded-lg border border-white/10 bg-black/30 p-3">
            <p className="text-sm font-semibold mb-2">Raw Record (Complete)</p>
            <pre className="text-xs text-muted-foreground overflow-x-auto whitespace-pre-wrap break-all">
              {JSON.stringify(record, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}

export { DashboardPage };
