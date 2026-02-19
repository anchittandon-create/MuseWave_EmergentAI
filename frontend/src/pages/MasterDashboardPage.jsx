import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { API } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { toast } from "sonner";
import { Shield, Users, Music, Disc, Calendar, Search, PlayCircle, Download, FileText, X, Play, Pause, Rewind, FastForward } from "lucide-react";

const TAB_CONFIG = [
  { id: "tracks", label: "All Tracks" },
  { id: "albums", label: "Albums" },
  { id: "songs", label: "Songs" },
];

const SORT_FIELD_OPTIONS = [
  { value: "created_at", label: "Date" },
  { value: "user_name", label: "User Name" },
  { value: "user_mobile", label: "Mobile" },
  { value: "title", label: "Track/Album Name" },
  { value: "album_title", label: "Album Name" },
  { value: "duration_seconds", label: "Duration" },
  { value: "song_count", label: "Track Count" },
];

const FILTER_ALL = "__all__";
const NO_ALBUM = "__no_album__";
const MEDIA_PREVIEW_FALLBACK = "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=240&h=240&fit=crop";

const toDateInputValue = (value) => {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString().slice(0, 10);
};

const formatDate = (value) => {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const formatDuration = (seconds) => {
  const value = Number(seconds || 0);
  if (!value) return "-";
  const mins = Math.floor(value / 60);
  const rem = value % 60;
  return `${mins}:${String(rem).padStart(2, "0")}`;
};

const recordContains = (record, searchText) => {
  if (!searchText) return true;
  const haystack = [
    record.title,
    record.album_title,
    record.user_name,
    record.user_mobile,
    record.music_prompt,
    record.artist_inspiration,
    ...(Array.isArray(record.genres) ? record.genres : []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(searchText.toLowerCase());
};

const compareValues = (a, b, field) => {
  if (field === "created_at") {
    return new Date(a || 0).getTime() - new Date(b || 0).getTime();
  }
  if (field === "duration_seconds" || field === "song_count") {
    return Number(a || 0) - Number(b || 0);
  }
  return String(a || "").localeCompare(String(b || ""));
};

const uniqueSorted = (values) =>
  Array.from(
    new Set(
      (values || [])
        .map((value) => String(value || "").trim())
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b));

const sanitizeFilename = (value) => {
  const base = String(value || "media")
    .replace(/[\\/:*?"<>|]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return base || "media";
};

const extensionFromUrl = (url, fallback) => {
  try {
    const clean = String(url || "").split("?")[0];
    const ext = clean.split(".").pop()?.toLowerCase();
    if (ext && /^[a-z0-9]{2,5}$/.test(ext)) return ext;
  } catch (_) {
    // noop
  }
  return fallback;
};

const buildSongDownloadUrl = (record, kind = "audio", ownerId) => {
  const songId = record?.id;
  const userId = ownerId || record?.user_id;
  if (!songId || !userId) return null;
  if (kind === "video") {
    return `${API}/songs/${songId}/download-video?user_id=${encodeURIComponent(userId)}`;
  }
  return `${API}/songs/${songId}/download?user_id=${encodeURIComponent(userId)}`;
};

const forceDownloadFile = async (url, filenameFallback) => {
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Download failed");
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filenameFallback;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(objectUrl);
};

const downloadRecordMedia = async (record, kind = "audio", ownerId) => {
  const directUrl = kind === "video" ? record?.video_url : record?.audio_url;
  const proxyUrl = buildSongDownloadUrl(record, kind, ownerId);
  const sourceUrl = proxyUrl || directUrl;
  if (!sourceUrl) {
    toast.error(`${kind === "video" ? "Video" : "Audio"} is not available`);
    return;
  }
  const ext = extensionFromUrl(directUrl || sourceUrl, kind === "video" ? "mp4" : "mp3");
  const filename = `${sanitizeFilename(record?.title || "track")}.${ext}`;
  try {
    await forceDownloadFile(sourceUrl, filename);
    toast.success(`${kind === "video" ? "Video" : "Audio"} download started`);
  } catch (error) {
    toast.error(error?.message || `Failed to download ${kind}`);
  }
};

export default function MasterDashboardPage({ user }) {
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("tracks");
  const [dashboard, setDashboard] = useState({ summary: {}, tracks: [], songs: [], albums: [], users: [] });
  const [search, setSearch] = useState("");
  const [nameFilter, setNameFilter] = useState(FILTER_ALL);
  const [mobileFilter, setMobileFilter] = useState(FILTER_ALL);
  const [titleFilter, setTitleFilter] = useState(FILTER_ALL);
  const [albumFilter, setAlbumFilter] = useState(FILTER_ALL);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [sortField, setSortField] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [mediaModalRecord, setMediaModalRecord] = useState(null);
  const [detailsModal, setDetailsModal] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/dashboard/master/${user.id}`);
      setDashboard(res.data || { summary: {}, tracks: [], songs: [], albums: [], users: [] });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to load master dashboard");
    } finally {
      setLoading(false);
    }
  }, [user.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const baseRecords = useMemo(() => (Array.isArray(dashboard[tab]) ? dashboard[tab] : []), [dashboard, tab]);

  const filterOptions = useMemo(() => {
    const names = uniqueSorted(baseRecords.map((record) => record.user_name));
    const mobiles = uniqueSorted(baseRecords.map((record) => record.user_mobile));
    const titles = uniqueSorted(baseRecords.map((record) => record.title));
    const albums = baseRecords.map((record) => {
      if (tab === "albums") return record.title || "";
      return record.album_title || NO_ALBUM;
    });
    const uniqueAlbums = uniqueSorted(albums).map((value) =>
      value === NO_ALBUM ? { value: NO_ALBUM, label: "Singles / No Album" } : { value, label: value }
    );

    return {
      names,
      mobiles,
      titles,
      albums: uniqueAlbums,
    };
  }, [baseRecords, tab]);

  const dateBounds = useMemo(() => {
    const validDates = baseRecords
      .map((record) => new Date(record.created_at))
      .filter((date) => !Number.isNaN(date.getTime()))
      .sort((a, b) => a.getTime() - b.getTime());

    if (!validDates.length) {
      return { min: "", max: "" };
    }

    return {
      min: toDateInputValue(validDates[0].toISOString()),
      max: toDateInputValue(validDates[validDates.length - 1].toISOString()),
    };
  }, [baseRecords]);

  useEffect(() => {
    setNameFilter(FILTER_ALL);
    setMobileFilter(FILTER_ALL);
    setTitleFilter(FILTER_ALL);
    setAlbumFilter(FILTER_ALL);
    setFromDate(dateBounds.min);
    setToDate(dateBounds.max);
  }, [tab, dateBounds.min, dateBounds.max]);

  const records = useMemo(() => {
    const filtered = baseRecords.filter((record) => {
      if (!recordContains(record, search)) return false;
      if (nameFilter !== FILTER_ALL && String(record.user_name || "") !== nameFilter) return false;
      if (mobileFilter !== FILTER_ALL && String(record.user_mobile || "") !== mobileFilter) return false;
      if (titleFilter !== FILTER_ALL && String(record.title || "") !== titleFilter) return false;

      const resolvedAlbum = tab === "albums" ? String(record.title || "") : String(record.album_title || NO_ALBUM);
      if (albumFilter !== FILTER_ALL && resolvedAlbum !== albumFilter) return false;

      const createdAt = record.created_at ? new Date(record.created_at) : null;
      if (fromDate) {
        const from = new Date(`${fromDate}T00:00:00`);
        if (!createdAt || createdAt < from) return false;
      }
      if (toDate) {
        const to = new Date(`${toDate}T23:59:59`);
        if (!createdAt || createdAt > to) return false;
      }

      return true;
    });

    return filtered.sort((a, b) => {
      const valueA = a?.[sortField];
      const valueB = b?.[sortField];
      const diff = compareValues(valueA, valueB, sortField);
      return sortOrder === "asc" ? diff : -diff;
    });
  }, [baseRecords, tab, search, nameFilter, mobileFilter, titleFilter, albumFilter, fromDate, toDate, sortField, sortOrder]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted-foreground">Loading master dashboard...</div>
      </div>
    );
  }

  const summary = dashboard.summary || {};

  return (
    <div className="min-h-screen p-6 lg:p-10" data-testid="master-dashboard-page">
      <div className="max-w-[1280px] mx-auto">
        <div className="mb-8 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="font-display text-3xl lg:text-4xl font-bold tracking-tight mb-2 flex items-center gap-3">
              <Shield className="w-8 h-8 text-primary" />
              Master Dashboard
            </h1>
            <p className="text-muted-foreground">
              Global data control for admin mobile {user.mobile}. View all users, tracks, songs, and albums.
            </p>
          </div>
          <Button onClick={loadData} className="gap-2" data-testid="master-refresh-btn">
            Refresh Data
          </Button>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="glass rounded-2xl p-4">
            <div className="text-xs text-muted-foreground mb-1">Total Users</div>
            <div className="text-2xl font-semibold flex items-center gap-2"><Users className="w-5 h-5 text-primary" />{summary.total_users || 0}</div>
          </div>
          <div className="glass rounded-2xl p-4">
            <div className="text-xs text-muted-foreground mb-1">Total Tracks</div>
            <div className="text-2xl font-semibold flex items-center gap-2"><Music className="w-5 h-5 text-primary" />{summary.total_tracks || 0}</div>
          </div>
          <div className="glass rounded-2xl p-4">
            <div className="text-xs text-muted-foreground mb-1">Singles</div>
            <div className="text-2xl font-semibold">{summary.total_singles || 0}</div>
          </div>
          <div className="glass rounded-2xl p-4">
            <div className="text-xs text-muted-foreground mb-1">Albums</div>
            <div className="text-2xl font-semibold flex items-center gap-2"><Disc className="w-5 h-5 text-primary" />{summary.total_albums || 0}</div>
          </div>
        </div>

        <div className="glass rounded-2xl p-5 mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-end">
            <div className="lg:col-span-5">
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Search</Label>
              <div className="relative mt-1">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" placeholder="Track, album, user, mobile..." />
              </div>
            </div>
            <div className="lg:col-span-3">
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Sort By</Label>
              <select
                className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={sortField}
                onChange={(e) => setSortField(e.target.value)}
              >
                {SORT_FIELD_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div className="lg:col-span-2">
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Order</Label>
              <select
                className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
              >
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
            <div className="lg:col-span-2 grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowAdvancedFilters((prev) => !prev)}
                className="w-full"
              >
                {showAdvancedFilters ? "Less" : "More"}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => {
                  setSearch("");
                  setNameFilter(FILTER_ALL);
                  setMobileFilter(FILTER_ALL);
                  setTitleFilter(FILTER_ALL);
                  setAlbumFilter(FILTER_ALL);
                  setFromDate(dateBounds.min);
                  setToDate(dateBounds.max);
                  setSortField("created_at");
                  setSortOrder("desc");
                }}
              >
                Reset
              </Button>
            </div>
          </div>

          {showAdvancedFilters && (
            <div className="mt-4 pt-4 border-t border-white/10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
              <div>
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">User Name</Label>
                <select className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm" value={nameFilter} onChange={(e) => setNameFilter(e.target.value)}>
                  <option value={FILTER_ALL}>All User Names</option>
                  {filterOptions.names.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">Mobile</Label>
                <select className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm" value={mobileFilter} onChange={(e) => setMobileFilter(e.target.value)}>
                  <option value={FILTER_ALL}>All Mobile Numbers</option>
                  {filterOptions.mobiles.map((mobile) => (
                    <option key={mobile} value={mobile}>{mobile}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">Track / Album</Label>
                <select className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm" value={titleFilter} onChange={(e) => setTitleFilter(e.target.value)}>
                  <option value={FILTER_ALL}>All Track/Album Names</option>
                  {filterOptions.titles.map((title) => (
                    <option key={title} value={title}>{title}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">Album</Label>
                <select className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm" value={albumFilter} onChange={(e) => setAlbumFilter(e.target.value)}>
                  <option value={FILTER_ALL}>All Albums</option>
                  {filterOptions.albums.map((album) => (
                    <option key={album.value} value={album.value}>{album.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">From Date</Label>
                <Input type="date" min={dateBounds.min || undefined} max={dateBounds.max || undefined} value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="mt-1" />
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">To Date</Label>
                <Input type="date" min={dateBounds.min || undefined} max={dateBounds.max || undefined} value={toDate} onChange={(e) => setToDate(e.target.value)} className="mt-1" />
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 mb-4">
          {TAB_CONFIG.map((option) => (
            <Button
              key={option.id}
              size="sm"
              variant={tab === option.id ? "default" : "ghost"}
              onClick={() => setTab(option.id)}
              data-testid={`master-tab-${option.id}`}
            >
              {option.label}
            </Button>
          ))}
          <Badge variant="secondary" className="ml-auto">
            {records.length} records
          </Badge>
        </div>

        <div className="glass rounded-2xl overflow-auto" data-testid="master-results-table">
          <table className="w-full min-w-[980px] text-sm">
            <thead className="bg-secondary/40">
              <tr>
                <th className="text-left p-3 font-medium">Type</th>
                <th className="text-left p-3 font-medium">Name</th>
                <th className="text-left p-3 font-medium">User</th>
                <th className="text-left p-3 font-medium">Created</th>
                <th className="text-left p-3 font-medium">Duration</th>
                <th className="text-left p-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map((item) => {
                const isAlbum = tab === "albums";
                const previewTrack = isAlbum ? (item.songs || [])[0] : item;
                return (
                  <tr key={`${tab}-${item.id}`} className="border-t border-white/5 hover:bg-white/[0.03]">
                    <td className="p-3">
                      <Badge variant="outline">{isAlbum ? "Album" : item.source === "single" ? "Single" : "Track"}</Badge>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-3">
                        <img
                          src={item.cover_art_url || MEDIA_PREVIEW_FALLBACK}
                          alt={item.title || "track"}
                          className="w-10 h-10 rounded object-cover border border-white/10"
                          loading="lazy"
                        />
                        <div>
                          <div className="font-medium truncate max-w-[220px]">{item.title || "-"}</div>
                          <div className="text-xs text-muted-foreground truncate max-w-[220px]">
                            Album: {item.album_title || "-"} • Mobile: {item.user_mobile || "-"}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="p-3">{item.user_name || "Unknown"}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Calendar className="w-3 h-3" />
                        {formatDate(item.created_at)}
                      </div>
                    </td>
                    <td className="p-3">{isAlbum ? `${item.song_count || 0} tracks` : formatDuration(item.duration_seconds)}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-1.5">
                        {previewTrack ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-8 gap-1"
                            onClick={() => setMediaModalRecord({ ...previewTrack, title: isAlbum ? `${item.title} (Album Preview)` : previewTrack.title })}
                          >
                            <PlayCircle className="w-4 h-4" />
                            Play
                          </Button>
                        ) : null}
                        {!isAlbum && item.audio_url && (
                          <button
                            type="button"
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-secondary hover:bg-secondary/80"
                            onClick={() => downloadRecordMedia(item, "audio")}
                          >
                            <Download className="w-3 h-3" />Audio
                          </button>
                        )}
                        {!isAlbum && item.video_url && (
                          <button
                            type="button"
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-secondary hover:bg-secondary/80"
                            onClick={() => downloadRecordMedia(item, "video")}
                          >
                            <Download className="w-3 h-3" />Video
                          </button>
                        )}
                        <Button size="sm" variant="ghost" className="h-8" onClick={() => setDetailsModal({ type: isAlbum ? "album" : "track", data: item })}>
                          <FileText className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {records.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-muted-foreground">No records matched your filters.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {mediaModalRecord && (
          <MasterMediaModal
            record={mediaModalRecord}
            onClose={() => setMediaModalRecord(null)}
          />
        )}

        {detailsModal && (
          <MasterDetailsModal
            type={detailsModal.type}
            record={detailsModal.data}
            onClose={() => setDetailsModal(null)}
          />
        )}
      </div>
    </div>
  );
}

function MasterMediaModal({ record, onClose }) {
  const audioRef = useRef(null);
  const videoRef = useRef(null);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [videoPlaying, setVideoPlaying] = useState(false);

  const seekMedia = (ref, delta) => {
    if (!ref.current) return;
    const next = Math.max(0, (ref.current.currentTime || 0) + delta);
    ref.current.currentTime = next;
  };

  const togglePlayback = async (ref, setPlaying) => {
    if (!ref.current) return;
    if (ref.current.paused) {
      await ref.current.play();
      setPlaying(true);
      return;
    }
    ref.current.pause();
    setPlaying(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div className="relative max-w-3xl w-full bg-card rounded-2xl overflow-hidden shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="absolute top-4 right-4 z-10 p-2 rounded-full bg-black/50 hover:bg-black/70 transition-colors">
          <X className="w-5 h-5" />
        </button>
        <div className="p-4 border-b border-white/5">
          <h3 className="font-semibold truncate pr-12">{record.title || "Media Preview"}</h3>
          <p className="text-xs text-muted-foreground mt-1">Duration: {formatDuration(record.duration_seconds)}</p>
        </div>

        <div className="p-4 space-y-4 max-h-[75vh] overflow-y-auto">
          {record.audio_url ? (
            <div className="space-y-2">
              <p className="text-sm font-medium">Audio Player</p>
              <audio
                ref={audioRef}
                src={record.audio_url}
                controls
                onPlay={() => setAudioPlaying(true)}
                onPause={() => setAudioPlaying(false)}
                className="w-full"
              />
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" className="gap-1" onClick={() => seekMedia(audioRef, -10)}>
                  <Rewind className="w-3.5 h-3.5" />
                  -10s
                </Button>
                <Button size="sm" variant="outline" className="gap-1" onClick={() => togglePlayback(audioRef, setAudioPlaying)}>
                  {audioPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                  {audioPlaying ? "Pause" : "Play"}
                </Button>
                <Button size="sm" variant="outline" className="gap-1" onClick={() => seekMedia(audioRef, 10)}>
                  <FastForward className="w-3.5 h-3.5" />
                  +10s
                </Button>
              </div>
              <button
                type="button"
                onClick={() => downloadRecordMedia(record, "audio")}
                className="inline-flex items-center gap-2 text-sm px-3 py-2 rounded-lg bg-secondary hover:bg-secondary/80"
              >
                <Download className="w-4 h-4" />
                Download Audio
              </button>
            </div>
          ) : (
            <div className="rounded-lg border border-white/10 bg-secondary/30 p-3 text-sm text-muted-foreground">
              Audio is not available for this record.
            </div>
          )}

          {record.video_url ? (
            <div className="space-y-2">
              <p className="text-sm font-medium">Video Player</p>
              <video
                ref={videoRef}
                src={record.video_url}
                poster={record.video_thumbnail}
                controls
                onPlay={() => setVideoPlaying(true)}
                onPause={() => setVideoPlaying(false)}
                className="w-full aspect-video bg-black rounded-xl"
              />
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" className="gap-1" onClick={() => seekMedia(videoRef, -10)}>
                  <Rewind className="w-3.5 h-3.5" />
                  -10s
                </Button>
                <Button size="sm" variant="outline" className="gap-1" onClick={() => togglePlayback(videoRef, setVideoPlaying)}>
                  {videoPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                  {videoPlaying ? "Pause" : "Play"}
                </Button>
                <Button size="sm" variant="outline" className="gap-1" onClick={() => seekMedia(videoRef, 10)}>
                  <FastForward className="w-3.5 h-3.5" />
                  +10s
                </Button>
              </div>
              <button
                type="button"
                onClick={() => downloadRecordMedia(record, "video")}
                className="inline-flex items-center gap-2 text-sm px-3 py-2 rounded-lg bg-secondary hover:bg-secondary/80"
              >
                <Download className="w-4 h-4" />
                Download Video
              </button>
            </div>
          ) : (
            <div className="rounded-lg border border-white/10 bg-secondary/30 p-3 text-sm text-muted-foreground">
              Video is not available for this record.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MasterDetailsModal({ type, record, onClose }) {
  const fields = [
    ["Title", record?.title],
    ["Music Prompt", record?.music_prompt],
    ["Genres", Array.isArray(record?.genres) ? record.genres.join(", ") : "-"],
    ["Duration", type === "track" ? formatDuration(record?.duration_seconds) : `${record?.song_count || record?.songs?.length || 0} tracks`],
    ["Vocal Languages", Array.isArray(record?.vocal_languages) ? record.vocal_languages.join(", ") : "-"],
    ["Lyrics", record?.lyrics],
    ["Artist Inspiration", record?.artist_inspiration],
    ["Video Style", record?.video_style],
    ["Entropy", record?.entropy],
    ["User", record?.user_name],
    ["Mobile", record?.user_mobile],
    ["Created", formatDate(record?.created_at)],
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div className="relative max-w-5xl w-full bg-card rounded-2xl overflow-hidden shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="absolute top-4 right-4 z-10 p-2 rounded-full bg-black/50 hover:bg-black/70 transition-colors">
          <X className="w-5 h-5" />
        </button>
        <div className="p-4 border-b border-white/5">
          <h3 className="font-semibold truncate pr-12">See All Details: {record?.title || "Untitled"}</h3>
          <p className="text-xs text-muted-foreground mt-1">{type === "album" ? "Album Details" : "Track Details"}</p>
        </div>

        <div className="p-4 max-h-[75vh] overflow-y-auto space-y-4">
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
                  <p className="text-xs text-muted-foreground">Duration: {formatDuration(song.duration_seconds || 0)}</p>
                  <p className="text-xs text-muted-foreground line-clamp-3">Lyrics: {song.lyrics || "-"}</p>
                  <div className="flex gap-2 mt-2">
                    {song.audio_url && (
                      <button
                        type="button"
                        onClick={() => downloadRecordMedia(song, "audio", song.user_id || record?.user_id)}
                        className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-secondary hover:bg-secondary/80"
                      >
                        <Download className="w-3 h-3" />Audio
                      </button>
                    )}
                    {song.video_url && (
                      <button
                        type="button"
                        onClick={() => downloadRecordMedia(song, "video", song.user_id || record?.user_id)}
                        className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-secondary hover:bg-secondary/80"
                      >
                        <Download className="w-3 h-3" />Video
                      </button>
                    )}
                  </div>
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

export { MasterDashboardPage };
