import crypto from "crypto";
import {
  uploadBufferToStorage,
  downloadBufferFromStorage,
  getFirestoreDb,
} from "./firebase-admin";
import {
  createSilentMasterWav,
  normalizeToWavPcm16,
  stitchMasterWithSegment,
  trimWavToDuration,
  applyMasteringChain,
  convertWavToMp3,
} from "./audio-pipeline";
import { predictLyriaSegment, generateGeminiJson } from "./vertex-gemini";

const SEGMENT_SECONDS = 30;
const activeJobs = new Map();

function nowIso() {
  return new Date().toISOString();
}

function deterministicSeed(trackId, segmentIndex) {
  const hash = crypto.createHash("sha256").update(`${trackId}:${segmentIndex}`).digest("hex");
  return parseInt(hash.slice(0, 8), 16);
}

function getMasterPaths(trackId) {
  return {
    wavPath: `audio/${trackId}_master.wav`,
    mp3Path: `audio/${trackId}_master.mp3`,
  };
}

function getSegmentPath(trackId, segmentIndex) {
  return `tempSegments/${trackId}/segment_${segmentIndex}.wav`;
}

function clampDuration(durationSeconds) {
  const parsed = Number(durationSeconds);
  if (!Number.isFinite(parsed)) return SEGMENT_SECONDS;
  return Math.max(30, Math.min(3600, Math.round(parsed)));
}

function parseBpmRange(tempoRange) {
  if (!tempoRange || typeof tempoRange !== "object") {
    return { min: 90, max: 120 };
  }
  const min = Number(tempoRange.min);
  const max = Number(tempoRange.max);
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return { min: 90, max: 120 };
  }
  return {
    min: Math.max(50, Math.min(220, Math.round(Math.min(min, max)))),
    max: Math.max(50, Math.min(220, Math.round(Math.max(min, max)))),
  };
}

function buildSegmentRole(totalSegments, segmentIndex, structurePreference) {
  const pref = String(structurePreference || "balanced").trim();
  if (totalSegments === 1) {
    return `single complete composition with a full arc (${pref})`;
  }
  if (segmentIndex === 0) {
    return `opening segment with clear motif and clean intro (${pref})`;
  }
  if (segmentIndex === totalSegments - 1) {
    return `ending segment with natural resolution and ending cadence (${pref})`;
  }
  return `continuation segment that evolves motifs without abrupt reset (${pref})`;
}

function buildIntentObject(track, bpmRange) {
  return {
    trackName: track.trackName,
    prompt: track.prompt,
    genres: track.genres || [],
    moods: track.moods || [],
    bpmRange,
    vocalLanguage: track.vocalLanguage || "",
    vocalStyle: track.vocalStyle || "",
    artistInspiration: track.artistInspiration || "",
    structurePreference: track.structurePreference || "",
    lyrics: track.lyrics || "",
  };
}

function buildSegmentPrompt({ track, segmentIndex, totalSegments, previousMetadata }) {
  const bpmRange = parseBpmRange(track.tempoRange);
  const intent = buildIntentObject(track, bpmRange);
  const segmentRole = buildSegmentRole(totalSegments, segmentIndex, track.structurePreference);

  const continuity = previousMetadata
    ? `Continue from previous segment ending: tempo=${previousMetadata.tempoBpm}, key=${previousMetadata.keySignature}, harmony=${previousMetadata.harmonicStructure}.`
    : "Start from a coherent initial tonal center and rhythmic motif.";

  return [
    `Track: ${track.trackName}`,
    `Segment ${segmentIndex + 1} of ${totalSegments}.`,
    `Role: ${segmentRole}.`,
    `Primary prompt: ${track.prompt}.`,
    `Intent JSON: ${JSON.stringify(intent)}.`,
    continuity,
    "Composition rules: maintain tempo, key center, rhythmic continuity, and instrument continuity.",
    "Avoid abrupt starts, abrupt cuts, and style resets.",
    "Generate exactly one seamless 30-second continuation block.",
  ].join(" ");
}

function buildNegativePrompt(track) {
  return [
    "abrupt transition",
    "hard reset",
    "key change without resolution",
    "tempo drift",
    track.generateVideo ? "silence" : "",
  ]
    .filter(Boolean)
    .join(", ");
}

