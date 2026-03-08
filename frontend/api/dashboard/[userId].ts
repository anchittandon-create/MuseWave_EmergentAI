import { listTracksByUser } from "../_store";

interface ApiRequest {
  method?: string;
  query?: { userId?: string };
}

interface ApiResponse {
  status(code: number): ApiResponse;
  json(payload: unknown): void;
}

export default async function handler(req: ApiRequest, res: ApiResponse): Promise<void> {
  if (req.method !== "GET") {
    res.status(405).json({ detail: "Method not allowed" });
    return;
  }
  const userId = String(req.query?.userId || "").trim();
  if (!userId) {
    res.status(400).json({ detail: "userId is required" });
    return;
  }

  const tracks = await listTracksByUser(userId);
  res.status(200).json({ songs: tracks, albums: [] });
}
