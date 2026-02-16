import { NextResponse } from "next/server";
import { getMongoDb } from "../../../lib/mongodb";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const db = await getMongoDb();
    const projects = await db
      .collection("projects")
      .find({})
      .sort({ created_at: -1 })
      .toArray();

    const serialized = projects.map((project) => ({
      ...project,
      _id: String(project._id),
    }));

    return NextResponse.json(serialized, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Failed to fetch projects",
      },
      { status: 500 }
    );
  }
}
