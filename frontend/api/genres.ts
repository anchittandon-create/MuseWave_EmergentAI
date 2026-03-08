interface ApiRequest {
  method?: string;
}

interface ApiResponse {
  status(code: number): ApiResponse;
  json(payload: unknown): void;
}

const genres = [
  "Afro Fusion", "Afro House", "Afro-Cuban", "Afrobeats", "Amapiano", "Ambient", "Ambient Soundscape",
  "Andean Folk", "Anisong", "Arabic Pop", "Bachata", "Baul", "Bedroom Pop", "Bhangra", "Bluegrass", "Blues",
  "Bollywood", "Bongo Flava", "Bossa Nova", "Carnatic", "Cinematic", "Cloud Rap", "Cumbia", "Dancehall",
  "Dark Ambient", "Deep House", "Dembow", "Disco", "Dream Pop", "Drill", "Drum and Bass", "Dubstep", "EDM",
  "Electronic", "Epic", "Filmi", "Flamenco", "Folk", "Future Bass", "Funk", "Ghazal", "Glitch", "Grime",
  "House", "Hyperpop", "IDM", "Indie", "J-Pop", "Jazz", "K-Pop", "Latin Pop", "Lo-fi", "Maqam", "Mariachi",
  "Math Rock", "Merengue", "Metal", "Neo-Classical", "Orchestral", "Phonk", "Pop", "Post-Punk", "Post-Rock",
  "Progressive House", "Qawwali", "R&B", "Reggaeton", "Rock", "Salsa", "Samba", "Shoegaze", "Soul", "Synthwave",
  "Tarab", "Techno", "Trap", "Trance", "Vaporwave", "Video Game"
];

export default function handler(req: ApiRequest, res: ApiResponse): void {
  if (req.method !== "GET") {
    res.status(405).json({ detail: "Method not allowed" });
    return;
  }
  res.status(200).json({ genres });
}
