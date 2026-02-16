import { promises as fs } from "fs";
import os from "os";
import path from "path";
import { spawn } from "child_process";
import { randomUUID, createHash } from "crypto";

const runFfmpeg = (args) =>
  new Promise((resolve, reject) => {
    const proc = spawn("ffmpeg", args, { stdio: ["ignore", "ignore", "pipe"] });

    let stderr = "";
    proc.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    proc.on("error", (err) => {
      if (err.code === "ENOENT") {
        reject(new Error("FFmpeg not found. Install FFmpeg on the deployment/runtime environment."));
      } else {
        reject(err);
      }
    });

    proc.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`FFmpeg failed with code ${code}: ${stderr}`));
    });
  });

const clampDuration = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 30;
  return Math.max(1, Math.min(Math.round(parsed), 300));
};

const promptSeed = (prompt) => {
  const hash = createHash("sha256").update(String(prompt || "")).digest("hex");
  const n = parseInt(hash.slice(0, 8), 16);
  return {
    hueSpeed: ((n % 9) + 1) / 4,
    saturation: 1 + ((n % 30) / 100),
    contrast: 1 + (((n >> 3) % 20) / 100),
  };
};

export async function generateVisualizationVideo({ prompt, duration }) {
  const safeDuration = clampDuration(duration);
  const seed = promptSeed(prompt);

  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "musewave-videogen-"));
  const outputPath = path.join(tempDir, `${randomUUID()}.mp4`);

  try {
    const videoFilter = [
      `testsrc2=size=1280x720:rate=30:duration=${safeDuration}`,
    ].join(":");

    const vf = [
      `hue=h=${seed.hueSpeed}*t`,
      `eq=saturation=${seed.saturation}:contrast=${seed.contrast}`,
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
      videoFilter,
      "-vf",
      vf,
      "-an",
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "+faststart",
      outputPath,
    ]);

    return await fs.readFile(outputPath);
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
}
