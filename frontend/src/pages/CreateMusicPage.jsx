import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Slider } from "../components/ui/slider";
import { Switch } from "../components/ui/switch";
import { Badge } from "../components/ui/badge";
import { Sparkles, Music, Disc, Play, Pause, Download, Loader2, Search, X, Volume2, ChevronDown } from "lucide-react";
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
  });

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

  const handleAISuggest = async (field) => {
    setSuggestingField(field);
    try {
      const response = await axios.post(`${API}/suggest`, {
        field,
        current_value: getFieldValue(field),
        context: {
          music_prompt: formData.musicPrompt,
          genres: formData.selectedGenres,
          lyrics: formData.lyrics,
          artist_inspiration: formData.artistInspiration,
        },
      });
      applySuggestion(field, response.data.suggestion);
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

  const handleSubmit = async () => {
    if (!formData.musicPrompt.trim()) {
      toast.error("Please describe your music idea");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const endpoint = mode === "single" ? "/songs/create" : "/albums/create";
      const payload = {
        title: formData.title,
        music_prompt: formData.musicPrompt,
        genres: formData.selectedGenres,
        vocal_languages: formData.vocalLanguages,
        lyrics: formData.lyrics,
        artist_inspiration: formData.artistInspiration,
        generate_video: formData.generateVideo,
        video_style: formData.videoStyle,
        user_id: user.id,
        ...(mode === "single" 
          ? { duration_seconds: formData.durationSeconds, mode: "single" }
          : { num_songs: formData.numSongs }
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

  const AISuggestIndicator = ({ field }) => {
    if (!aiSuggestedFields.has(field)) return null;
    return (
      <div className="absolute -top-2 -right-2 flex items-center gap-1 bg-gradient-to-r from-purple-500 to-pink-500 text-white px-2 py-1 rounded-full text-xs font-semibold animate-pulse">
        <Sparkles className="w-3 h-3" />
        AI Suggested
      </div>
    );
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
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Video Style</Label>
                <SuggestButton field="video_style" />
              </div>
              <Input
                placeholder="Describe the visual style..."
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
                    <div>
                      <h3 className="text-2xl font-bold">{result.data.title}</h3>
                      <p className="text-muted-foreground mt-1">{result.data.songs?.length || 0} tracks</p>
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
  const formatTime = (s) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;

  return (
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
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <a
          href={track.audio_url}
          download
          className="p-2.5 rounded-lg hover:bg-white/5 transition-colors"
          data-testid={`download-btn-${track.id}`}
        >
          <Download className="w-5 h-5 text-muted-foreground hover:text-foreground" />
        </a>
      </div>
    </div>
  );
};

export { CreateMusicPage };
