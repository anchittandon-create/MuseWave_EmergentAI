interface ApiRequest { method?: string }
interface ApiResponse { status(code: number): ApiResponse; json(payload: unknown): void }

const styles = [
  "Cyberpunk cityscape", "Abstract geometric patterns", "Nature cinematatography", "Psychedelic visuals",
  "Minimalist motion graphics", "Retro VHS aesthetic", "Surreal dreamscape", "Urban street footage", "Space and cosmos", "Neon lights"
];

export default function handler(req: ApiRequest, res: ApiResponse): void {
  if (req.method !== "GET") {
    res.status(405).json({ detail: "Method not allowed" });
    return;
  }
  res.status(200).json({ styles });
}
