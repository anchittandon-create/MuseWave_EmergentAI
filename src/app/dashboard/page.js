"use client";

import { useEffect, useMemo, useState } from "react";

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value || "");
  }
}

function statusClass(status) {
  if (status === "completed") return "completed";
  if (status === "failed") return "failed";
  return "generating";
}

function TrackRow({ track }) {
  const percent = Math.max(0, Math.min(100, Number(track.progressPercentage || 0)));

  return (
    <article className="track-row">
      <div className="track-meta">
        <div>
          <strong>{track.trackName || "Untitled Track"}</strong>
          <div className="inline-note">{formatDate(track.createdAt)}</div>
        </div>
        <span className={`track-status ${statusClass(track.status)}`}>{track.status || "queued"}</span>
      </div>

      <div className="inline-note">
        Duration: {track.durationGenerated || 0}s / {track.durationRequested || 0}s | Segments: {track.segmentsGenerated || 0}
      </div>

      <div className="progress-bar">
        <span style={{ width: `${percent}%` }} />
      </div>

      {track.audioMasterUrl ? (
        <audio controls preload="metadata" src={track.audioMasterUrl} style={{ width: "100%" }} />
      ) : (
        <div className="inline-note">Master audio URL will appear after first segment stitch.</div>
      )}

      <div className="controls-row" style={{ marginTop: 8 }}>
        {track.audioMasterUrl ? (
          <a className="btn" href={track.audioMasterUrl} target="_blank" rel="noreferrer">
            Download Master
          </a>
        ) : null}
        {track.videoUrl ? (
          <a className="btn" href={track.videoUrl} target="_blank" rel="noreferrer">
            Download Video
          </a>
        ) : null}
      </div>

      {track.errorMessage ? <div className="inline-note" style={{ color: "#ac3030" }}>{track.errorMessage}</div> : null}
    </article>
  );
}

export default function DashboardPage() {
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const hasGenerating = useMemo(() => tracks.some((track) => track.status === "generating" || track.status === "queued"), [tracks]);

  useEffect(() => {
    let alive = true;

    const fetchTracks = async () => {
      try {
        const response = await fetch("/api/tracks", { cache: "no-store" });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data?.error || "failed to fetch tracks");
        }
        if (alive) {
          setTracks(Array.isArray(data.tracks) ? data.tracks : []);
          setError("");
        }
      } catch (err) {
        if (alive) {
          setError(err instanceof Error ? err.message : "failed to fetch tracks");
        }
      } finally {
        if (alive) setLoading(false);
      }
    };

    fetchTracks();
    const interval = setInterval(fetchTracks, 4000);

    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <section>
      <h2 className="page-title">Dashboard</h2>
      <p className="page-subtitle">
        Tracks are stored in Firestore with progressive master audio updates in Firebase Storage. Playback always points
        to one master audio URL per track.
      </p>

      {loading ? <p className="inline-note">Loading tracks...</p> : null}
      {error ? <p className="inline-note" style={{ color: "#ac3030" }}>{error}</p> : null}
      {hasGenerating ? <p className="inline-note">Live polling active while tracks are generating.</p> : null}

      <div className="track-list">
        {tracks.map((track) => (
          <TrackRow key={track.id} track={track} />
        ))}
      </div>
    </section>
  );
}
