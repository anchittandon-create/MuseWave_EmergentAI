import { randomBytes, randomUUID } from "crypto";
import { performance } from "perf_hooks";

const sanitizeEntropy = (value) =>
  String(value || "")
    .trim()
    .replace(/[^a-zA-Z0-9_-]/g, "-")
    .slice(0, 120);

export function generateEntropy(prefix = "mwv") {
  const timePart = Date.now();
  const perfPart = Math.floor(performance.now() * 1000);
  const uuidPart = randomUUID();
  const bytesPart = randomBytes(16).toString("hex");
  return sanitizeEntropy(`${prefix}-${timePart}-${perfPart}-${uuidPart}-${bytesPart}`);
}

export function buildEntropyPrompt(userPrompt, entropy) {
  const basePrompt = String(userPrompt || "").trim();
  const entropyValue = sanitizeEntropy(entropy || generateEntropy("prompt"));

  return `${basePrompt}

Creative variation seed: ${entropyValue}

Musical variation timestamp: ${Date.now()}

Randomization factor: ${Math.random()}`;
}

export function addEntropyVariation(baseSuggestion, entropy) {
  const text = String(baseSuggestion || "").trim();
  const entropyValue = sanitizeEntropy(entropy || generateEntropy("variation"));
  if (!text) return `Variation ${entropyValue}`;
  return `${text} - variation ${entropyValue}`;
}

