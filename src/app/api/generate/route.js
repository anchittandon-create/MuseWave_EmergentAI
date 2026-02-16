import { randomUUID } from "crypto";
import { NextResponse } from "next/server";
import { autoSuggestPrompt, generateMusicAudio } from "../../../lib/musicgen";
import { uploadAudioBlob, uploadVideoBlob } from "../../../lib/blob";
import { getMongoDb } from "../../../lib/mongodb";
import { generateVisualizationVideo } from "../../../lib/videogen";
import { normalizeAudioToWav, muxAudioAndVideo } from "../../../lib/mux";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const clampDuration = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 30;
  return Math.max(1, Math.min(Math.round(parsed), 300));
};

export async function POST(request) {
  try {
    const body = await request.json();

    const duration = clampDuration(body?.duration);
    const genres = Array.isArray(body?.genres) ? body.genres : [];
    const artistInspiration = typeof body?.artist_inspiration === "string" ? body.artist_inspiration : "";
    const description = typeof body?.description === "string" ? body.description : "";

    let prompt = typeof body?.prompt === "string" ? body.prompt.trim() : "";
    if (!prompt) {
      prompt = await autoSuggestPrompt({ genres, artistInspiration, description });
    }

    const projectId = randomUUID();

    const { audioBuffer: rawAudioBuffer } = await generateMusicAudio({
      prompt,
      duration,
    });

    const wavAudioBuffer = await normalizeAudioToWav(rawAudioBuffer);

    const visualVideoBuffer = await generateVisualizationVideo({
      prompt,
      duration,
    });

    const finalVideoBuffer = await muxAudioAndVideo({
      audioBuffer: wavAudioBuffer,
      videoBuffer: visualVideoBuffer,
      duration,
    });

    const [audioUrl, videoUrl] = await Promise.all([
      uploadAudioBlob(projectId, wavAudioBuffer),
      uploadVideoBlob(projectId, finalVideoBuffer),
    ]);

    const db = await getMongoDb();
    const createdAt = new Date();

    await db.collection("projects").insertOne({
      project_id: projectId,
      prompt,
      audio_url: audioUrl,
      video_url: videoUrl,
      created_at: createdAt,
    });

    return NextResponse.json(
      {
        success: true,
        project_id: projectId,
        prompt,
        audio_url: audioUrl,
        video_url: videoUrl,
        created_at: createdAt,
      },
      { status: 200 }
    );
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Generation failed",
      },
      { status: 500 }
    );
  }
}