async function extractSegmentMetadata(segmentWavBuffer, track, segmentIndex, totalSegments) {
  const instruction = [
    "Analyze this music segment and return strict JSON only.",
    "Schema: {\"tempoBpm\": number, \"keySignature\": string, \"harmonicStructure\": string, \"rhythmicCharacter\": string}",
    "Focus on the ending region so next generation can continue seamlessly.",
    `Context: ${JSON.stringify({
      trackName: track.trackName,
      prompt: track.prompt,
      segmentIndex,
      totalSegments,
      genres: track.genres,
      moods: track.moods,
    })}`,
  ].join("\n");

  return generateGeminiJson({
    model: process.env.GEMINI_ANALYSIS_MODEL || process.env.GEMINI_REASONING_MODEL || "gemini-2.5-flash",
    instruction,
    inlineParts: [
      {
        inlineData: {
          mimeType: "audio/wav",
          data: segmentWavBuffer.toString("base64"),
        },
      },
    ],
    temperature: 0.2,
    maxOutputTokens: 300,
  });
}

async function updateTrack(trackId, patch) {
  const db = getFirestoreDb();
  await db
    .collection("tracks")
    .doc(trackId)
    .set({ ...patch, updatedAt: nowIso() }, { merge: true });
}

async function uploadMasterArtifacts(trackId, wavBuffer) {
  const { wavPath, mp3Path } = getMasterPaths(trackId);
  const [wavUpload, mp3Buffer] = await Promise.all([
    uploadBufferToStorage({
      path: wavPath,
      buffer: wavBuffer,
      contentType: "audio/wav",
      token: `${trackId}-master-wav`,
    }),
    convertWavToMp3(wavBuffer),
  ]);

  const mp3Upload = await uploadBufferToStorage({
    path: mp3Path,
    buffer: mp3Buffer,
    contentType: "audio/mpeg",
    token: `${trackId}-master-mp3`,
  });

  return {
    wavUrl: wavUpload.url,
    mp3Url: mp3Upload.url,
  };
}

async function generateOptionalVideo(track, trackId, audioUrl) {
  if (!track.generateVideo) return "";
  const endpoint = process.env.VIDEO_GENERATION_ENDPOINT;
  if (!endpoint) return "";

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(process.env.VIDEO_GENERATION_API_KEY
        ? { Authorization: `Bearer ${process.env.VIDEO_GENERATION_API_KEY}` }
        : {}),
    },
    body: JSON.stringify({
      trackId,
      trackName: track.trackName,
      prompt: track.prompt,
      videoStyle: track.videoStyle,
      durationSeconds: track.durationRequested,
      audioMasterUrl: audioUrl,
    }),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`Video generation failed: ${response.status} ${detail}`.trim());
  }

  const payload = await response.json();
  const videoUrl = String(payload?.videoUrl || payload?.url || "").trim();
  return videoUrl;
}

