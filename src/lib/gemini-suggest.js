import { generateGeminiJson } from "./vertex-gemini";

export async function suggestFieldValue({ fieldName, currentValue, fullContext }) {
  const contextPayload = {
    fieldName,
    currentValue: currentValue || "",
    fullContext,
  };

  const instruction = [
    "You are a music creation assistant.",
    "Return one concise suggestion for the requested field.",
    "Output JSON only: {\"suggestion\": string}.",
    "Do not include markdown.",
    "Keep semantic consistency with existing context and requested style.",
    `Context: ${JSON.stringify(contextPayload)}`,
  ].join("\n");

  const parsed = await generateGeminiJson({
    model: process.env.GEMINI_SUGGEST_MODEL || process.env.GEMINI_REASONING_MODEL || "gemini-2.5-flash",
    instruction,
    temperature: 0.75,
    maxOutputTokens: 240,
  });

  const suggestion = String(parsed?.suggestion || "").trim();
  if (!suggestion) {
    throw new Error("Gemini suggest returned empty suggestion");
  }
  return suggestion;
}
