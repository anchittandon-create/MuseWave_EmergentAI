interface ApiRequest { method?: string }
interface ApiResponse { status(code: number): ApiResponse; json(payload: unknown): void }

const artists = [
  "A. R. Rahman", "Adele", "Ado", "Amr Diab", "Antonio Vivaldi", "Aphex Twin", "Arctic Monkeys", "Arijit Singh",
  "Asake", "BLACKPINK", "Bad Bunny", "Beyonce", "Boards of Canada", "Bonobo", "Burna Boy", "Daft Punk", "Drake",
  "Dua Lipa", "Ed Sheeran", "Fairuz", "Flying Lotus", "Four Tet", "Hans Zimmer", "J Balvin", "Jay Chou", "Kendrick Lamar",
  "Karol G", "Nusrat Fateh Ali Khan", "Post Malone", "Radiohead", "Rema", "Rosalia", "Shakira", "SZA", "Taylor Swift",
  "The Weeknd", "Travis Scott", "Tycho", "Wizkid", "YOASOBI"
];

export default function handler(req: ApiRequest, res: ApiResponse): void {
  if (req.method !== "GET") {
    res.status(405).json({ detail: "Method not allowed" });
    return;
  }
  res.status(200).json({ artists });
}
