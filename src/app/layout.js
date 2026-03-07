import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "MuseWave - Gemini Music Generation",
  description: "Anonymous AI music generation with progressive master-audio orchestration.",
};

const navItems = [
  { href: "/", label: "Home" },
  { href: "/create", label: "Create Music" },
  { href: "/dashboard", label: "Dashboard" },
];

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <div className="brand">
              <div className="brand-logo">MW</div>
              <div>
                <h1>MuseWave</h1>
                <p>Gemini Music Platform</p>
              </div>
            </div>
            <nav className="nav-links">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href} className="nav-link">
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>
          <main className="main-content">{children}</main>
        </div>
      </body>
    </html>
  );
}
