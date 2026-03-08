import { createHash } from "crypto";
import { findUserByMobile, normalizeMobile, upsertUser } from "../_store";

interface ApiRequest {
  method?: string;
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
  if (req.method !== "POST") {
    res.status(405).json({ detail: "Method not allowed" });
    return;
  }

  const body = parseBody(req.body);
  const name = String(body.name || "").trim();
  const mobile = normalizeMobile(String(body.mobile || body.phoneNumber || ""));

  if (!name || !mobile) {
    res.status(400).json({ detail: "name and mobile are required" });
    return;
  }

  const existing = await findUserByMobile(mobile);
  const userId =
    existing?.id ||
    createHash("sha1")
      .update(mobile)
      .digest("hex")
      .slice(0, 24);

  const user = await upsertUser({
    id: userId,
    name,
    mobile,
    role: mobile === "9873945238" ? "Master User" : "User",
  });

  res.status(200).json(user);
}
