import crypto from "crypto";
import { NextResponse } from "next/server";
import { autoSuggestPrompt, generateMusicAudio } from "../../../lib/musicgen";
import { uploadAudioBlob, uploadVideoBlob } from "../../../lib/blob";
import { getMongoCollection } from "../../../lib/mongodb";
import { generateVisualizationVideo } from "../../../lib/videogen";
import { muxAudioAndVideo, normalizeAudioToWav } from "../../../lib/mux";
import { buildFinalPrompt, generateEntropy } from "../../../lib/entropy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const parseDuration = (duration) => {
  const parsed = Number(duration);
  if (!Number.isFinite(parsed)) {
    throw new Error("duration must be a valid number");
  }
  const normalized = Math.round(parsed);
  if (normalized < 1 || normalized > 300) {
    throw new Error("duration must be between 1 and 300 seconds");
  }
  return normalized;
};

const toArray = (value) => {
  if (Array.isArray(value)) {
    return value.map((item) => String(item || "").trim()).filter(Boolean);
  }
  if (typeof value === "string") {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
};

const buildRuntimePrompt = ({ prompt, genres, artistInspiration, description, entropy }) => {
  const directPrompt = String(prompt || "").trim();
  if (directPrompt) {
    return buildFinalPrompt(directPrompt, entropy);
  }

  const contextText = [
    toArray(genres).join(", "),
    String(artistInspiration || "").trim(),
    String(description || "").trim(),
  ]
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .join(" | ");

  if (!contextText) {
    throw new Error("prompt or context fields are required");
  }

  return buildFinalPrompt(contextText, entropy);
};

export async function POST(request) {
  try {
    const body = await request.json();

    const duration = parseDuration(body?.duration);
    const genres = toArray(body?.genres);
    const artistInspiration = typeof body?.artist_inspiration === "string" ? body.artist_inspiration : "";
    const description = typeof body?.description === "string" ? body.description : "";

    const projectId = crypto.randomUUID();

    const entropy = generateEntropy();

    const runtimePrompt = buildRuntimePrompt({
      prompt: body?.prompt,
      genres,
      artistInspiration,
      description,
      entropy,
    });

    const dynamicPrompt = await autoSuggestPrompt({
      userPrompt: runtimePrompt,
      genres,
      artistInspiration,
      description,
      entropy,
    });

    const { audioBuffer, finalPrompt } = await generateMusicAudio({
      prompt: dynamicPrompt,
      duration,
      entropy,
    });

    const wavAudioBuffer = await normalizeAudioToWav(audioBuffer);

    const videoBuffer = await generateVisualizationVideo({
      prompt: finalPrompt,
      duration,
      entropy,
    });

    const muxedVideoBuffer = await muxAudioAndVideo({
      audioBuffer: wavAudioBuffer,
      videoBuffer,
      duration,
    });

    const audioUrl = await uploadAudioBlob(projectId, entropy, wavAudioBuffer);
    const videoUrl = await uploadVideoBlob(projectId, entropy, muxedVideoBuffer);

    const projectsCollection = await getMongoCollection("projects");
    const createdAt = new Date();

    await projectsCollection.insertOne({
      project_id: projectId,
      entropy,
      prompt: finalPrompt,
      audio_url: audioUrl,
      video_url: videoUrl,
      duration,
      created_at: createdAt,
    });

    return NextResponse.json(
      {
        success: true,
        project_id: projectId,
        entropy,
        audio_url: audioUrl,
        video_url: videoUrl,
        created_at: createdAt.toISOString(),
      },
      { status: 200 }
    );
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "generation request failed",
      },
      { status: 500 }
    );
  }
}
