import { NextResponse } from "next/server";
import { getFirestoreDb } from "../../../../lib/firebase-admin";
import { isTrackGenerating } from "../../../../lib/track-orchestrator";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_request, { params }) {
  try {
    const id = String(params?.id || "").trim();
    if (!id) {
      return NextResponse.json({ error: "track id is required" }, { status: 400 });
    }

    const db = getFirestoreDb();
    const snapshot = await db.collection("tracks").doc(id).get();

    if (!snapshot.exists) {
      return NextResponse.json({ error: "track not found" }, { status: 404 });
    }

    const track = snapshot.data();
    return NextResponse.json(
      {
        track,
        activeInProcess: isTrackGenerating(id),
      },
      { status: 200 }
    );
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "track fetch failed" },
      { status: 500 }
    );
  }
}
