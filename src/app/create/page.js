"use client";

import { useMemo, useState } from "react";

const GENRE_OPTIONS = [
  "Electronic",
  "Ambient",
  "Cinematic",
  "House",
  "Techno",
  "Pop",
  "Lo-fi",
  "Hip-Hop",
  "R&B",
  "Rock",
  "Orchestral",
  "Afrobeats",
  "Trap",
  "Indie",
  "Drum and Bass",
];

const MOOD_OPTIONS = [
  "Uplifting",
  "Dark",
  "Dreamy",
  "Aggressive",
  "Melancholic",
  "Energetic",
  "Calm",
  "Euphoric",
  "Nostalgic",
  "Futuristic",
];

const VOCAL_LANG_OPTIONS = ["Instrumental", "English", "Hindi", "Spanish", "French", "Japanese", "Korean"];
const VOCAL_STYLE_OPTIONS = ["None", "Clean Lead", "Breathy", "Rap", "Choral", "Robotic", "Falsetto"];
const STRUCTURE_OPTIONS = ["Balanced", "Verse/Chorus", "Build-and-Drop", "Cinematic Arc", "Loop Friendly"];
const VIDEO_STYLE_OPTIONS = ["None", "Abstract Motion", "Neon Pulse", "Cinematic Landscape", "Particle Field"];

const INITIAL_FORM = {
  mode: "single",
  albumCount: 3,
  trackName: "",
  musicPrompt: "",
  genres: [],
  moods: [],
  tempoRange: { min: 90, max: 120 },
  durationSeconds: 120,
  lyrics: "",
  vocalLanguage: "Instrumental",
  vocalStyle: "None",
  artistInspiration: "",
  structurePreference: "Balanced",
  generateVideo: false,
  videoStyle: "None",
};

function sanitizeCommaList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function SuggestBlock({ suggestion, onApply, onDismiss }) {
  if (!suggestion) return null;
  return (
    <div className="suggest-box">
      <div>{suggestion}</div>
      <div className="controls-row" style={{ marginTop: 8 }}>
        <button type="button" className="btn" onClick={onApply}>
          Apply
        </button>
        <button type="button" className="btn" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  );
}

