import { NextResponse } from "next/server";
import { suggestFieldValue } from "../../../lib/gemini-suggest";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request) {
  try {
    const body = await request.json();
    const fieldName = String(body?.fieldName || "").trim();

    if (!fieldName) {
      return NextResponse.json({ error: "fieldName is required" }, { status: 400 });
    }

    const suggestion = await suggestFieldValue({
      fieldName,
      currentValue: body?.currentValue,
      fullContext: body?.fullContext || {},
    });

    return NextResponse.json({ suggestion, fieldName }, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "suggestion failed" },
      { status: 500 }
    );
  }
}