async function generateTrackInternal(trackId) {
  const db = getFirestoreDb();
  const trackRef = db.collection("tracks").doc(trackId);
  const trackSnapshot = await trackRef.get();
  if (!trackSnapshot.exists) {
    throw new Error(`Track ${trackId} not found`);
  }

  const track = trackSnapshot.data();
  const durationRequested = clampDuration(track.durationRequested);
  const segmentsNeeded = Math.ceil(durationRequested / SEGMENT_SECONDS);

  // Step 1: initialize empty master file in storage and doc.
  const initialMaster = await createSilentMasterWav(0.2);
  const initialMasterUpload = await uploadMasterArtifacts(trackId, initialMaster);

  await updateTrack(trackId, {
    status: "generating",
    durationRequested,
    durationGenerated: 0,
    segmentsGenerated: 0,
    progressPercentage: 0,
    audioMasterUrl: initialMasterUpload.mp3Url,
  });

  let previousMetadata = null;
  let masterWav = await downloadBufferFromStorage(getMasterPaths(trackId).wavPath);

  for (let currentSegment = 0; currentSegment < segmentsNeeded; currentSegment += 1) {
    const prompt = buildSegmentPrompt({
      track,
      segmentIndex: currentSegment,
      totalSegments: segmentsNeeded,
      previousMetadata,
    });

    const segmentAudio = await predictLyriaSegment({
      prompt,
      negativePrompt: buildNegativePrompt(track),
      seed: deterministicSeed(trackId, currentSegment),
      durationSeconds: SEGMENT_SECONDS,
    });

    const normalizedSegment = await normalizeToWavPcm16(segmentAudio.audioBuffer, segmentAudio.mimeType);

    await uploadBufferToStorage({
      path: getSegmentPath(trackId, currentSegment),
      buffer: normalizedSegment,
      contentType: "audio/wav",
      token: `${trackId}-seg-${currentSegment}`,
    });

    // Step 4: progressive master stitching with crossfade and zero-crossing alignment.
    masterWav = await stitchMasterWithSegment({
      masterWavBuffer: masterWav,
      segmentWavBuffer: normalizedSegment,
    });

    const currentDurationGenerated = Math.min(durationRequested, (currentSegment + 1) * SEGMENT_SECONDS);
    const progressPercentage = Math.min(100, Math.round((currentDurationGenerated / durationRequested) * 100));
    const masterUploads = await uploadMasterArtifacts(trackId, masterWav);

    // Step 5: progress update.
    await updateTrack(trackId, {
      durationGenerated: currentDurationGenerated,
      segmentsGenerated: currentSegment + 1,
      progressPercentage,
      audioMasterUrl: masterUploads.mp3Url,
      status: "generating",
    });

    // Step 6: metadata extraction for next segment conditioning.
    previousMetadata = await extractSegmentMetadata(normalizedSegment, track, currentSegment, segmentsNeeded);
  }

  // Step 7: final trim to exact requested duration.
  let finalWav = await trimWavToDuration(masterWav, durationRequested);

  // Step 8: post-processing/mastering pipeline.
  finalWav = await applyMasteringChain(finalWav, durationRequested);

  const finalUploads = await uploadMasterArtifacts(trackId, finalWav);
  const videoUrl = await generateOptionalVideo(track, trackId, finalUploads.mp3Url);

  // Step 9: final document update.
  await updateTrack(trackId, {
    status: "completed",
    durationGenerated: durationRequested,
    progressPercentage: 100,
    audioMasterUrl: finalUploads.mp3Url,
    audioMasterWavUrl: finalUploads.wavUrl,
    videoUrl,
    lastSegmentMetadata: previousMetadata || null,
  });
}

export function queueTrackGeneration(trackId) {
  if (activeJobs.has(trackId)) {
    return;
  }

  const task = generateTrackInternal(trackId)
    .catch(async (error) => {
      await updateTrack(trackId, {
        status: "failed",
        errorMessage: error instanceof Error ? error.message : String(error),
      });
    })
    .finally(() => {
      activeJobs.delete(trackId);
    });

  activeJobs.set(trackId, task);
}

export function isTrackGenerating(trackId) {
  return activeJobs.has(trackId);
}

export function buildTrackDocument(payload) {
  const createdAt = nowIso();
  const durationRequested = clampDuration(payload.durationSeconds);

  return {
    id: payload.id,
    trackName: String(payload.trackName || "Untitled Track").trim() || "Untitled Track",
    prompt: String(payload.musicPrompt || "").trim(),
    genres: Array.isArray(payload.genres) ? payload.genres : [],
    moods: Array.isArray(payload.moods) ? payload.moods : [],
    tempoRange: payload.tempoRange || { min: 90, max: 120 },
    durationRequested,
    durationGenerated: 0,
    segmentsGenerated: 0,
    audioMasterUrl: "",
    videoUrl: "",
    status: "generating",
    progressPercentage: 0,
    lyrics: String(payload.lyrics || ""),
    vocalLanguage: String(payload.vocalLanguage || ""),
    vocalStyle: String(payload.vocalStyle || ""),
    artistInspiration: String(payload.artistInspiration || ""),
    structurePreference: String(payload.structurePreference || "balanced"),
    generateVideo: Boolean(payload.generateVideo),
    videoStyle: String(payload.videoStyle || ""),
    mode: String(payload.mode || "single"),
    createdAt,
    updatedAt: createdAt,
  };
}
