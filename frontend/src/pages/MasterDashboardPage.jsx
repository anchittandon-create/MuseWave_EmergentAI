import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { API } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { toast } from "sonner";
import { Shield, Users, Music, Disc, Calendar, Search } from "lucide-react";

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

const MediaThumbLink = ({ href, image, label }) => {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="group inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.02] p-1.5 hover:border-primary/50 hover:bg-primary/10 transition-colors"
    >
      <img
        src={image || MEDIA_PREVIEW_FALLBACK}
        alt={label}
        className="w-10 h-10 rounded object-cover border border-white/10"
        loading="lazy"
      />
      <span className="text-xs text-primary group-hover:underline">{label}</span>
    </a>
  );
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
      <div className="max-w-[1200px] mx-auto">
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Search</Label>
              <div className="relative mt-1">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" placeholder="Track, album, user, mobile..." />
              </div>
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">User Name</Label>
              <select
                className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={nameFilter}
                onChange={(e) => setNameFilter(e.target.value)}
              >
                <option value={FILTER_ALL}>All User Names</option>
                {filterOptions.names.map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Mobile</Label>
              <select
                className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={mobileFilter}
                onChange={(e) => setMobileFilter(e.target.value)}
              >
                <option value={FILTER_ALL}>All Mobile Numbers</option>
                {filterOptions.mobiles.map((mobile) => (
                  <option key={mobile} value={mobile}>{mobile}</option>
                ))}
              </select>
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Track / Album</Label>
              <select
                className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={titleFilter}
                onChange={(e) => setTitleFilter(e.target.value)}
              >
                <option value={FILTER_ALL}>All Track/Album Names</option>
                {filterOptions.titles.map((title) => (
                  <option key={title} value={title}>{title}</option>
                ))}
              </select>
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Album</Label>
              <select
                className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={albumFilter}
                onChange={(e) => setAlbumFilter(e.target.value)}
              >
                <option value={FILTER_ALL}>All Albums</option>
                {filterOptions.albums.map((album) => (
                  <option key={album.value} value={album.value}>{album.label}</option>
                ))}
              </select>
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">From Date</Label>
              <Input
                type="date"
                min={dateBounds.min || undefined}
                max={dateBounds.max || undefined}
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">To Date</Label>
              <Input
                type="date"
                min={dateBounds.min || undefined}
                max={dateBounds.max || undefined}
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="mt-1"
              />
            </div>
            <div className="grid grid-cols-2 gap-2 md:col-span-2 lg:col-span-3">
              <div>
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
              <div>
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
              <div className="flex items-end">
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
                  Reset Filters
                </Button>
              </div>
            </div>
          </div>
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
          <table className="w-full min-w-[1180px] text-sm">
            <thead className="bg-secondary/40">
              <tr>
                <th className="text-left p-3 font-medium">Type</th>
                <th className="text-left p-3 font-medium">Name</th>
                <th className="text-left p-3 font-medium">Album</th>
                <th className="text-left p-3 font-medium">User</th>
                <th className="text-left p-3 font-medium">Mobile</th>
                <th className="text-left p-3 font-medium">Created</th>
                <th className="text-left p-3 font-medium">Duration</th>
                <th className="text-left p-3 font-medium">Files</th>
              </tr>
            </thead>
            <tbody>
              {records.map((item) => {
                const isAlbum = tab === "albums";
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
                        <div className="font-medium truncate max-w-[220px]">{item.title || "-"}</div>
                      </div>
                    </td>
                    <td className="p-3 text-muted-foreground truncate max-w-[220px]">{item.album_title || "-"}</td>
                    <td className="p-3">{item.user_name || "Unknown"}</td>
                    <td className="p-3 font-mono">{item.user_mobile || "-"}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Calendar className="w-3 h-3" />
                        {formatDate(item.created_at)}
                      </div>
                    </td>
                    <td className="p-3">{isAlbum ? `${item.song_count || 0} tracks` : formatDuration(item.duration_seconds)}</td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-2">
                        {!isAlbum && (
                          <MediaThumbLink
                            href={item.audio_url}
                            image={item.cover_art_url || MEDIA_PREVIEW_FALLBACK}
                            label="Audio"
                          />
                        )}
                        {!isAlbum && (
                          <MediaThumbLink
                            href={item.video_url}
                            image={item.video_thumbnail || item.cover_art_url || MEDIA_PREVIEW_FALLBACK}
                            label="Video"
                          />
                        )}
                        {isAlbum && <span className="text-muted-foreground">-</span>}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {records.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-6 text-center text-muted-foreground">No records matched your filters.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export { MasterDashboardPage };
