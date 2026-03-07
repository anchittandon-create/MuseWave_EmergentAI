import { promises as fs } from "fs";
import os from "os";
import path from "path";
import crypto from "crypto";
import { spawn } from "child_process";

const AUDIO_SAMPLE_RATE = 48000;
const AUDIO_CHANNELS = 2;
const CROSSFADE_MS = 100;

const runFfmpeg = (args) =>
  new Promise((resolve, reject) => {
    const handle = spawn("ffmpeg", args, { stdio: ["ignore", "ignore", "pipe"] });
    let stderr = "";
    handle.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });
    handle.on("error", reject);
    handle.on("close", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`ffmpeg failed (${code}): ${stderr}`));
      }
    });
  });

async function runFfmpegWithBuffers({ inputBuffer, inputExtension = "wav", argsBuilder, outputExtension }) {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "mwv-audio-"));
  const inputPath = path.join(tempDir, `${crypto.randomUUID()}-input.${inputExtension.replace(/^\./, "")}`);
  const outputPath = path.join(tempDir, `${crypto.randomUUID()}-output.${outputExtension.replace(/^\./, "")}`);

  try {
    await fs.writeFile(inputPath, inputBuffer);
    const args = argsBuilder(inputPath, outputPath);
    await runFfmpeg(args);
    const outputBuffer = await fs.readFile(outputPath);
    if (!outputBuffer.length) {
      throw new Error("ffmpeg produced empty output");
    }
    return outputBuffer;
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
}

export async function createSilentMasterWav(seconds = 0.2) {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "mwv-silent-"));
  const outputPath = path.join(tempDir, `${crypto.randomUUID()}-silent.wav`);
  try {
    await runFfmpeg([
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-f",
      "lavfi",
      "-i",
      `anullsrc=r=${AUDIO_SAMPLE_RATE}:cl=stereo`,
      "-t",
      String(Math.max(0.1, seconds)),
      "-ar",
      String(AUDIO_SAMPLE_RATE),
      "-ac",
      String(AUDIO_CHANNELS),
      "-c:a",
      "pcm_s16le",
      outputPath,
    ]);
    return await fs.readFile(outputPath);
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
}

export async function normalizeToWavPcm16(audioBuffer, sourceMime = "audio/wav") {
  const ext = sourceMime.includes("mpeg") ? "mp3" : sourceMime.includes("ogg") ? "ogg" : "wav";
  return runFfmpegWithBuffers({
    inputBuffer: audioBuffer,
    inputExtension: ext,
    outputExtension: "wav",
    argsBuilder: (inputPath, outputPath) => [
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-i",
      inputPath,
      "-ar",
      String(AUDIO_SAMPLE_RATE),
      "-ac",
      String(AUDIO_CHANNELS),
      "-c:a",
      "pcm_s16le",
      outputPath,
    ],
  });
}

function parseWavPcm16(buffer) {
  if (!Buffer.isBuffer(buffer) || buffer.length < 44) {
    throw new Error("Invalid WAV buffer");
  }
  if (buffer.toString("ascii", 0, 4) !== "RIFF" || buffer.toString("ascii", 8, 12) !== "WAVE") {
    throw new Error("WAV header not recognized");
  }

  let offset = 12;
  let fmt = null;
  let dataChunk = null;

  while (offset + 8 <= buffer.length) {
    const chunkId = buffer.toString("ascii", offset, offset + 4);
    const chunkSize = buffer.readUInt32LE(offset + 4);
    const chunkStart = offset + 8;
    const chunkEnd = chunkStart + chunkSize;

    if (chunkEnd > buffer.length) break;

    if (chunkId === "fmt ") {
      fmt = {
        audioFormat: buffer.readUInt16LE(chunkStart),
        channels: buffer.readUInt16LE(chunkStart + 2),
        sampleRate: buffer.readUInt32LE(chunkStart + 4),
        bitsPerSample: buffer.readUInt16LE(chunkStart + 14),
      };
    } else if (chunkId === "data") {
      dataChunk = buffer.subarray(chunkStart, chunkEnd);
    }

    offset = chunkEnd + (chunkSize % 2);
  }

  if (!fmt || !dataChunk) {
    throw new Error("WAV missing fmt/data chunks");
  }
  if (fmt.audioFormat !== 1 || fmt.bitsPerSample !== 16) {
    throw new Error("WAV must be PCM 16-bit for stitching");
  }

  const samples = new Int16Array(dataChunk.buffer, dataChunk.byteOffset, Math.floor(dataChunk.byteLength / 2));
  return {
    sampleRate: fmt.sampleRate,
    channels: fmt.channels,
    samples,
  };
}

