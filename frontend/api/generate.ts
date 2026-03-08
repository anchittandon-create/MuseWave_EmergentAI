import { randomUUID } from "crypto";
import { saveTrack } from "./_store";

type GenerateRequestBody = {
  trackName?: string;
  description?: string;
  genre?: string;
  duration?: number;
  artistStyle?: string;
  lyrics?: string;
  generateVideo?: boolean;
  videoStyle?: string;
  vocalLanguages?: string[];
  userId?: string;
};

interface ApiRequest {
  method?: string;
  body?: string | GenerateRequestBody;
}

interface ApiResponse {
  setHeader(name: string, value: string): void;
  status(code: number): ApiResponse;
  json(payload: unknown): void;
}

function parseBody(body: ApiRequest["body"]): GenerateRequestBody {
  if (!body) return {};
  if (typeof body === "string") {
    try {
      return JSON.parse(body) as GenerateRequestBody;
    } catch {
      return {};
    }
  }
  return body;
}

export default async function handler(req: ApiRequest, res: ApiResponse): Promise<void> {
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  const payload = parseBody(req.body);
  const trackName = String(payload.trackName || "").trim();
  const description = String(payload.description || "").trim();
  const genre = String(payload.genre || "").trim();
  const artistStyle = String(payload.artistStyle || "").trim();
  const duration = Number(payload.duration);

  if (!trackName) {
    res.status(400).json({ error: "trackName is required" });
    return;
  }
  if (!description) {
    res.status(400).json({ error: "description is required" });
    return;
  }
  if (!genre) {
    res.status(400).json({ error: "genre is required" });
    return;
  }
  if (!Number.isFinite(duration) || duration <= 0) {
    res.status(400).json({ error: "duration must be a positive number" });
    return;
  }

  const trackId = randomUUID();
  const nonce = `${Date.now()}-${Math.floor(Math.random() * 100000)}`;
  const audioUrl = `/mock/generated-track.mp3?v=${nonce}`;
  const videoUrl = payload.generateVideo ? `/mock/generated-track.mp4?v=${nonce}` : null;
  const createdAt = new Date().toISOString();

  await saveTrack({
    id: trackId,
    user_id: String(payload.userId || "anonymous"),
    title: trackName,
    music_prompt: description,
    genres: genre
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    duration_seconds: Math.round(duration),
    artist_inspiration: artistStyle,
    lyrics: String(payload.lyrics || ""),
    audio_url: audioUrl,
    video_url: videoUrl,
    cover_art_url: "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=400&h=400&fit=crop",
    created_at: createdAt,
  });

  res.status(200).json({
    status: "success",
    trackUrl: audioUrl,
    message: "Track generated successfully",
    trackId,
    title: trackName,
    description,
    genre,
    duration,
    artistStyle,
    audio_url: audioUrl,
    video_url: videoUrl,
    coverArtUrl: "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=400&h=400&fit=crop",
    createdAt,
  });
}
