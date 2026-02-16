import crypto from "crypto";

const sanitizeForPath = (value) =>
  String(value || "")
    .trim()
    .replace(/[^a-zA-Z0-9_-]/g, "-")
    .slice(0, 180);

export function generateEntropy() {
  return `${crypto.randomUUID()}-${Date.now()}-${crypto.randomBytes(16).toString("hex")}`;
}

export function buildFinalPrompt(userPrompt, entropy) {
  const promptText = String(userPrompt || "").trim();
  const entropyText = String(entropy || generateEntropy()).trim();

  return `${promptText}

Entropy seed: ${entropyText}
Timestamp: ${Date.now()}
Variation: ${Math.random()}`;
}

export function toEntropyPathToken(entropy) {
  return sanitizeForPath(entropy || generateEntropy());
}
