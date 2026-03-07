import crypto from "crypto";
import { NextResponse } from "next/server";
import { getFirestoreDb } from "../../../lib/firebase-admin";
import { buildTrackDocument, queueTrackGeneration } from "../../../lib/track-orchestrator";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function toSafeArray(value) {
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
}

function parseTempoRange(value) {
  const fallback = { min: 90, max: 120 };
  if (!value || typeof value !== "object") return fallback;
  const min = Number(value.min);
  const max = Number(value.max);
  if (!Number.isFinite(min) || !Number.isFinite(max)) return fallback;
  return {
    min: Math.max(40, Math.min(220, Math.round(Math.min(min, max)))),
    max: Math.max(40, Math.min(220, Math.round(Math.max(min, max)))),
  };
}

export async function GET() {
  try {
    const db = getFirestoreDb();
    const snapshot = await db.collection("tracks").orderBy("createdAt", "desc").limit(200).get();
    const tracks = snapshot.docs.map((doc) => doc.data());
    return NextResponse.json({ tracks }, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "failed to list tracks" },
      { status: 500 }
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const trackName = String(body?.trackName || "").trim();
    const musicPrompt = String(body?.musicPrompt || "").trim();

    if (!musicPrompt) {
      return NextResponse.json({ error: "musicPrompt is required" }, { status: 422 });
    }

    const id = crypto.randomUUID();
    const payload = {
      id,
      trackName,
      musicPrompt,
      genres: toSafeArray(body?.genres),
      moods: toSafeArray(body?.moods),
      tempoRange: parseTempoRange(body?.tempoRange),
      durationSeconds: Number(body?.durationSeconds || 60),
      lyrics: String(body?.lyrics || ""),
      vocalLanguage: String(body?.vocalLanguage || ""),
      vocalStyle: String(body?.vocalStyle || ""),
      artistInspiration: String(body?.artistInspiration || ""),
      structurePreference: String(body?.structurePreference || "balanced"),
      generateVideo: Boolean(body?.generateVideo),
      videoStyle: String(body?.videoStyle || ""),
      mode: String(body?.mode || "single"),
    };

    const trackDoc = buildTrackDocument(payload);
    const db = getFirestoreDb();

    await db.collection("tracks").doc(id).set(trackDoc);
    queueTrackGeneration(id);

    return NextResponse.json(
      {
        track: trackDoc,
        message: "Track queued for generation",
      },
      { status: 202 }
    );
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "track creation failed" },
      { status: 500 }
    );
  }
}
