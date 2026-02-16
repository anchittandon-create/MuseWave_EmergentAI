import { promises as fs } from "fs";
import os from "os";
import path from "path";
import { spawn } from "child_process";
import crypto from "crypto";
import { generateEntropy } from "./entropy";

const runFfmpeg = (args) =>
  new Promise((resolve, reject) => {
    const processHandle = spawn("ffmpeg", args, { stdio: ["ignore", "ignore", "pipe"] });

    let stderr = "";
    processHandle.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    processHandle.on("error", (error) => {
      reject(error);
    });

    processHandle.on("close", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`ffmpeg failed with code ${code}: ${stderr}`));
      }
    });
  });

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

const createVisualProfile = (prompt, entropy) => {
  const hash = crypto
    .createHash("sha256")
    .update(`${String(prompt || "").trim()}-${String(entropy || "").trim()}-${Date.now()}-${Math.random()}`)
    .digest("hex");

  const n = parseInt(hash.slice(0, 12), 16);
  const contrast = 1 + ((n % 30) / 100);
  const saturation = 1 + (((n >> 2) % 40) / 100);
  const hueSpeed = ((n % 13) + 1) / 4;
  const noise = Math.max(4, Math.floor(Math.random() * 100));

  return { contrast, saturation, hueSpeed, noise };
};

export async function generateVisualizationVideo({ prompt, duration, entropy }) {
  const safeDuration = parseDuration(duration);
  const requestEntropy = String(entropy || generateEntropy()).trim();
  const visual = createVisualProfile(prompt, requestEntropy);

  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "mwv-video-"));
  const outputPath = path.join(tempDir, `${crypto.randomUUID()}-${Date.now()}.mp4`);

  try {
    const sourceFilter = `color=c=black:s=1280x720:r=30:d=${safeDuration}`;
    const videoFilter = [
      `noise=alls=${visual.noise}:allf=t+u`,
      `eq=contrast=${visual.contrast}:saturation=${visual.saturation}`,
      `hue=h=${visual.hueSpeed}*t`,
      "format=yuv420p",
    ].join(",");

    await runFfmpeg([
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-f",
      "lavfi",
      "-i",
      sourceFilter,
      "-vf",
      videoFilter,
      "-an",
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "+faststart",
      outputPath,
    ]);

    const videoBuffer = await fs.readFile(outputPath);
    if (!videoBuffer.length) {
      throw new Error("video generation produced empty output");
    }
    return videoBuffer;
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
}
