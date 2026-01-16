import { useState, useEffect, useCallback } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Slider } from "../components/ui/slider";
import { Switch } from "../components/ui/switch";
import { Badge } from "../components/ui/badge";
import { Sparkles, Music, Disc, Play, Pause, Download, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { API } from "../App";

export default function CreateMusicPage({ user }) {
  const [mode, setMode] = useState("single");
  const [loading, setLoading] = useState(false);
  const [suggestingField, setSuggestingField] = useState(null);
  const [genres, setGenres] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [result, setResult] = useState(null);
  const [playingTrack, setPlayingTrack] = useState(null);
  const [audioRef, setAudioRef] = useState(null);

  const [formData, setFormData] = useState({
    title: "",
    musicPrompt: "",
    selectedGenres: [],
    durationSeconds: 180,
    vocalLanguages: [],
    lyrics: "",
    artistInspiration: "",
    generateVideo: false,
    videoStyle: "",
    numSongs: 3,
  });

  useEffect(() => {
    fetchOptions();
  }, []);

  const fetchOptions = async () => {
    try {
      const [genresRes, langsRes] = await Promise.all([
        axios.get(`${API}/genres`),
        axios.get(`${API}/languages`),
      ]);
      setGenres(genresRes.data.genres);
      setLanguages(langsRes.data.languages);
    } catch (error) {
      console.error("Failed to fetch options:", error);
    }
  };

  const formatDuration = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return { h, m, s };
  };

  const parseDuration = (h, m, s) => {
    return (parseInt(h) || 0) * 3600 + (parseInt(m) || 0) * 60 + (parseInt(s) || 0);
  };

  const duration = formatDuration(formData.durationSeconds);

  const handleDurationChange = (field, value) => {
    const newDuration = { ...duration, [field]: parseInt(value) || 0 };
    setFormData({
      ...formData,
      durationSeconds: parseDuration(newDuration.h, newDuration.m, newDuration.s),
    });
  };

  const handleSliderChange = (value) => {
    setFormData({ ...formData, durationSeconds: value[0] });
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

  const handleAISuggest = async (field) => {
    setSuggestingField(field);
    try {
      const response = await axios.post(`${API}/suggest`, {
        field,
        current_value: formData[field === "genres" ? "selectedGenres" : field === "vocal_languages" ? "vocalLanguages" : field === "music_prompt" ? "musicPrompt" : field === "artist_inspiration" ? "artistInspiration" : field === "video_style" ? "videoStyle" : field] || "",
        context: {
          music_prompt: formData.musicPrompt,
          genres: formData.selectedGenres,
          lyrics: formData.lyrics,
        },
      });

      const suggestion = response.data.suggestion;
      
      if (field === "genres") {
        const suggestedGenres = suggestion.split(",").map((g) => g.trim());
        const validGenres = suggestedGenres.filter((g) => genres.includes(g));
        if (validGenres.length > 0) {
          setFormData({ ...formData, selectedGenres: validGenres });
          toast.success("Genres suggested!");
        }
      } else if (field === "vocal_languages") {
        const suggestedLangs = suggestion.split(",").map((l) => l.trim());
        const validLangs = suggestedLangs.filter((l) => languages.includes(l));
        if (validLangs.length > 0) {
          setFormData({ ...formData, vocalLanguages: validLangs });
          toast.success("Languages suggested!");
        } else if (suggestion.toLowerCase().includes("instrumental")) {
          setFormData({ ...formData, vocalLanguages: ["Instrumental"] });
          toast.success("Suggested: Instrumental");
        }
      } else {
        const fieldMap = {
          music_prompt: "musicPrompt",
          artist_inspiration: "artistInspiration",
          video_style: "videoStyle",
        };
        const key = fieldMap[field] || field;
        setFormData({ ...formData, [key]: suggestion });
        toast.success(`${field.replace("_", " ")} suggested!`);
      }
    } catch (error) {
      toast.error("Failed to get suggestion");
    } finally {
      setSuggestingField(null);
    }
  };

  const handleSubmit = async () => {
    if (!formData.musicPrompt.trim()) {
      toast.error("Please describe your music idea");
      return;
    }

    setLoading(true);
    try {
      if (mode === "single") {
        const response = await axios.post(`${API}/songs/create`, {
          title: formData.title,
          music_prompt: formData.musicPrompt,
          genres: formData.selectedGenres,
          duration_seconds: formData.durationSeconds,
          vocal_languages: formData.vocalLanguages,
          lyrics: formData.lyrics,
          artist_inspiration: formData.artistInspiration,
          generate_video: formData.generateVideo,
          video_style: formData.videoStyle,
          mode: "single",
          user_id: user.id,
        });
        setResult({ type: "song", data: response.data });
        toast.success("Song created successfully!");
      } else {
        const response = await axios.post(`${API}/albums/create`, {
          title: formData.title,
          music_prompt: formData.musicPrompt,
          genres: formData.selectedGenres,
          vocal_languages: formData.vocalLanguages,
          lyrics: formData.lyrics,
          artist_inspiration: formData.artistInspiration,
          generate_video: formData.generateVideo,
          video_style: formData.videoStyle,
          num_songs: formData.numSongs,
          user_id: user.id,
        });
        setResult({ type: "album", data: response.data });
        toast.success("Album created successfully!");
      }
    } catch (error) {
      toast.error("Failed to create music");
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

  const SuggestButton = ({ field, disabled }) => (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="text-primary hover:text-primary/80 h-8 px-2"
      onClick={() => handleAISuggest(field)}
      disabled={suggestingField === field || disabled}
      data-testid={`suggest-${field}-btn`}
    >
      {suggestingField === field ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Sparkles className="w-4 h-4" />
      )}
      <span className="ml-1 text-xs">AI Suggest</span>
    </Button>
  );

  return (
    <div className="min-h-screen p-8" data-testid="create-music-page">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Create Music</h1>
          <p className="text-muted-foreground">
            Describe your vision and let AI bring it to life
          </p>
        </div>

        {/* Mode Selection */}
        <div className="flex gap-4 mb-8" data-testid="mode-selection">
          <button
            type="button"
            onClick={() => setMode("single")}
            className={`flex-1 p-6 rounded-xl border transition-all ${
              mode === "single"
                ? "border-primary bg-primary/5"
                : "border-white/10 hover:border-white/20"
            }`}
            data-testid="single-mode-btn"
          >
            <Music className={`w-8 h-8 mb-3 ${mode === "single" ? "text-primary" : "text-muted-foreground"}`} />
            <h3 className="font-semibold mb-1">Single Song</h3>
            <p className="text-sm text-muted-foreground">Create one track</p>
          </button>
          <button
            type="button"
            onClick={() => setMode("album")}
            className={`flex-1 p-6 rounded-xl border transition-all ${
              mode === "album"
                ? "border-primary bg-primary/5"
                : "border-white/10 hover:border-white/20"
            }`}
            data-testid="album-mode-btn"
          >
            <Disc className={`w-8 h-8 mb-3 ${mode === "album" ? "text-primary" : "text-muted-foreground"}`} />
            <h3 className="font-semibold mb-1">Album</h3>
            <p className="text-sm text-muted-foreground">Create multiple tracks</p>
          </button>
        </div>

        {/* Form */}
        <div className="space-y-8">
          {/* Album tracks count */}
          {mode === "album" && (
            <div className="p-4 rounded-xl bg-card border border-white/5 animate-fade-in">
              <div className="flex items-center justify-between">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                  Number of Songs
                </Label>
              </div>
              <Input
                type="number"
                min={2}
                max={20}
                value={formData.numSongs}
                onChange={(e) => setFormData({ ...formData, numSongs: parseInt(e.target.value) || 3 })}
                className="mt-2 bg-transparent border-b border-white/20 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary w-24"
                data-testid="num-songs-input"
              />
            </div>
          )}

          {/* Title */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                {mode === "single" ? "Track Name" : "Album Name"}
              </Label>
              <SuggestButton field="title" />
            </div>
            <Input
              placeholder={mode === "single" ? "Enter track name (optional)" : "Enter album name (optional)"}
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="bg-transparent border-b border-white/20 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary h-12 text-lg"
              data-testid="title-input"
            />
          </div>

          {/* Music Prompt */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                Music Description *
              </Label>
              <SuggestButton field="music_prompt" />
            </div>
            <Textarea
              placeholder="Describe the mood, energy, atmosphere, imagery... Be as detailed as you like."
              value={formData.musicPrompt}
              onChange={(e) => setFormData({ ...formData, musicPrompt: e.target.value })}
              className="min-h-32 bg-transparent border border-white/10 rounded-xl focus-visible:ring-0 focus-visible:border-primary resize-none"
              data-testid="music-prompt-input"
            />
          </div>

          {/* Genres */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                Genres
              </Label>
              <SuggestButton field="genres" />
            </div>
            <div className="flex flex-wrap gap-2" data-testid="genres-selection">
              {genres.map((genre) => (
                <Badge
                  key={genre}
                  variant={formData.selectedGenres.includes(genre) ? "default" : "outline"}
                  className={`cursor-pointer transition-all ${
                    formData.selectedGenres.includes(genre)
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-white/5"
                  }`}
                  onClick={() => toggleGenre(genre)}
                  data-testid={`genre-${genre.toLowerCase()}`}
                >
                  {genre}
                </Badge>
              ))}
            </div>
          </div>

          {/* Duration - Only for single mode */}
          {mode === "single" && (
            <div className="space-y-4">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                Duration
              </Label>
              <div className="space-y-6">
                <Slider
                  value={[formData.durationSeconds]}
                  onValueChange={handleSliderChange}
                  max={600}
                  min={30}
                  step={1}
                  className="w-full"
                  data-testid="duration-slider"
                />
                <div className="flex items-center gap-4 font-mono" data-testid="duration-inputs">
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min={0}
                      max={9}
                      value={duration.h}
                      onChange={(e) => handleDurationChange("h", e.target.value)}
                      className="w-16 text-center bg-secondary border-0"
                      data-testid="duration-hours"
                    />
                    <span className="text-muted-foreground">HH</span>
                  </div>
                  <span className="text-2xl text-muted-foreground">:</span>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min={0}
                      max={59}
                      value={duration.m}
                      onChange={(e) => handleDurationChange("m", e.target.value)}
                      className="w-16 text-center bg-secondary border-0"
                      data-testid="duration-minutes"
                    />
                    <span className="text-muted-foreground">MM</span>
                  </div>
                  <span className="text-2xl text-muted-foreground">:</span>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min={0}
                      max={59}
                      value={duration.s}
                      onChange={(e) => handleDurationChange("s", e.target.value)}
                      className="w-16 text-center bg-secondary border-0"
                      data-testid="duration-seconds"
                    />
                    <span className="text-muted-foreground">SS</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Vocal Languages */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                Vocal Language(s)
              </Label>
              <SuggestButton field="vocal_languages" />
            </div>
            <div className="flex flex-wrap gap-2" data-testid="languages-selection">
              {languages.map((lang) => (
                <Badge
                  key={lang}
                  variant={formData.vocalLanguages.includes(lang) ? "default" : "outline"}
                  className={`cursor-pointer transition-all ${
                    formData.vocalLanguages.includes(lang)
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-white/5"
                  }`}
                  onClick={() => toggleLanguage(lang)}
                  data-testid={`lang-${lang.toLowerCase()}`}
                >
                  {lang}
                </Badge>
              ))}
            </div>
          </div>

          {/* Lyrics */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                Lyrics or Vocal Theme
              </Label>
              <SuggestButton field="lyrics" />
            </div>
            <Textarea
              placeholder="Enter themes, stories, or full lyrics..."
              value={formData.lyrics}
              onChange={(e) => setFormData({ ...formData, lyrics: e.target.value })}
              className="min-h-32 bg-transparent border border-white/10 rounded-xl focus-visible:ring-0 focus-visible:border-primary resize-none"
              data-testid="lyrics-input"
            />
          </div>

          {/* Artist Inspiration */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                Artist Inspiration
              </Label>
              <SuggestButton field="artist_inspiration" />
            </div>
            <Input
              placeholder="e.g., Tame Impala, The Weeknd, M83"
              value={formData.artistInspiration}
              onChange={(e) => setFormData({ ...formData, artistInspiration: e.target.value })}
              className="bg-transparent border-b border-white/20 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary h-12"
              data-testid="artist-inspiration-input"
            />
          </div>

          {/* Video Toggle */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-card border border-white/5">
            <div>
              <Label className="text-sm font-medium">Generate Video</Label>
              <p className="text-xs text-muted-foreground mt-1">
                Create a music video for your track
              </p>
            </div>
            <Switch
              checked={formData.generateVideo}
              onCheckedChange={(checked) => setFormData({ ...formData, generateVideo: checked })}
              data-testid="video-toggle"
            />
          </div>

          {/* Video Style */}
          {formData.generateVideo && (
            <div className="space-y-2 animate-fade-in">
              <div className="flex items-center justify-between">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">
                  Video Style
                </Label>
                <SuggestButton field="video_style" />
              </div>
              <Input
                placeholder="e.g., Cyberpunk cityscape, Abstract visualizer, Nature scenes"
                value={formData.videoStyle}
                onChange={(e) => setFormData({ ...formData, videoStyle: e.target.value })}
                className="bg-transparent border-b border-white/20 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary h-12"
                data-testid="video-style-input"
              />
            </div>
          )}

          {/* Submit Button */}
          <Button
            size="lg"
            className="w-full h-14 bg-primary text-primary-foreground hover:bg-primary/90 font-semibold text-lg glow-primary"
            onClick={handleSubmit}
            disabled={loading}
            data-testid="generate-btn"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                {mode === "single" ? "Creating Song..." : "Creating Album..."}
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Music className="w-5 h-5" />
                {mode === "single" ? "Generate Song" : "Generate Album"}
              </span>
            )}
          </Button>
        </div>

        {/* Result Section */}
        {result && (
          <div className="mt-12 animate-fade-in" data-testid="result-section">
            <div className="border-t border-white/10 pt-12">
              <h2 className="text-2xl font-bold mb-6">
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
                  <div className="flex items-center gap-4 mb-6">
                    <img
                      src={result.data.cover_art_url}
                      alt={result.data.title}
                      className="w-24 h-24 rounded-xl object-cover"
                    />
                    <div>
                      <h3 className="text-xl font-bold">{result.data.title}</h3>
                      <p className="text-muted-foreground">
                        {result.data.songs?.length || 0} tracks
                      </p>
                    </div>
                  </div>
                  {result.data.songs?.map((track, index) => (
                    <TrackCard
                      key={track.id}
                      track={track}
                      index={index + 1}
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
  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div
      className="flex items-center gap-4 p-4 rounded-xl bg-card border border-white/5 hover:border-white/10 transition-all group"
      data-testid={`track-card-${track.id}`}
    >
      <div className="relative w-16 h-16 rounded-lg overflow-hidden flex-shrink-0">
        <img
          src={track.cover_art_url}
          alt={track.title}
          className="w-full h-full object-cover"
        />
        <button
          onClick={onPlay}
          className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          data-testid={`play-btn-${track.id}`}
        >
          {isPlaying ? (
            <Pause className="w-6 h-6 text-white" />
          ) : (
            <Play className="w-6 h-6 text-white" />
          )}
        </button>
      </div>

      <div className="flex-1 min-w-0">
        {index && (
          <span className="text-xs text-muted-foreground font-mono">
            Track {index}
          </span>
        )}
        <h4 className="font-medium truncate">{track.title}</h4>
        <p className="text-sm text-muted-foreground font-mono">
          {formatTime(track.duration_seconds)}
        </p>
      </div>

      <a
        href={track.audio_url}
        download
        className="p-2 rounded-lg hover:bg-white/5 transition-colors"
        data-testid={`download-btn-${track.id}`}
      >
        <Download className="w-5 h-5 text-muted-foreground hover:text-foreground" />
      </a>
    </div>
  );
};

export { CreateMusicPage };
