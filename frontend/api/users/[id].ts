import { getUserById, upsertUser } from "../_store";

interface ApiRequest {
  method?: string;
  query?: { id?: string };
  body?: string | { name?: string; mobile?: string; phoneNumber?: string };
}

interface ApiResponse {
  setHeader(name: string, value: string): void;
  status(code: number): ApiResponse;
  json(payload: unknown): void;
}

function parseBody(body: ApiRequest["body"]): { name?: string; mobile?: string; phoneNumber?: string } {
  if (!body) return {};
  if (typeof body === "string") {
    try {
      return JSON.parse(body);
    } catch {
      return {};
    }
  }
  return body;
}

export default async function handler(req: ApiRequest, res: ApiResponse): Promise<void> {
  res.setHeader("Cache-Control", "no-store");
  const userId = String(req.query?.id || "").trim();
  if (!userId) {
    res.status(400).json({ detail: "user id is required" });
    return;
  }

  if (req.method === "GET") {
    const user = await getUserById(userId);
    if (!user) {
      res.status(404).json({ detail: "User not found" });
      return;
    }
    res.status(200).json(user);
    return;
  }

  if (req.method === "PATCH") {
    const body = parseBody(req.body);
    const existing = await getUserById(userId);
    if (!existing) {
      res.status(404).json({ detail: "User not found" });
      return;
    }
    const next = await upsertUser({
      id: userId,
      name: String(body.name || existing.name),
      mobile: String(body.mobile || body.phoneNumber || existing.mobile),
      role: existing.role,
    });
    res.status(200).json(next);
    return;
  }

  if (req.method === "DELETE") {
    res.status(200).json({ success: true });
    return;
  }

  res.status(405).json({ detail: "Method not allowed" });
}
