import Link from "next/link";

export default function HomePage() {
  return (
    <section>
      <h2 className="page-title">MuseWave</h2>
      <p className="page-subtitle">
        Anonymous AI music generation platform powered by Gemini Music orchestration. Tracks are generated in fixed
        30-second segments and stitched into a single progressively growing master audio file.
      </p>
      <div className="card" style={{ marginTop: 24 }}>
        <h3 style={{ marginTop: 0 }}>How It Works</h3>
        <p>
          The backend performs deterministic segment orchestration, continuity conditioning, zero-crossing alignment,
          100ms crossfades, and progressive master file updates in Firebase Storage.
        </p>
        <Link className="btn primary" href="/create">
          Create Music
        </Link>
      </div>
    </section>
  );
}
