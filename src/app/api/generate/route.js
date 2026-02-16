import { randomUUID } from "crypto";
import { NextResponse } from "next/server";
import { generateMusicAudio } from "../../../lib/musicgen";
import { uploadAudioToBlob } from "../../../lib/blob";
import { getMongoDb } from "../../../lib/mongodb";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const parseDuration = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 30;
  return Math.max(1, Math.min(Math.round(parsed), 300));
};

export async function POST(request) {
  try {
    const payload = await request.json();

    const prompt = typeof payload?.prompt === "string" ? payload.prompt.trim() : "";
    const duration = parseDuration(payload?.duration);
    const genres = Array.isArray(payload?.genres) ? payload.genres : [];
    const artistInspiration = typeof payload?.artist_inspiration === "string" ? payload.artist_inspiration : "";
    const description = typeof payload?.description === "string" ? payload.description : "";

    const projectId = randomUUID();

    const musicResult = await generateMusicAudio({
      prompt,
      duration,
      genres,
      artistInspiration,
      description,
    });

    const audioUrl = await uploadAudioToBlob(projectId, musicResult.audioBuffer);

    const db = await getMongoDb();
    await db.collection("projects").insertOne({
      project_id: projectId,
      prompt: musicResult.prompt,
      audio_url: audioUrl,
      created_at: new Date(),
    });

    return NextResponse.json(
      {
        success: true,
        project_id: projectId,
        audio_url: audioUrl,
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