export default function CreateMusicPage() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [genreSearch, setGenreSearch] = useState("");
  const [moodSearch, setMoodSearch] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [suggestingField, setSuggestingField] = useState("");
  const [suggestions, setSuggestions] = useState({});

  const filteredGenres = useMemo(() => {
    const q = genreSearch.trim().toLowerCase();
    if (!q) return GENRE_OPTIONS;
    return GENRE_OPTIONS.filter((item) => item.toLowerCase().includes(q));
  }, [genreSearch]);

  const filteredMoods = useMemo(() => {
    const q = moodSearch.trim().toLowerCase();
    if (!q) return MOOD_OPTIONS;
    return MOOD_OPTIONS.filter((item) => item.toLowerCase().includes(q));
  }, [moodSearch]);

  const fullContext = {
    trackName: form.trackName,
    musicPrompt: form.musicPrompt,
    genres: form.genres,
    moods: form.moods,
    tempoRange: form.tempoRange,
    durationSeconds: form.durationSeconds,
    lyrics: form.lyrics,
    vocalLanguage: form.vocalLanguage,
    vocalStyle: form.vocalStyle,
    artistInspiration: form.artistInspiration,
    structurePreference: form.structurePreference,
    generateVideo: form.generateVideo,
    videoStyle: form.videoStyle,
    mode: form.mode,
  };

  const getFieldValue = (fieldName) => {
    if (fieldName === "genres") return form.genres.join(", ");
    if (fieldName === "moods") return form.moods.join(", ");
    if (fieldName === "tempoRange") return `${form.tempoRange.min}-${form.tempoRange.max}`;
    return form[fieldName];
  };

  const applySuggestion = (fieldName) => {
    const suggestion = suggestions[fieldName];
    if (!suggestion) return;

    setForm((prev) => {
      if (fieldName === "genres") {
        return { ...prev, genres: sanitizeCommaList(suggestion) };
      }
      if (fieldName === "moods") {
        return { ...prev, moods: sanitizeCommaList(suggestion) };
      }
      if (fieldName === "tempoRange") {
        const match = String(suggestion).match(/(\d+)\D+(\d+)/);
        if (match) {
          const min = Math.max(40, Math.min(220, Number(match[1])));
          const max = Math.max(40, Math.min(220, Number(match[2])));
          return { ...prev, tempoRange: { min: Math.min(min, max), max: Math.max(min, max) } };
        }
        return prev;
      }
      if (fieldName === "durationSeconds") {
        const parsed = Number(suggestion);
        if (Number.isFinite(parsed)) {
          return { ...prev, durationSeconds: Math.max(30, Math.min(3600, Math.round(parsed))) };
        }
        return prev;
      }
      return { ...prev, [fieldName]: suggestion };
    });

    setSuggestions((prev) => {
      const next = { ...prev };
      delete next[fieldName];
      return next;
    });
  };

  const requestSuggestion = async (fieldName) => {
    try {
      setSuggestingField(fieldName);
      const response = await fetch("/api/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fieldName,
          currentValue: getFieldValue(fieldName),
          fullContext,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "suggestion failed");
      }
      setSuggestions((prev) => ({ ...prev, [fieldName]: data.suggestion }));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Suggestion failed");
    } finally {
      setSuggestingField("");
    }
  };

  const toggleArrayValue = (field, value) => {
    setForm((prev) => {
      const existing = prev[field];
      const has = existing.includes(value);
      return {
        ...prev,
        [field]: has ? existing.filter((item) => item !== value) : [...existing, value],
      };
    });
  };

  const submitTrack = async (payload) => {
    const response = await fetch("/api/tracks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data?.error || "Track creation failed");
    }
    return data.track;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");

    try {
      const basePayload = {
        trackName: form.trackName || "Untitled Track",
        musicPrompt: form.musicPrompt,
        genres: form.genres,
        moods: form.moods,
        tempoRange: form.tempoRange,
        durationSeconds: form.durationSeconds,
        lyrics: form.lyrics,
        vocalLanguage: form.vocalLanguage,
        vocalStyle: form.vocalStyle,
        artistInspiration: form.artistInspiration,
        structurePreference: form.structurePreference,
        generateVideo: form.generateVideo,
        videoStyle: form.videoStyle,
      };

      if (form.mode === "single") {
        await submitTrack({ ...basePayload, mode: "single" });
        setMessage("Track queued. Open Dashboard for live progress and continuous master playback.");
      } else {
        const count = Math.max(2, Math.min(8, Number(form.albumCount) || 3));
        const jobs = [];
        for (let i = 0; i < count; i += 1) {
          jobs.push(
            submitTrack({
              ...basePayload,
              trackName: `${basePayload.trackName} ${i + 1}`,
              musicPrompt: `${basePayload.musicPrompt} (album track ${i + 1} of ${count})`,
              mode: "album",
            })
          );
        }
        await Promise.all(jobs);
        setMessage(`${count} tracks queued for album generation.`);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Track generation failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section>
      <h2 className="page-title">Create Music</h2>
      <p className="page-subtitle">
        Gemini Music Generation runs in deterministic 30-second segment loops and stitches every segment into one
        progressively growing master file.
      </p>

      <form className="card" style={{ marginTop: 20 }} onSubmit={handleSubmit}>
        <div className="controls-row" style={{ marginBottom: 12 }}>
          <button
            type="button"
            className={`pill ${form.mode === "single" ? "active" : ""}`}
            onClick={() => setForm((prev) => ({ ...prev, mode: "single" }))}
          >
            Single Track
          </button>
          <button
            type="button"
            className={`pill ${form.mode === "album" ? "active" : ""}`}
            onClick={() => setForm((prev) => ({ ...prev, mode: "album" }))}
          >
            Album
          </button>
          {form.mode === "album" && (
            <input
              type="number"
              min={2}
              max={8}
              value={form.albumCount}
              onChange={(e) => setForm((prev) => ({ ...prev, albumCount: Number(e.target.value) || 3 }))}
              style={{ width: 100 }}
            />
          )}
        </div>

        <div className="form-grid">
          <div className="field">
            <label>
              Track Name
              <button type="button" className="pill" onClick={() => requestSuggestion("trackName")}>
                {suggestingField === "trackName" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <input value={form.trackName} onChange={(e) => setForm((prev) => ({ ...prev, trackName: e.target.value }))} />
            <SuggestBlock
              suggestion={suggestions.trackName}
              onApply={() => applySuggestion("trackName")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, trackName: "" }))}
            />
          </div>

          <div className="field">
            <label>
              Duration (seconds)
              <button type="button" className="pill" onClick={() => requestSuggestion("durationSeconds")}>
                {suggestingField === "durationSeconds" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <input
              type="number"
              min={30}
              max={3600}
              value={form.durationSeconds}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, durationSeconds: Math.max(30, Math.min(3600, Number(e.target.value) || 30)) }))
              }
            />
            <SuggestBlock
              suggestion={suggestions.durationSeconds}
              onApply={() => applySuggestion("durationSeconds")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, durationSeconds: "" }))}
            />
          </div>

          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>
              Music Prompt
              <button type="button" className="pill" onClick={() => requestSuggestion("musicPrompt")}>
                {suggestingField === "musicPrompt" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <textarea
              value={form.musicPrompt}
              onChange={(e) => setForm((prev) => ({ ...prev, musicPrompt: e.target.value }))}
              placeholder="Describe instrumentation, groove, energy, arrangement, and sonic texture"
            />
            <SuggestBlock
              suggestion={suggestions.musicPrompt}
              onApply={() => applySuggestion("musicPrompt")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, musicPrompt: "" }))}
            />
          </div>

          <div className="field">
            <label>
              Genres
              <button type="button" className="pill" onClick={() => requestSuggestion("genres")}>
                {suggestingField === "genres" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <input placeholder="Search genres" value={genreSearch} onChange={(e) => setGenreSearch(e.target.value)} />
            <div className="controls-row" style={{ marginTop: 8 }}>
              {filteredGenres.map((genre) => (
                <button
                  key={genre}
                  type="button"
                  className={`pill ${form.genres.includes(genre) ? "active" : ""}`}
                  onClick={() => toggleArrayValue("genres", genre)}
                >
                  {genre}
                </button>
              ))}
            </div>
            <div className="inline-note" style={{ marginTop: 8 }}>
              Selected: {form.genres.join(", ") || "None"}
            </div>
            <SuggestBlock
              suggestion={suggestions.genres}
              onApply={() => applySuggestion("genres")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, genres: "" }))}
            />
          </div>

          <div className="field">
            <label>
              Moods
              <button type="button" className="pill" onClick={() => requestSuggestion("moods")}>
                {suggestingField === "moods" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <input placeholder="Search moods" value={moodSearch} onChange={(e) => setMoodSearch(e.target.value)} />
            <div className="controls-row" style={{ marginTop: 8 }}>
              {filteredMoods.map((mood) => (
                <button
                  key={mood}
                  type="button"
                  className={`pill ${form.moods.includes(mood) ? "active" : ""}`}
                  onClick={() => toggleArrayValue("moods", mood)}
                >
                  {mood}
                </button>
              ))}
            </div>
            <div className="inline-note" style={{ marginTop: 8 }}>
              Selected: {form.moods.join(", ") || "None"}
            </div>
            <SuggestBlock
              suggestion={suggestions.moods}
              onApply={() => applySuggestion("moods")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, moods: "" }))}
            />
          </div>

          <div className="field">
            <label>
              Tempo Range ({form.tempoRange.min}-{form.tempoRange.max} BPM)
              <button type="button" className="pill" onClick={() => requestSuggestion("tempoRange")}>
                {suggestingField === "tempoRange" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <input
              type="range"
              min={40}
              max={220}
              value={form.tempoRange.min}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  tempoRange: { ...prev.tempoRange, min: Math.min(Number(e.target.value), prev.tempoRange.max) },
                }))
              }
            />
            <input
              type="range"
              min={40}
              max={220}
              value={form.tempoRange.max}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  tempoRange: { ...prev.tempoRange, max: Math.max(Number(e.target.value), prev.tempoRange.min) },
                }))
              }
            />
            <SuggestBlock
              suggestion={suggestions.tempoRange}
              onApply={() => applySuggestion("tempoRange")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, tempoRange: "" }))}
            />
          </div>

          <div className="field">
            <label>
              Artist Inspiration
              <button type="button" className="pill" onClick={() => requestSuggestion("artistInspiration")}>
                {suggestingField === "artistInspiration" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <input
              value={form.artistInspiration}
              onChange={(e) => setForm((prev) => ({ ...prev, artistInspiration: e.target.value }))}
            />
            <SuggestBlock
              suggestion={suggestions.artistInspiration}
              onApply={() => applySuggestion("artistInspiration")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, artistInspiration: "" }))}
            />
          </div>

          <div className="field">
            <label>
              Vocal Language
              <button type="button" className="pill" onClick={() => requestSuggestion("vocalLanguage")}>
                {suggestingField === "vocalLanguage" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <select value={form.vocalLanguage} onChange={(e) => setForm((prev) => ({ ...prev, vocalLanguage: e.target.value }))}>
              {VOCAL_LANG_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <SuggestBlock
              suggestion={suggestions.vocalLanguage}
              onApply={() => applySuggestion("vocalLanguage")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, vocalLanguage: "" }))}
            />
          </div>

          <div className="field">
            <label>
              Vocal Style
              <button type="button" className="pill" onClick={() => requestSuggestion("vocalStyle")}>
                {suggestingField === "vocalStyle" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <select value={form.vocalStyle} onChange={(e) => setForm((prev) => ({ ...prev, vocalStyle: e.target.value }))}>
              {VOCAL_STYLE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <SuggestBlock
              suggestion={suggestions.vocalStyle}
              onApply={() => applySuggestion("vocalStyle")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, vocalStyle: "" }))}
            />
          </div>

          <div className="field">
            <label>
              Structure Preference
              <button type="button" className="pill" onClick={() => requestSuggestion("structurePreference")}>
                {suggestingField === "structurePreference" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <select
              value={form.structurePreference}
              onChange={(e) => setForm((prev) => ({ ...prev, structurePreference: e.target.value }))}
            >
              {STRUCTURE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <SuggestBlock
              suggestion={suggestions.structurePreference}
              onApply={() => applySuggestion("structurePreference")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, structurePreference: "" }))}
            />
          </div>

          <div className="field">
            <label>
              Video Style
              <button type="button" className="pill" onClick={() => requestSuggestion("videoStyle")}>
                {suggestingField === "videoStyle" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <select value={form.videoStyle} onChange={(e) => setForm((prev) => ({ ...prev, videoStyle: e.target.value }))}>
              {VIDEO_STYLE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <SuggestBlock
              suggestion={suggestions.videoStyle}
              onApply={() => applySuggestion("videoStyle")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, videoStyle: "" }))}
            />
          </div>

          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>
              Lyrics (optional)
              <button type="button" className="pill" onClick={() => requestSuggestion("lyrics")}>
                {suggestingField === "lyrics" ? "Thinking..." : "AI Suggest"}
              </button>
            </label>
            <textarea value={form.lyrics} onChange={(e) => setForm((prev) => ({ ...prev, lyrics: e.target.value }))} />
            <SuggestBlock
              suggestion={suggestions.lyrics}
              onApply={() => applySuggestion("lyrics")}
              onDismiss={() => setSuggestions((prev) => ({ ...prev, lyrics: "" }))}
            />
          </div>

          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Generate Video</label>
            <div className="controls-row">
              <button
                type="button"
                className={`pill ${form.generateVideo ? "active" : ""}`}
                onClick={() => setForm((prev) => ({ ...prev, generateVideo: !prev.generateVideo }))}
              >
                {form.generateVideo ? "Enabled" : "Disabled"}
              </button>
            </div>
            <p className="inline-note">Video generation runs only after the master audio is completed.</p>
          </div>
        </div>

        <div className="controls-row" style={{ marginTop: 18 }}>
          <button type="submit" className="btn primary" disabled={submitting}>
            {submitting ? "Queueing..." : form.mode === "single" ? "Generate Track" : "Generate Album"}
          </button>
          <button type="button" className="btn" onClick={() => setForm(INITIAL_FORM)}>
            Reset
          </button>
        </div>

        {message ? <p className="inline-note" style={{ marginTop: 10 }}>{message}</p> : null}
      </form>
    </section>
  );
}