function encodeWavPcm16({ sampleRate, channels, samples }) {
  const dataSize = samples.length * 2;
  const buffer = Buffer.alloc(44 + dataSize);
  buffer.write("RIFF", 0, "ascii");
  buffer.writeUInt32LE(36 + dataSize, 4);
  buffer.write("WAVE", 8, "ascii");
  buffer.write("fmt ", 12, "ascii");
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(channels, 22);
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate * channels * 2, 28);
  buffer.writeUInt16LE(channels * 2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write("data", 36, "ascii");
  buffer.writeUInt32LE(dataSize, 40);

  for (let i = 0; i < samples.length; i += 1) {
    buffer.writeInt16LE(samples[i], 44 + i * 2);
  }
  return buffer;
}

function frameMagnitude(samples, channels, frameIndex) {
  let magnitude = 0;
  const base = frameIndex * channels;
  for (let c = 0; c < channels; c += 1) {
    magnitude += Math.abs(samples[base + c] || 0);
  }
  return magnitude;
}

function findNearestZeroCrossing(samples, channels, targetFrame, searchRadiusFrames) {
  const totalFrames = Math.floor(samples.length / channels);
  const start = Math.max(1, targetFrame - searchRadiusFrames);
  const end = Math.min(totalFrames - 1, targetFrame + searchRadiusFrames);

  let bestFrame = targetFrame;
  let bestScore = Number.POSITIVE_INFINITY;

  for (let frame = start; frame <= end; frame += 1) {
    const curr = samples[frame * channels];
    const prev = samples[(frame - 1) * channels];
    const crossing = (prev <= 0 && curr >= 0) || (prev >= 0 && curr <= 0);
    const mag = frameMagnitude(samples, channels, frame);

    const distancePenalty = Math.abs(frame - targetFrame) * 0.35;
    const crossingPenalty = crossing ? 0 : 4000;
    const score = mag + distancePenalty + crossingPenalty;
    if (score < bestScore) {
      bestScore = score;
      bestFrame = frame;
    }
  }

  return bestFrame;
}

