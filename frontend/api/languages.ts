interface ApiRequest { method?: string }
interface ApiResponse { status(code: number): ApiResponse; json(payload: unknown): void }

const languages = [
  "Instrumental", "English", "Spanish", "French", "German", "Italian", "Portuguese", "Japanese", "Korean",
  "Chinese (Mandarin)", "Chinese (Cantonese)", "Hindi", "Urdu", "Arabic", "Russian", "Turkish", "Persian",
  "Tamil", "Telugu", "Kannada", "Malayalam", "Punjabi", "Bengali", "Marathi", "Gujarati", "Swahili", "Yoruba"
];

export default function handler(req: ApiRequest, res: ApiResponse): void {
  if (req.method !== "GET") {
    res.status(405).json({ detail: "Method not allowed" });
    return;
  }
  res.status(200).json({ languages });
}
