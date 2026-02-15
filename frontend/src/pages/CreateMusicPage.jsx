import { useState, useEffect, useCallback } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Slider } from "../components/ui/slider";
import { Switch } from "../components/ui/switch";
import { Badge } from "../components/ui/badge";
import { Sparkles, Music, Disc, Play, Pause, Download, Loader2, Search, X, ChevronDown, Film } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { API } from "../App";

export default function CreateMusicPage({ user }) {
  const [mode, setMode] = useState("single");
  const [loading, setLoading] = useState(false);
  const [suggestingField, setSuggestingField] = useState(null);
  const [genres, setGenres] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [artists, setArtists] = useState([]);
  const [videoStyles, setVideoStyles] = useState([]);
  const [result, setResult] = useState(null);
  const [playingTrack, setPlayingTrack] = useState(null);
  const [audioRef, setAudioRef] = useState(null);
  const [genreSearch, setGenreSearch] = useState("");
  const [languageSearch, setLanguageSearch] = useState("");
  const [durationInput, setDurationInput] = useState("25s");
  const [showAllGenres, setShowAllGenres] = useState(false);
  const [aiSuggestedFields, setAiSuggestedFields] = useState(new Set());
  const [lastSuggestion, setLastSuggestion] = useState({});
  const [expandedSongIndex, setExpandedSongIndex] = useState(null);
  const [songReference, setSongReference] = useState(null); // Track which song was used as reference
  const [albumVideoLoading, setAlbumVideoLoading] = useState(false);

  const [formData, setFormData] = useState({
    title: "",
    musicPrompt: "",
    selectedGenres: [],
    durationSeconds: 25,
    vocalLanguages: [],
    lyrics: "",
    artistInspiration: "",
    generateVideo: false,
    videoStyle: "",
    numSongs: 3,
    albumSongs: [], // Array of song configs for album mode
  });

  // Initialize album songs when number changes
  useEffect(() => {
    if (mode === "album") {
      const currentSongsCount = formData.albumSongs.length;
      const requiredSongsCount = formData.numSongs;
      
      if (currentSongsCount !== requiredSongsCount) {
        const newSongs = [];
        for (let i = 0; i < requiredSongsCount; i++) {
          if (i < currentSongsCount) {
            newSongs.push(formData.albumSongs[i]);
          } else {
            newSongs.push({
              title: "",
              musicPrompt: "",
              selectedGenres: [],
              durationSeconds: 25,
              vocalLanguages: [],
              lyrics: "",
              artistInspiration: "",
              videoStyle: "",
            });
          }
        }
        setFormData((prev) => ({ ...prev, albumSongs: newSongs }));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.numSongs, mode]);

  useEffect(() => {
    fetchKnowledgeBases();
  }, []);

  const fetchKnowledgeBases = async () => {
    try {
      const [genresRes, langsRes, artistsRes, stylesRes] = await Promise.all([
        axios.get(`${API}/genres`),
        axios.get(`${API}/languages`),
        axios.get(`${API}/artists`),
        axios.get(`${API}/video-styles`),
      ]);
      setGenres(genresRes.data.genres || []);
      setLanguages(langsRes.data.languages || []);
      setArtists(artistsRes.data.artists || []);
      setVideoStyles(stylesRes.data.styles || []);
    } catch (error) {
      console.error("Failed to fetch knowledge bases:", error);
    }
  };

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}:${secs.toString().padStart(2, "0")}`;
    } else {
      return `${secs}s`;
    }
  };

  const toggleGenre = (genre) => {
    const selected = formData.selectedGenres.includes(genre)
      ? formData.selectedGenres.filter((g) => g !== genre)
      : [...formData.selectedGenres, genre];
    setFormData({ ...formData, selectedGenres: selected });
  };

  const toggleLanguage = (lang) => {
    const selected = formData.vocalLanguages.includes(lang)
      ? formData.vocalLanguages.filter((l) => l !== lang)
      : [...formData.vocalLanguages, lang];
    setFormData({ ...formData, vocalLanguages: selected });
  };

  const filteredGenres = genreSearch
    ? genres.filter((g) => g.toLowerCase().includes(genreSearch.toLowerCase()))
    : genres;

  const displayedGenres = showAllGenres ? filteredGenres : filteredGenres.slice(0, 20);

  const handleAISuggest = async (field, songIndex = null) => {
    setSuggestingField(field);
    try {
      // Get current value based on mode (single or album song)
      let currentValue, context;
      
      if (mode === "album" && songIndex !== null) {
        const song = formData.albumSongs[songIndex];
        const fieldMap = {
          title: song.title,
          music_prompt: song.musicPrompt,
          genres: song.selectedGenres.join(", "),
          lyrics: song.lyrics,
          artist_inspiration: song.artistInspiration,
          video_style: song.videoStyle,
          vocal_languages: song.vocalLanguages.join(", "),
          duration: formatDuration(song.durationSeconds),
        };
        currentValue = fieldMap[field] || "";
        context = {
          music_prompt: song.musicPrompt,
          genres: song.selectedGenres,
          lyrics: song.lyrics,
          artist_inspiration: song.artistInspiration,
          album_context: formData.title, // Album title for context
          track_number: songIndex + 1,
        };
      } else {
        currentValue = getFieldValue(field);
        context = {
          music_prompt: formData.musicPrompt,
          genres: formData.selectedGenres,
          lyrics: formData.lyrics,
          artist_inspiration: formData.artistInspiration,
        };
      }

      const response = await axios.post(`${API}/suggest`, {
        field,
        current_value: currentValue,
        context,
      });

      if (mode === "album" && songIndex !== null) {
        applySuggestionToSong(songIndex, field, response.data.suggestion);
      } else {
        applySuggestion(field, response.data.suggestion);
      }
      toast.success("AI suggestion applied!", { duration: 2000 });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to get suggestion");
    } finally {
      setSuggestingField(null);
    }
  };

  const parseDurationInput = (input) => {
    const s = String(input).trim();
    if (!s) return null;
    const num = parseInt(s, 10);
    if (!isNaN(num) && num >= 10) return Math.min(num, 72000);
    const hMatch = s.match(/(\d+)\s*h/);
    const mMatch = s.match(/(\d+)\s*m/);
    const sMatch = s.match(/(\d+)\s*s/);
    const colonMatch = s.match(/^(\d+):(\d+)(?::(\d+))?$/);
    if (colonMatch) {
      const [, a, b, c] = colonMatch;
      let total;
      if (c !== undefined) {
        total = parseInt(a, 10) * 3600 + parseInt(b, 10) * 60 + parseInt(c, 10);
      } else {
        total = parseInt(a, 10) * 60 + parseInt(b, 10);
      }
      return total >= 10 ? Math.min(total, 72000) : null;
    }
    let total = 0;
    if (hMatch) total += parseInt(hMatch[1], 10) * 3600;
    if (mMatch) total += parseInt(mMatch[1], 10) * 60;
    if (sMatch) total += parseInt(sMatch[1], 10);
    if (total >= 10) return Math.min(total, 72000);
    return null;
  };

  const handleDurationInputChange = (e) => {
    const val = e.target.value;
    setDurationInput(val);
    const parsed = parseDurationInput(val);
    if (parsed !== null) {
      setFormData((prev) => ({ ...prev, durationSeconds: parsed }));
    }
  };

  const handleDurationInputBlur = () => {
    setDurationInput(formatDuration(formData.durationSeconds));
  };

  const getFieldValue = (field) => {
    const mapping = {
      title: formData.title,
      music_prompt: formData.musicPrompt,
      genres: formData.selectedGenres.join(", "),
      lyrics: formData.lyrics,
      artist_inspiration: formData.artistInspiration,
      video_style: formData.videoStyle,
      vocal_languages: formData.vocalLanguages.join(", "),
    };
    return mapping[field] || "";
  };

  const findBestMatch = (suggested, options) => {
    const s = suggested.toLowerCase().trim();
    const exact = options.find((o) => o.toLowerCase() === s);
    if (exact) return exact;
    const contains = options.find((o) => o.toLowerCase().includes(s) || s.includes(o.toLowerCase()));
    if (contains) return contains;
    const startsWith = options.find((o) => o.toLowerCase().startsWith(s) || s.startsWith(o.toLowerCase()));
    return startsWith || null;
  };

  const applySuggestion = (field, suggestion) => {
    const trimmed = (suggestion || "").trim();
    if (!trimmed) return;

    // Track that this field received an AI suggestion
    const newSuggestedFields = new Set(aiSuggestedFields);
    newSuggestedFields.add(field);
    setAiSuggestedFields(newSuggestedFields);
    setLastSuggestion({ ...lastSuggestion, [field]: trimmed });

    const updates = {
      title: { title: suggestion },
      music_prompt: { musicPrompt: suggestion },
      lyrics: { lyrics: suggestion },
      artist_inspiration: { artistInspiration: suggestion },
      video_style: { videoStyle: suggestion },
    };

    if (updates[field]) {
      setFormData((prev) => ({ ...prev, ...updates[field] }));
    } else if (field === "genres") {
      setGenreSearch(suggestion);
      const suggestedGenres = suggestion.split(",").map((g) => g.trim()).filter(Boolean);
      const validGenres = [];
      for (const g of suggestedGenres) {
        const match = findBestMatch(g, genres);
        if (match && !validGenres.includes(match)) validGenres.push(match);
      }
      if (validGenres.length > 0) {
        setFormData((prev) => ({ ...prev, selectedGenres: validGenres }));
      }
    } else if (field === "vocal_languages") {
      setLanguageSearch(suggestion);
      const suggestedLangs = suggestion.split(",").map((l) => l.trim()).filter(Boolean);
      const validLangs = [];
      for (const l of suggestedLangs) {
        const match = findBestMatch(l, languages);
        if (match && !validLangs.includes(match)) validLangs.push(match);
      }
      if (validLangs.length > 0) {
        setFormData((prev) => ({ ...prev, vocalLanguages: validLangs }));
      } else if (suggestion.toLowerCase().includes("instrumental")) {
        setFormData((prev) => ({ ...prev, vocalLanguages: ["Instrumental"] }));
      }
    } else if (field === "duration") {
      // Parse duration suggestion (could be "45s", "2m30s", etc.)
      const parsed = parseDurationInput(suggestion);
      if (parsed !== null && parsed >= 10) {
        setDurationInput(formatDuration(parsed));
        setFormData((prev) => ({ ...prev, durationSeconds: parsed }));
      }
    }
  };

  // Helper function to update album song data
  const updateAlbumSong = (index, updates) => {
    const newSongs = [...formData.albumSongs];
    newSongs[index] = { ...newSongs[index], ...updates };
    setFormData((prev) => ({ ...prev, albumSongs: newSongs }));
  };

  // Copy song data from a previous song to current song
  const copySongFromPrevious = (toIndex, fromIndex, copyType = "all") => {
    const sourceSong = formData.albumSongs[fromIndex];
    const updates = {};

    switch (copyType) {
      case "all":
        // Copy all fields
        updates.title = sourceSong.title ? `${sourceSong.title} (Variation)` : "";
        updates.musicPrompt = sourceSong.musicPrompt;
        updates.selectedGenres = [...sourceSong.selectedGenres];
        updates.durationSeconds = sourceSong.durationSeconds;
        updates.vocalLanguages = [...sourceSong.vocalLanguages];
        updates.lyrics = sourceSong.lyrics;
        updates.artistInspiration = sourceSong.artistInspiration;
        updates.videoStyle = sourceSong.videoStyle;
        break;
      case "genres":
        updates.selectedGenres = [...sourceSong.selectedGenres];
        break;
      case "languages":
        updates.vocalLanguages = [...sourceSong.vocalLanguages];
        break;
      case "style":
        updates.musicPrompt = sourceSong.musicPrompt;
        updates.selectedGenres = [...sourceSong.selectedGenres];
        updates.vocalLanguages = [...sourceSong.vocalLanguages];
        break;
      default:
        break;
    }

    if (Object.keys(updates).length > 0) {
      updateAlbumSong(toIndex, updates);
      setSongReference({ songIndex: toIndex, referencedFrom: fromIndex, type: copyType });
      toast.success(`Track ${toIndex + 1} updated from Track ${fromIndex + 1}`);
    }
  };

  // Apply AI suggestion to a specific album song
  const applySuggestionToSong = (songIndex, field, suggestion) => {
    const trimmed = (suggestion || "").trim();
    if (!trimmed) return;

    const song = formData.albumSongs[songIndex];
    const updates = {};

    switch (field) {
      case "title":
        updates.title = trimmed;
        break;
      case "music_prompt":
        updates.musicPrompt = trimmed;
        break;
      case "lyrics":
        updates.lyrics = trimmed;
        break;
      case "artist_inspiration":
        updates.artistInspiration = trimmed;
        break;
      case "video_style":
        updates.videoStyle = trimmed;
        break;
      case "duration":
        const parsed = parseDurationInput(trimmed);
        if (parsed !== null && parsed >= 10) {
          updates.durationSeconds = parsed;
        }
        break;
      case "genres":
        const suggestedGenres = trimmed.split(",").map((g) => g.trim()).filter(Boolean);
        const validGenres = [];
        for (const g of suggestedGenres) {
          const match = findBestMatch(g, genres);
          if (match && !validGenres.includes(match)) validGenres.push(match);
        }
        if (validGenres.length > 0) {
          updates.selectedGenres = validGenres;
        }
        break;
      case "vocal_languages":
        const suggestedLangs = trimmed.split(",").map((l) => l.trim()).filter(Boolean);
        const validLangs = [];
        for (const l of suggestedLangs) {
          const match = findBestMatch(l, languages);
          if (match && !validLangs.includes(match)) validLangs.push(match);
        }
        if (validLangs.length > 0) {
          updates.vocalLanguages = validLangs;
        } else if (trimmed.toLowerCase().includes("instrumental")) {
          updates.vocalLanguages = ["Instrumental"];
        }
        break;
      default:
        break;
    }

    if (Object.keys(updates).length > 0) {
      updateAlbumSong(songIndex, updates);
    }
  };

  const handleSubmit = async () => {
    if (mode === "single" && !formData.musicPrompt.trim()) {
      toast.error("Please describe your music idea");
      return;
    }
    if (mode === "album") {
      if (!formData.albumSongs.length) {
        toast.error("Add at least one track to the album");
        return;
      }
      const missingTrackPrompts = formData.albumSongs
        .map((song, index) => ({ index, prompt: song.musicPrompt?.trim() }))
        .filter((item) => !item.prompt)
        .map((item) => item.index + 1);
      if (missingTrackPrompts.length > 0) {
        toast.error(`Please enter music description for track(s): ${missingTrackPrompts.join(", ")}`);
        return;
      }
    }

    setLoading(true);
    setResult(null);

    try {
      const endpoint = mode === "single" ? "/songs/create" : "/albums/create";
      const albumGenres = Array.from(
        new Set(
          formData.albumSongs.flatMap((song) => song.selectedGenres || []).concat(formData.selectedGenres || [])
        )
      );
      const payload = {
        title: formData.title,
        music_prompt: mode === "single"
          ? formData.musicPrompt
          : (formData.musicPrompt || formData.albumSongs[0]?.musicPrompt || ""),
        genres: mode === "single" ? formData.selectedGenres : albumGenres,
        vocal_languages: formData.vocalLanguages,
        lyrics: formData.lyrics,
        artist_inspiration: formData.artistInspiration,
        generate_video: formData.generateVideo,
        video_style: formData.videoStyle,
        user_id: user.id,
        ...(mode === "single" 
          ? { duration_seconds: formData.durationSeconds, mode: "single" }
          : {
              num_songs: formData.albumSongs.length,
              album_songs: formData.albumSongs.map((song) => ({
                title: song.title || "",
                music_prompt: song.musicPrompt || "",
                genres: song.selectedGenres || [],
                duration_seconds: song.durationSeconds || 25,
                vocal_languages: song.vocalLanguages || [],
                lyrics: song.lyrics || "",
                artist_inspiration: song.artistInspiration || "",
                video_style: song.videoStyle || "",
              })),
            }
        ),
      };

      const response = await axios.post(`${API}${endpoint}`, payload);
      setResult({ type: mode === "single" ? "song" : "album", data: response.data });
      toast.success(mode === "single" ? "Track created!" : `Album with ${response.data.songs?.length} tracks created!`);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Creation failed");
    } finally {
      setLoading(false);
    }
  };

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

  const generateAlbumVideos = async (albumId) => {
    try {
      setAlbumVideoLoading(true);
      const response = await axios.post(`${API}/albums/${albumId}/generate-videos?user_id=${user.id}`);
      toast.success(response.data?.message || "Video generation started");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to generate videos");
    } finally {
      setAlbumVideoLoading(false);
    }
  };

  const SuggestButton = ({ field }) => (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className={`h-7 px-2 text-xs font-semibold transition-all gap-1 ${
        aiSuggestedFields.has(field)
          ? "text-purple-500 hover:text-purple-600 hover:bg-purple-500/10 border border-purple-500/30"
          : "text-primary hover:text-primary hover:bg-primary/10"
      }`}
      onClick={() => handleAISuggest(field)}
      disabled={suggestingField === field || loading}
      data-testid={`suggest-${field}-btn`}
    >
      {suggestingField === field ? (
        <Loader2 className="w-3 h-3 animate-spin" />
      ) : (
        <Sparkles className="w-3 h-3" />
      )}
      {aiSuggestedFields.has(field) ? "Suggested" : "Suggest"}
    </Button>
  );

  return (
    <div className="min-h-screen p-6 lg:p-10" data-testid="create-music-page">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <h1 className="font-display text-3xl lg:text-4xl font-bold tracking-tight mb-2">Create Music</h1>
          <p className="text-muted-foreground">Describe your vision and let AI bring it to life</p>
        </div>

        {/* Mode Selection */}
        <div className="grid grid-cols-2 gap-4 mb-10" data-testid="mode-selection">
          {[
            { id: "single", icon: Music, title: "Single Song", desc: "One unique track" },
            { id: "album", icon: Disc, title: "Album", desc: "Multiple tracks" },
          ].map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setMode(m.id)}
              className={`p-6 rounded-2xl border-2 transition-all duration-200 text-left ${
                mode === m.id
                  ? "border-primary bg-primary/5 shadow-lg shadow-primary/10"
                  : "border-white/10 hover:border-white/20 hover:bg-white/[0.02]"
              }`}
              data-testid={`${m.id}-mode-btn`}
            >
              <m.icon className={`w-7 h-7 mb-3 ${mode === m.id ? "text-primary" : "text-muted-foreground"}`} />
              <h3 className="font-semibold mb-1">{m.title}</h3>
              <p className="text-sm text-muted-foreground">{m.desc}</p>
            </button>
          ))}
        </div>

        {/* Form */}
        <div className="space-y-8">
          {/* Album track count */}
          {mode === "album" && (
            <div className="p-5 rounded-2xl bg-card border border-white/5 animate-fade-in">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground mb-3 block">
                Number of Tracks
              </Label>
              <div className="flex items-center gap-4">
                <Input
                  type="number"
                  min={2}
                  max={8}
                  value={formData.numSongs}
                  onChange={(e) => setFormData({ ...formData, numSongs: Math.min(parseInt(e.target.value) || 3, 8) })}
                  className="w-20 h-12 text-center text-lg font-medium bg-secondary border-0"
                  data-testid="num-songs-input"
                />
                <span className="text-sm text-muted-foreground">tracks with cohesive variation</span>
              </div>
            </div>
          )}

          {/* Album Songs Configuration - Form by Form with Details */}
          {mode === "album" && formData.albumSongs.length > 0 && (
            <div className="space-y-6">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground block">
                Configure Each Track
              </Label>
              
              {formData.albumSongs.map((song, idx) => (
                <div key={idx} className="space-y-4">
                  {/* Song Summary Header */}
                  <button
                    type="button"
                    onClick={() => setExpandedSongIndex(expandedSongIndex === idx ? null : idx)}
                    className={`w-full p-4 rounded-xl border-2 transition-all text-left ${
                      expandedSongIndex === idx
                        ? "border-primary bg-primary/5 shadow-md"
                        : "border-white/10 hover:border-white/20 hover:bg-white/[0.02]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-primary/20 text-primary text-xs font-bold">
                            {idx + 1}
                          </span>
                          <h4 className="font-semibold text-sm">
                            {song.title ? song.title : `Track ${idx + 1}`}
                          </h4>
                        </div>
                        {song.musicPrompt && (
                          <p className="text-xs text-muted-foreground line-clamp-2 mt-2 ml-10">{song.musicPrompt}</p>
                        )}
                      </div>
                      <ChevronDown
                        className={`w-5 h-5 text-muted-foreground transition-transform flex-shrink-0 ${
                          expandedSongIndex === idx ? "rotate-180" : ""
                        }`}
                      />
                    </div>
                  </button>

                  {/* Expanded Song Form Details */}
                  {expandedSongIndex === idx && (
                    <div className="space-y-6 p-6 rounded-2xl bg-card border border-white/10 animate-fade-in ml-2">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-display text-lg font-bold">Track {idx + 1} Details</h3>
                        {songReference?.songIndex === idx && (
                          <Badge variant="outline" className="text-xs border-blue-500/50 bg-blue-500/10 text-blue-400">
                            Referenced from Track {songReference.referencedFrom + 1}
                          </Badge>
                        )}
                      </div>

                      {/* Copy from Previous Songs */}
                      {idx > 0 && (
                        <div className="p-4 rounded-lg bg-secondary/50 border border-white/10">
                          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-3 block font-medium">
                            Quick Copy from Previous Track
                          </p>
                          <div className="flex flex-wrap gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => copySongFromPrevious(idx, idx - 1, "all")}
                              className="text-xs h-9"
                            >
                              Copy All from Track {idx}
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => copySongFromPrevious(idx, idx - 1, "style")}
                              className="text-xs h-9"
                            >
                              Copy Style & Genres
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => copySongFromPrevious(idx, idx - 1, "genres")}
                              className="text-xs h-9"
                            >
                              Copy Genres Only
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => copySongFromPrevious(idx, idx - 1, "languages")}
                              className="text-xs h-9"
                            >
                              Copy Languages
                            </Button>
                          </div>
                        </div>
                      )}
                      
                      {/* Song Title */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs uppercase tracking-widest text-muted-foreground">Track Title</Label>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleAISuggest("title", idx)}
                            disabled={suggestingField === "title"}
                            className="text-xs h-auto px-2 py-1 text-primary hover:text-primary/80"
                          >
                            {suggestingField === "title" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                          </Button>
                        </div>
                        <Input
                          placeholder="e.g., Midnight Dreams"
                          value={song.title}
                          onChange={(e) => updateAlbumSong(idx, { title: e.target.value })}
                          className="h-12 text-lg bg-transparent border-0 border-b-2 border-white/10 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary"
                        />
                      </div>

                      {/* Song Prompt */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs uppercase tracking-widest text-muted-foreground">Track Description</Label>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleAISuggest("music_prompt", idx)}
                            disabled={suggestingField === "music_prompt"}
                            className="text-xs h-auto px-2 py-1 text-primary hover:text-primary/80"
                          >
                            {suggestingField === "music_prompt" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                          </Button>
                        </div>
                        <Textarea
                          placeholder="Describe the mood, style, and feel of this specific track..."
                          value={song.musicPrompt}
                          onChange={(e) => updateAlbumSong(idx, { musicPrompt: e.target.value })}
                          className="min-h-[100px] text-base leading-relaxed bg-card border border-white/10 rounded-xl focus-visible:ring-1 focus-visible:ring-primary focus-visible:border-primary resize-none p-4"
                        />
                      </div>

                      {/* Song Duration */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs uppercase tracking-widest text-muted-foreground">Duration</Label>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleAISuggest("duration", idx)}
                            disabled={suggestingField === "duration"}
                            className="text-xs h-auto px-2 py-1 text-primary hover:text-primary/80"
                          >
                            {suggestingField === "duration" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                          </Button>
                        </div>
                        <div className="flex items-center gap-4">
                          <Input
                            value={formatDuration(song.durationSeconds)}
                            onChange={(e) => {
                              const parsed = parseDurationInput(e.target.value);
                              if (parsed !== null) {
                                updateAlbumSong(idx, { durationSeconds: parsed });
                              }
                            }}
                            className="w-32 h-11 font-mono text-center bg-secondary/50"
                            placeholder="e.g. 1:30"
                          />
                          <span className="text-sm text-muted-foreground">Format: 30s, 1:30, or 1m 30s</span>
                        </div>
                      </div>

                      {/* Song Lyrics */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs uppercase tracking-widest text-muted-foreground">Lyrics/Concept</Label>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleAISuggest("lyrics", idx)}
                            disabled={suggestingField === "lyrics"}
                            className="text-xs h-auto px-2 py-1 text-primary hover:text-primary/80"
                          >
                            {suggestingField === "lyrics" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                          </Button>
                        </div>
                        <Textarea
                          placeholder="Enter lyrics, lyrical themes, or concepts for this track..."
                          value={song.lyrics}
                          onChange={(e) => updateAlbumSong(idx, { lyrics: e.target.value })}
                          className="min-h-[80px] text-base leading-relaxed bg-card border border-white/10 rounded-xl focus-visible:ring-1 focus-visible:ring-primary resize-none p-4"
                        />
                      </div>

                      {/* Song Genres */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs uppercase tracking-widest text-muted-foreground">Genres</Label>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleAISuggest("genres", idx)}
                            disabled={suggestingField === "genres"}
                            className="text-xs h-auto px-2 py-1 text-primary hover:text-primary/80"
                          >
                            {suggestingField === "genres" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                          </Button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {genres.map((genre) => (
                            <Badge
                              key={genre}
                              variant={song.selectedGenres.includes(genre) ? "default" : "outline"}
                              className="cursor-pointer"
                              onClick={() => {
                                const selected = song.selectedGenres.includes(genre)
                                  ? song.selectedGenres.filter((g) => g !== genre)
                                  : [...song.selectedGenres, genre];
                                updateAlbumSong(idx, { selectedGenres: selected });
                              }}
                            >
                              {genre}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      {/* Song Languages */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs uppercase tracking-widest text-muted-foreground">Vocal Languages</Label>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleAISuggest("vocal_languages", idx)}
                            disabled={suggestingField === "vocal_languages"}
                            className="text-xs h-auto px-2 py-1 text-primary hover:text-primary/80"
                          >
                            {suggestingField === "vocal_languages" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                          </Button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {languages.map((lang) => (
                            <Badge
                              key={lang}
                              variant={song.vocalLanguages.includes(lang) ? "default" : "outline"}
                              className="cursor-pointer"
                              onClick={() => {
                                const selected = song.vocalLanguages.includes(lang)
                                  ? song.vocalLanguages.filter((l) => l !== lang)
                                  : [...song.vocalLanguages, lang];
                                updateAlbumSong(idx, { vocalLanguages: selected });
                              }}
                            >
                              {lang}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      {/* Song Artist Inspiration */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs uppercase tracking-widest text-muted-foreground">Artist Inspiration</Label>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleAISuggest("artist_inspiration", idx)}
                            disabled={suggestingField === "artist_inspiration"}
                            className="text-xs h-auto px-2 py-1 text-primary hover:text-primary/80"
                          >
                            {suggestingField === "artist_inspiration" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                          </Button>
                        </div>
                        <Input
                          placeholder="Artists, producers, vocal references..."
                          value={song.artistInspiration}
                          onChange={(e) => updateAlbumSong(idx, { artistInspiration: e.target.value })}
                          className="h-11 bg-secondary/40 border-white/10"
                        />
                      </div>

                      {/* Song Video Style */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs uppercase tracking-widest text-muted-foreground">Video Style</Label>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleAISuggest("video_style", idx)}
                            disabled={suggestingField === "video_style"}
                            className="text-xs h-auto px-2 py-1 text-primary hover:text-primary/80"
                          >
                            {suggestingField === "video_style" ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                          </Button>
                        </div>
                        <Input
                          placeholder="Visual direction for this specific track"
                          value={song.videoStyle}
                          onChange={(e) => updateAlbumSong(idx, { videoStyle: e.target.value })}
                          className="h-11 bg-secondary/40 border-white/10"
                        />
                      </div>

                      {/* Close Button */}
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => setExpandedSongIndex(null)}
                        className="w-full text-muted-foreground hover:text-foreground"
                      >
                        Done Configuring Track {idx + 1}
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          {/* Title */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                {mode === "single" ? "Track Name" : "Album Name"}
              </Label>
              <SuggestButton field="title" />
            </div>
            <Input
              placeholder={`Enter ${mode === "single" ? "track" : "album"} name or let AI suggest...`}
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="h-14 text-lg bg-transparent border-0 border-b-2 border-white/10 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary transition-colors"
              data-testid="title-input"
            />
          </div>

          {mode === "single" && (
          <>
          {/* Music Prompt */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                  Music Description
                </Label>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">Required</span>
              </div>
              <SuggestButton field="music_prompt" />
            </div>
            <Textarea
              placeholder="Describe the mood, energy, atmosphere, instruments... Be as detailed as you like. This is the main input that shapes your music."
              value={formData.musicPrompt}
              onChange={(e) => setFormData({ ...formData, musicPrompt: e.target.value })}
              className="min-h-[140px] text-base leading-relaxed bg-card border border-white/10 rounded-xl focus-visible:ring-1 focus-visible:ring-primary focus-visible:border-primary resize-none p-4"
              data-testid="music-prompt-input"
            />
          </div>

          {/* Genres */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Genres</Label>
                {aiSuggestedFields.has("genres") && (
                  <Badge variant="outline" className="border-purple-500/50 bg-purple-500/10 text-purple-400 text-xs gap-1">
                    <Sparkles className="w-3 h-3" />
                    AI Selected
                  </Badge>
                )}
              </div>
              <SuggestButton field="genres" />
            </div>
            
            {/* Selected genres - highlighted if AI suggested */}
            {formData.selectedGenres.length > 0 && (
              <div className={`flex flex-wrap gap-2 p-3 rounded-lg border transition-all ${
                aiSuggestedFields.has("genres")
                  ? "bg-gradient-to-r from-purple-500/10 to-pink-500/10 border-purple-500/40"
                  : "bg-primary/5 border-primary/20"
              }`}>
                {formData.selectedGenres.map((genre) => (
                  <Badge
                    key={genre}
                    className={`cursor-pointer pr-1 transition-all ${
                      aiSuggestedFields.has("genres")
                        ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600"
                        : "bg-primary text-primary-foreground hover:bg-primary/80"
                    }`}
                    onClick={() => toggleGenre(genre)}
                  >
                    {genre}
                    <X className="w-3 h-3 ml-1" />
                  </Badge>
                ))}
              </div>
            )}
            
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search genres..."
                value={genreSearch}
                onChange={(e) => setGenreSearch(e.target.value)}
                className="pl-10 h-11 bg-secondary/50 border-0 rounded-lg"
                data-testid="genre-search"
              />
              {genreSearch && (
                <button
                  onClick={() => setGenreSearch("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                >
                  <X className="w-4 h-4 text-muted-foreground hover:text-foreground" />
                </button>
              )}
            </div>

            {/* Genre list */}
            <div className="flex flex-wrap gap-2" data-testid="genres-selection">
              {displayedGenres.map((genre) => (
                <Badge
                  key={genre}
                  variant={formData.selectedGenres.includes(genre) ? "default" : "outline"}
                  className={`badge-interactive ${
                    formData.selectedGenres.includes(genre)
                      ? "bg-primary text-primary-foreground"
                      : "border-white/10 hover:border-white/20 hover:bg-white/5"
                  }`}
                  onClick={() => toggleGenre(genre)}
                  data-testid={`genre-${genre.toLowerCase().replace(/\s+/g, '-')}`}
                >
                  {genre}
                </Badge>
              ))}
            </div>

            {filteredGenres.length > 20 && !showAllGenres && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAllGenres(true)}
                className="text-muted-foreground"
              >
                <ChevronDown className="w-4 h-4 mr-1" />
                Show all {filteredGenres.length} genres
              </Button>
            )}
          </div>

          {/* Duration - Only for single */}
          {mode === "single" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <Label className="text-xs uppercase tracking-widest text-muted-foreground">Duration</Label>
                  {aiSuggestedFields.has("duration") && (
                    <Badge variant="outline" className="border-purple-500/50 bg-purple-500/10 text-purple-400 text-xs gap-1">
                      <Sparkles className="w-3 h-3" />
                      AI Suggested
                    </Badge>
                  )}
                </div>
                <Input
                  value={durationInput}
                  onChange={handleDurationInputChange}
                  onBlur={handleDurationInputBlur}
                  onFocus={(e) => e.target.select()}
                  className={`w-32 h-11 font-mono text-center transition-all ${
                    aiSuggestedFields.has("duration")
                      ? "bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/40 text-purple-300"
                      : "bg-secondary/50"
                  }`}
                  placeholder="e.g. 1:30 or 90 or 1h 5m"
                  data-testid="duration-input"
                />
              </div>
              <Slider
                value={[formData.durationSeconds]}
                onValueChange={(v) => {
                  const secs = v[0];
                  setFormData((prev) => ({ ...prev, durationSeconds: secs }));
                  setDurationInput(formatDuration(secs));
                }}
                max={72000}
                min={10}
                step={1}
                className="w-full"
                data-testid="duration-slider"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>10s</span>
                <span>20 hours</span>
              </div>
            </div>
          )}

          {/* Vocal Languages */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Vocal Language</Label>
                {aiSuggestedFields.has("vocal_languages") && (
                  <Badge variant="outline" className="border-purple-500/50 bg-purple-500/10 text-purple-400 text-xs gap-1">
                    <Sparkles className="w-3 h-3" />
                    AI Selected
                  </Badge>
                )}
              </div>
              <SuggestButton field="vocal_languages" />
            </div>
            
            {/* Selected languages - highlighted if AI suggested */}
            {formData.vocalLanguages.length > 0 && (
              <div className={`flex flex-wrap gap-2 p-3 rounded-lg border transition-all ${
                aiSuggestedFields.has("vocal_languages")
                  ? "bg-gradient-to-r from-purple-500/10 to-pink-500/10 border-purple-500/40"
                  : "bg-primary/5 border-primary/20"
              }`}>
                {formData.vocalLanguages.map((lang) => (
                  <Badge
                    key={lang}
                    className={`cursor-pointer pr-1 transition-all ${
                      aiSuggestedFields.has("vocal_languages")
                        ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600"
                        : "bg-primary text-primary-foreground hover:bg-primary/80"
                    }`}
                    onClick={() => toggleLanguage(lang)}
                  >
                    {lang}
                    <X className="w-3 h-3 ml-1" />
                  </Badge>
                ))}
              </div>
            )}
            
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search or view AI suggestion..."
                value={languageSearch}
                onChange={(e) => setLanguageSearch(e.target.value)}
                className="pl-10 h-11 bg-secondary/50 border-0 rounded-lg"
                data-testid="language-search"
              />
              {languageSearch && (
                <button
                  onClick={() => setLanguageSearch("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                >
                  <X className="w-4 h-4 text-muted-foreground hover:text-foreground" />
                </button>
              )}
            </div>

            {/* Language grid */}
            <div className="flex flex-wrap gap-2" data-testid="languages-selection">
              {(languageSearch ? languages.filter((l) => l.toLowerCase().includes(languageSearch.toLowerCase())) : languages).map((lang) => (
                <Badge
                  key={lang}
                  variant={formData.vocalLanguages.includes(lang) ? "default" : "outline"}
                  className={`badge-interactive ${
                    formData.vocalLanguages.includes(lang)
                      ? "bg-primary text-primary-foreground"
                      : "border-white/10 hover:border-white/20 hover:bg-white/5"
                  }`}
                  onClick={() => toggleLanguage(lang)}
                  data-testid={`lang-${lang.toLowerCase().replace(/[\s()]/g, '-')}`}
                >
                  {lang}
                </Badge>
              ))}
            </div>
          </div>

          {/* Lyrics */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">Lyrics / Vocal Theme</Label>
              <SuggestButton field="lyrics" />
            </div>
            <Textarea
              placeholder="Enter themes, stories, or actual lyrics..."
              value={formData.lyrics}
              onChange={(e) => setFormData({ ...formData, lyrics: e.target.value })}
              className="min-h-[100px] bg-card border border-white/10 rounded-xl focus-visible:ring-1 focus-visible:ring-primary resize-none p-4"
              data-testid="lyrics-input"
            />
          </div>

          {/* Artist Inspiration */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">Artist Inspiration</Label>
              <SuggestButton field="artist_inspiration" />
            </div>
            <Input
              placeholder="e.g., Tame Impala, The Weeknd, Bonobo..."
              value={formData.artistInspiration}
              onChange={(e) => setFormData({ ...formData, artistInspiration: e.target.value })}
              className="h-12 bg-transparent border-0 border-b-2 border-white/10 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary"
              data-testid="artist-inspiration-input"
            />
            {!formData.artistInspiration && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {artists.slice(0, 10).map((artist) => (
                  <button
                    key={artist}
                    type="button"
                    onClick={() => setFormData({ ...formData, artistInspiration: artist })}
                    className="text-xs px-2 py-1 rounded-md bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                  >
                    {artist}
                  </button>
                ))}
              </div>
            )}
          </div>
          </>
          )}

          {/* Video Toggle */}
          <div className="flex items-center justify-between p-5 rounded-2xl bg-card border border-white/5">
            <div>
              <Label className="font-medium">Generate Video</Label>
              <p className="text-sm text-muted-foreground mt-1">Create a music video with Sora 2 AI</p>
            </div>
            <Switch
              checked={formData.generateVideo}
              onCheckedChange={(checked) => setFormData({ ...formData, generateVideo: checked })}
              data-testid="video-toggle"
            />
          </div>

          {/* Video Style */}
          {formData.generateVideo && (
            <div className="space-y-3 animate-fade-in">
              <div className="flex items-center justify-between">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                  {mode === "single" ? "Video Style" : "Default Video Style"}
                </Label>
                <SuggestButton field="video_style" />
              </div>
              <Input
                placeholder={mode === "single" ? "Describe the visual style..." : "Used when a track does not specify video style"}
                value={formData.videoStyle}
                onChange={(e) => setFormData({ ...formData, videoStyle: e.target.value })}
                className="h-12 bg-transparent border-0 border-b-2 border-white/10 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary"
                data-testid="video-style-input"
              />
              <div className="flex flex-wrap gap-1.5">
                {videoStyles.slice(0, 6).map((style) => (
                  <button
                    key={style}
                    type="button"
                    onClick={() => setFormData({ ...formData, videoStyle: style })}
                    className="text-xs px-2 py-1 rounded-md bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                  >
                    {style}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Submit */}
          <Button
            size="lg"
            className="w-full h-16 text-lg font-semibold btn-primary glow-primary rounded-2xl"
            onClick={handleSubmit}
            disabled={loading}
            data-testid="generate-btn"
          >
            {loading ? (
              <span className="flex items-center gap-3">
                <Loader2 className="w-5 h-5 animate-spin" />
                {mode === "single" ? "Creating your track..." : "Creating your album..."}
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Music className="w-5 h-5" />
                {mode === "single" ? "Generate Track" : "Generate Album"}
              </span>
            )}
          </Button>
        </div>

        {/* Result */}
        {result && (
          <div className="mt-16 animate-fade-in" data-testid="result-section">
            <div className="border-t border-white/10 pt-12">
              <h2 className="font-display text-2xl font-bold mb-8">
                {result.type === "song" ? "Your Track" : "Your Album"}
              </h2>

              {result.type === "song" ? (
                <TrackCard
                  track={result.data}
                  isPlaying={playingTrack === result.data.id}
                  onPlay={() => playTrack(result.data.audio_url, result.data.id)}
                />
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center gap-5 mb-8 p-5 rounded-2xl glass">
                    <img
                      src={result.data.cover_art_url}
                      alt={result.data.title}
                      className="w-28 h-28 rounded-xl object-cover shadow-lg"
                    />
                    <div className="flex-1">
                      <h3 className="text-2xl font-bold">{result.data.title}</h3>
                      <p className="text-muted-foreground mt-1">{result.data.songs?.length || 0} tracks</p>
                      <div className="flex items-center gap-3 mt-4">
                        <Button
                          type="button"
                          size="sm"
                          onClick={async () => {
                            try {
                              const response = await axios.get(`${API}/albums/${result.data.id}/download?user_id=${user.id}`, {
                                responseType: "blob",
                              });
                              const url = window.URL.createObjectURL(new Blob([response.data]));
                              const link = document.createElement("a");
                              link.href = url;
                              link.setAttribute("download", `${result.data.title}.zip`);
                              document.body.appendChild(link);
                              link.click();
                              link.parentNode.removeChild(link);
                              window.URL.revokeObjectURL(url);
                              toast.success("Album downloaded!");
                            } catch (error) {
                              toast.error("Failed to download album");
                            }
                          }}
                          className="gap-2"
                        >
                          <Download className="w-4 h-4" />
                          Download Album
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => generateAlbumVideos(result.data.id)}
                          disabled={albumVideoLoading}
                          className="gap-2"
                        >
                          {albumVideoLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Film className="w-4 h-4" />
                          )}
                          Generate Videos
                        </Button>
                      </div>
                    </div>
                  </div>
                  {result.data.songs?.map((track, i) => (
                    <TrackCard
                      key={track.id}
                      track={track}
                      index={i + 1}
                      isPlaying={playingTrack === track.id}
                      onPlay={() => playTrack(track.audio_url, track.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const TrackCard = ({ track, index, isPlaying, onPlay }) => {
  const [generatingVideo, setGeneratingVideo] = useState(false);
  const [videoUrl, setVideoUrl] = useState(track.video_url || null);
  const [showVideo, setShowVideo] = useState(false);

  const formatTime = (s) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;

  const generateVideo = async () => {
    try {
      setGeneratingVideo(true);
      const response = await axios.post(`${API}/songs/${track.id}/generate-video?user_id=${track.user_id}`);
      if (response.data.video_url) {
        setVideoUrl(response.data.video_url);
        toast.success("Video generated successfully!");
      } else if (response.data.status === "processing") {
        toast.success(response.data.message || "Video generation started");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to generate video");
    } finally {
      setGeneratingVideo(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="track-card flex items-center gap-4 p-4 group" data-testid={`track-card-${track.id}`}>
        {/* Cover / Play */}
        <div className="relative w-16 h-16 rounded-lg overflow-hidden flex-shrink-0">
          <img src={track.cover_art_url} alt={track.title} className="w-full h-full object-cover" />
          <button
            onClick={onPlay}
            className="absolute inset-0 bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
            data-testid={`play-btn-${track.id}`}
          >
            {isPlaying ? <Pause className="w-6 h-6 text-white" /> : <Play className="w-6 h-6 text-white" />}
          </button>
          {isPlaying && (
            <div className="absolute inset-0 bg-black/60 flex items-center justify-center gap-0.5">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="w-1 bg-primary rounded-full waveform-bar" style={{ height: '60%' }} />
              ))}
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          {index && <span className="text-xs text-muted-foreground font-mono">Track {index}</span>}
          <h4 className="font-medium truncate">{track.title}</h4>
          <p className="text-sm text-muted-foreground font-mono">{formatTime(track.duration_seconds)}</p>
          {track.lyrics && (
            <p className="text-xs text-muted-foreground line-clamp-2 mt-1">{track.lyrics}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Generate Video Button */}
          <Button
            type="button"
            size="icon"
            variant="ghost"
            onClick={generateVideo}
            disabled={generatingVideo}
            className="h-10 w-10 p-0 hover:bg-white/5"
            title="Generate video for this track"
          >
            {generatingVideo ? (
              <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
            ) : (
              <Film className="w-5 h-5 text-muted-foreground hover:text-foreground" />
            )}
          </Button>

          {/* Download Button */}
          <a
            href={track.audio_url}
            download
            className="p-2.5 rounded-lg hover:bg-white/5 transition-colors"
            data-testid={`download-btn-${track.id}`}
            title="Download audio"
          >
            <Download className="w-5 h-5 text-muted-foreground hover:text-foreground" />
          </a>
        </div>
      </div>

      {/* Video Player */}
      {videoUrl && (
        <div className="rounded-xl overflow-hidden border border-white/10 bg-black">
          <button
            type="button"
            onClick={() => setShowVideo(!showVideo)}
            className="w-full p-3 flex items-center justify-between hover:bg-white/5 transition-colors"
          >
            <span className="text-sm font-medium flex items-center gap-2">
              <Film className="w-4 h-4" />
              Video Preview
            </span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showVideo ? "rotate-180" : ""}`} />
          </button>
          {showVideo && (
            <div className="aspect-video bg-black">
              <video
                src={videoUrl}
                controls
                className="w-full h-full"
                preload="metadata"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export { CreateMusicPage };