function stitchPcmWithCrossfade(master, incoming, crossfadeMs = CROSSFADE_MS) {
  if (master.sampleRate !== incoming.sampleRate || master.channels !== incoming.channels) {
    throw new Error("Cannot stitch mismatched sample rates/channels");
  }

  const sampleRate = master.sampleRate;
  const channels = master.channels;
  const masterFrames = Math.floor(master.samples.length / channels);
  const incomingFrames = Math.floor(incoming.samples.length / channels);

  if (masterFrames < 2) return incoming;
  if (incomingFrames < 2) return master;

  const fadeFrames = Math.max(1, Math.round((crossfadeMs / 1000) * sampleRate));
  const usableFadeFrames = Math.min(fadeFrames, masterFrames - 1, incomingFrames - 1);

  const targetMasterFrame = Math.max(1, masterFrames - usableFadeFrames);
  const masterCutFrame = findNearestZeroCrossing(master.samples, channels, targetMasterFrame, Math.min(sampleRate, usableFadeFrames * 4));
  const incomingStartFrame = findNearestZeroCrossing(incoming.samples, channels, 1, Math.min(sampleRate, usableFadeFrames * 4));

  const safeMasterCut = Math.min(Math.max(1, masterCutFrame), masterFrames - 1);
  const safeIncomingStart = Math.min(Math.max(0, incomingStartFrame), incomingFrames - 1);
  const availableIncoming = incomingFrames - safeIncomingStart;
  const actualFade = Math.min(usableFadeFrames, safeMasterCut, availableIncoming - 1);

  if (actualFade < 1) {
    const combined = new Int16Array(master.samples.length + incoming.samples.length);
    combined.set(master.samples, 0);
    combined.set(incoming.samples, master.samples.length);
    return { sampleRate, channels, samples: combined };
  }

  const preFrames = safeMasterCut - actualFade;
  const postFrames = availableIncoming - actualFade;
  const totalFrames = preFrames + actualFade + postFrames;
  const output = new Int16Array(totalFrames * channels);

  // Copy pre-crossfade section from master.
  for (let frame = 0; frame < preFrames; frame += 1) {
    for (let c = 0; c < channels; c += 1) {
      output[frame * channels + c] = master.samples[frame * channels + c];
    }
  }

  // Crossfade overlap.
  for (let frame = 0; frame < actualFade; frame += 1) {
    const fadeIn = frame / (actualFade - 1 || 1);
    const fadeOut = 1 - fadeIn;
    const masterFrame = preFrames + frame;
    const incomingFrame = safeIncomingStart + frame;

    for (let c = 0; c < channels; c += 1) {
      const masterSample = master.samples[masterFrame * channels + c] || 0;
      const incomingSample = incoming.samples[incomingFrame * channels + c] || 0;
      const mixed = Math.round(masterSample * fadeOut + incomingSample * fadeIn);
      output[(preFrames + frame) * channels + c] = Math.max(-32768, Math.min(32767, mixed));
    }
  }

  // Copy tail from incoming after crossfade.
  for (let frame = 0; frame < postFrames; frame += 1) {
    const incomingFrame = safeIncomingStart + actualFade + frame;
    const outFrame = preFrames + actualFade + frame;
    for (let c = 0; c < channels; c += 1) {
      output[outFrame * channels + c] = incoming.samples[incomingFrame * channels + c] || 0;
    }
  }

  return { sampleRate, channels, samples: output };
}

export async function stitchMasterWithSegment({ masterWavBuffer, segmentWavBuffer }) {
  const master = parseWavPcm16(masterWavBuffer);
  const segment = parseWavPcm16(segmentWavBuffer);
  const stitched = stitchPcmWithCrossfade(master, segment, CROSSFADE_MS);
  return encodeWavPcm16(stitched);
}

export async function trimWavToDuration(wavBuffer, durationSeconds) {
  return runFfmpegWithBuffers({
    inputBuffer: wavBuffer,
    inputExtension: "wav",
    outputExtension: "wav",
    argsBuilder: (inputPath, outputPath) => [
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-i",
      inputPath,
      "-t",
      String(Math.max(1, durationSeconds)),
      "-ar",
      String(AUDIO_SAMPLE_RATE),
      "-ac",
      String(AUDIO_CHANNELS),
      "-c:a",
      "pcm_s16le",
      outputPath,
    ],
  });
}

export async function applyMasteringChain(wavBuffer, durationSeconds) {
  const fadeOutStart = Math.max(0, durationSeconds - 0.3);
  return runFfmpegWithBuffers({
    inputBuffer: wavBuffer,
    inputExtension: "wav",
    outputExtension: "wav",
    argsBuilder: (inputPath, outputPath) => [
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-i",
      inputPath,
      "-ar",
      String(AUDIO_SAMPLE_RATE),
      "-ac",
      String(AUDIO_CHANNELS),
      "-af",
      [
        "loudnorm=I=-14:TP=-1.5:LRA=11",
        "alimiter=limit=0.95",
        "equalizer=f=120:t=q:w=1:g=0.8",
        "equalizer=f=5200:t=q:w=1:g=0.8",
        "afade=t=in:st=0:d=0.08",
        `afade=t=out:st=${fadeOutStart.toFixed(3)}:d=0.25`,
      ].join(","),
      "-c:a",
      "pcm_s16le",
      outputPath,
    ],
  });
}

export async function convertWavToMp3(wavBuffer) {
  return runFfmpegWithBuffers({
    inputBuffer: wavBuffer,
    inputExtension: "wav",
    outputExtension: "mp3",
    argsBuilder: (inputPath, outputPath) => [
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-i",
      inputPath,
      "-codec:a",
      "libmp3lame",
      "-b:a",
      "192k",
      outputPath,
    ],
  });
}
