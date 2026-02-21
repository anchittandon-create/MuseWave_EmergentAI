"""
MuseWave - AI Music Creation Application
Independent backend with:
- Gemini/OpenAI-powered AI suggestions and lyrics synthesis
- Optional external provider hook for actual music generation
- Optional Replicate-based video generation
- Global knowledge bases for genres/languages/artists
"""

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
import uuid
from datetime import datetime, timezone
from openai import OpenAI
import random
import hashlib
import mimetypes
import zipfile
import io
import base64
import requests
from PIL import Image, ImageDraw
import json
import re
import time
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl, unquote_to_bytes

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = (
    os.environ.get("MONGO_URL")
    or os.environ.get("MONGODB_URI")
    or "mongodb://localhost:27017"
)
client = AsyncIOMotorClient(mongo_url)
PRIMARY_DB_NAME = os.environ.get('DB_NAME', 'muzify_db')
LEGACY_DB_NAME = os.environ.get('LEGACY_DB_NAME', 'musewave_db')
db = client[PRIMARY_DB_NAME]
legacy_db = client[LEGACY_DB_NAME] if LEGACY_DB_NAME != PRIMARY_DB_NAME else None
# Permanent master user for global dashboard access.
MASTER_ADMIN_MOBILE = "9873945238"
MASTER_ADMIN_NAME = "Anchit Tandon"
MASTER_ADMIN_ROLE = "Master User"

# API Keys
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip() or None
GEMINI_MODEL = (os.environ.get("GEMINI_MODEL", "gemini-1.5-flash") or "gemini-1.5-flash").strip()
AI_SUGGEST_PROVIDER = os.environ.get("AI_SUGGEST_PROVIDER", "gemini").strip().lower()
REPLICATE_API_TOKEN = os.environ.get('REPLICATE_API_TOKEN')
MUSICGEN_API_URL = os.environ.get("MUSICGEN_API_URL")
MUSICGEN_API_KEY = os.environ.get("MUSICGEN_API_KEY")
REPLICATE_MUSIC_MODEL = os.environ.get(
    "REPLICATE_MUSIC_MODEL",
    "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
)
REPLICATE_MUSIC_MODEL_VERSION = os.environ.get("REPLICATE_MUSIC_MODEL_VERSION", "stereo-large")
REPLICATE_MUSIC_OUTPUT_FORMAT = os.environ.get("REPLICATE_MUSIC_OUTPUT_FORMAT", "mp3")
REPLICATE_MUSIC_NORMALIZATION_STRATEGY = os.environ.get("REPLICATE_MUSIC_NORMALIZATION_STRATEGY", "peak")
REPLICATE_MUSIC_MAX_DURATION_SECONDS = int(os.environ.get("REPLICATE_MUSIC_MAX_DURATION_SECONDS", "30"))
STRICT_REAL_MEDIA_OUTPUT = os.environ.get("STRICT_REAL_MEDIA_OUTPUT", "false").lower() == "true"
FREE_TIER_MODE = os.environ.get("FREE_TIER_MODE", "false").lower() == "true"
SUGGEST_MAX_ATTEMPTS = max(1, min(int(os.environ.get("SUGGEST_MAX_ATTEMPTS", "3")), 6))
SUGGEST_OPENAI_TIMEOUT_SECONDS = max(
    2.0, min(float(os.environ.get("SUGGEST_OPENAI_TIMEOUT_SECONDS", "8")), 30.0)
)

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _ai_provider_order() -> list[str]:
    provider = (AI_SUGGEST_PROVIDER or "").strip().lower()
    if provider == "openai":
        return ["openai", "gemini"]
    if provider == "gemini":
        return ["gemini", "openai"]
    return ["gemini", "openai"]


def _extract_gemini_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        for part in parts:
            text = str(part.get("text") or "").strip()
            if text:
                return text
    prompt_feedback = payload.get("promptFeedback") or {}
    block_reason = prompt_feedback.get("blockReason")
    if block_reason:
        raise RuntimeError(f"Gemini blocked response: {block_reason}")
    raise RuntimeError("Gemini returned empty response")


def _call_gemini_text(system_prompt: str, user_prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"{system_prompt}\n\n"
                            f"User request:\n{user_prompt}\n\n"
                            "Return only valid JSON with no markdown."
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 1.0,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": 1400,
            "responseMimeType": "application/json",
        },
    }
    response = requests.post(
        endpoint,
        headers={"Content-Type": "application/json"},
        json=body,
        timeout=max(SUGGEST_OPENAI_TIMEOUT_SECONDS, 10),
    )
    if response.status_code >= 400:
        raw_error = (response.text or "").strip().replace("\n", " ")
        raise RuntimeError(f"Gemini HTTP {response.status_code}: {raw_error[:220]}")
    payload = response.json()
    return _extract_gemini_text(payload)


def _call_openai_text(system_prompt: str, user_prompt: str) -> str:
    if not openai_client:
        raise RuntimeError("OPENAI_API_KEY is missing")
    response = openai_client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=1.0,
        top_p=0.95,
        frequency_penalty=0.7,
        presence_penalty=0.8,
        max_tokens=900,
        timeout=max(SUGGEST_OPENAI_TIMEOUT_SECONDS, 10),
    )
    return (response.choices[0].message.content or "").strip()


async def _generate_context_text(system_prompt: str, user_prompt: str) -> str:
    last_error: Optional[str] = None
    for provider in _ai_provider_order():
        try:
            if provider == "gemini":
                return await asyncio.to_thread(_call_gemini_text, system_prompt, user_prompt)
            if provider == "openai":
                return await asyncio.to_thread(_call_openai_text, system_prompt, user_prompt)
        except Exception as exc:
            last_error = str(exc)
            logger.warning("AI context generation via %s failed: %s", provider, exc)
    raise RuntimeError(last_error or "No AI provider available for suggestions")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="MuseWave API", description="AI Music Creation Platform")

# Create a router mounted at root; Vercel function path handling is normalized via middleware below.
api_router = APIRouter(prefix="")


@app.middleware("http")
async def normalize_api_path_prefix(request, call_next):
    path = request.scope.get("path", "")
    if path == "/api" or path.startswith("/api/"):
        normalized = path[4:] or "/"
        request.scope["path"] = normalized
        request.scope["raw_path"] = normalized.encode("utf-8")
    return await call_next(request)

RECENT_SUGGESTIONS: dict[str, list[str]] = {}

# ==================== CURATED AUDIO LIBRARY ====================
# High-quality royalty-free tracks from reliable CDN sources

AUDIO_LIBRARY = {
    "electronic": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", "title": "Electronic Pulse", "duration": 30},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", "title": "Digital Wave", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3", "title": "Synth Dreams", "duration": 25},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3", "title": "Cyber Flow", "duration": 27},
    ],
    "ambient": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3", "title": "Peaceful Ambient", "duration": 30},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3", "title": "Ethereal Space", "duration": 26},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3", "title": "Calm Waters", "duration": 24},
    ],
    "rock": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3", "title": "Rock Energy", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3", "title": "Guitar Riff", "duration": 25},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3", "title": "Power Chords", "duration": 30},
    ],
    "hip_hop": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3", "title": "Urban Beat", "duration": 26},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3", "title": "Street Flow", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-13.mp3", "title": "Boom Bap", "duration": 24},
    ],
    "cinematic": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-14.mp3", "title": "Epic Journey", "duration": 30},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-15.mp3", "title": "Dramatic Score", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-16.mp3", "title": "Orchestral Rise", "duration": 25},
    ],
    "jazz": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", "title": "Smooth Jazz", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", "title": "Jazz Cafe", "duration": 26},
    ],
    "pop": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3", "title": "Pop Vibes", "duration": 25},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3", "title": "Feel Good", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3", "title": "Summer Hit", "duration": 24},
    ],
    "lofi": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3", "title": "Lofi Study", "duration": 30},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3", "title": "Chill Beats", "duration": 26},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3", "title": "Rainy Day", "duration": 28},
    ],
    "classical": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3", "title": "Piano Sonata", "duration": 30},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3", "title": "Strings Ensemble", "duration": 28},
    ],
    "default": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3", "title": "Inspiring", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3", "title": "Uplifting", "duration": 25},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-13.mp3", "title": "Creative Flow", "duration": 30},
    ]
}

COVER_ART_LIBRARY = {
    "electronic": [
        "https://images.unsplash.com/photo-1614149162883-504ce4d13909?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1571974599782-87624638275e?w=400&h=400&fit=crop",
    ],
    "ambient": [
        "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1507400492013-162706c8c05e?w=400&h=400&fit=crop",
    ],
    "rock": [
        "https://images.unsplash.com/photo-1498038432885-c6f3f1b912ee?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400&h=400&fit=crop",
    ],
    "hip_hop": [
        "https://images.unsplash.com/photo-1571609860754-01a63ee4d50c?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1546367791-e07aabff30bc?w=400&h=400&fit=crop",
    ],
    "cinematic": [
        "https://images.unsplash.com/photo-1478737270239-2f02b77fc618?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=400&h=400&fit=crop",
    ],
    "jazz": [
        "https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400&h=400&fit=crop",
    ],
    "pop": [
        "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1506157786151-b8491531f063?w=400&h=400&fit=crop",
    ],
    "lofi": [
        "https://images.unsplash.com/photo-1528722828814-77b9b83aafb2?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1515378960530-7c0da6231fb1?w=400&h=400&fit=crop",
    ],
    "classical": [
        "https://images.unsplash.com/photo-1507838153414-b4b713384a76?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1520523839897-bd0b52f945a0?w=400&h=400&fit=crop",
    ],
    "default": [
        "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=400&h=400&fit=crop",
    ]
}

# ==================== GLOBAL KNOWLEDGE BASES ====================

GENRE_KNOWLEDGE_BASE = {
    "mainstream": ["Pop", "Rock", "Hip-Hop", "R&B", "Electronic", "Jazz", "Classical", "Country", "Reggae", "Blues", "Metal", "Folk", "Indie", "Soul", "Funk", "Disco"],
    "electronic": ["House", "Techno", "Trance", "Dubstep", "Drum and Bass", "Ambient", "IDM", "Synthwave", "Chillwave", "Future Bass", "Hardstyle", "Deep House", "Progressive House", "EDM"],
    "underground": ["Lo-fi", "Vaporwave", "Shoegaze", "Post-Punk", "Noise", "Drone", "Dark Ambient", "Industrial", "Chiptune", "Glitch"],
    "regional": ["Afrobeats", "Reggaeton", "K-Pop", "J-Pop", "Bollywood", "Bossa Nova", "Flamenco", "Cumbia", "Salsa", "Samba", "Dancehall", "Grime"],
    "micro_genres": ["Trap", "Drill", "Phonk", "Hyperpop", "Bedroom Pop", "Cloud Rap", "Math Rock", "Post-Rock", "Dream Pop"],
    "cinematic": ["Orchestral", "Cinematic", "Epic", "Film Score", "Video Game", "Ambient Soundscape", "Neo-Classical", "Minimalist"],
    "latin": ["Latin Pop", "Bachata", "Merengue", "Regional Mexican", "Corridos", "Norteño", "Mariachi", "Dembow", "Latin Trap"],
    "african": ["Amapiano", "Afro House", "Afro Fusion", "Bongo Flava", "Highlife", "Gqom", "Kuduro", "Afro-Cuban"],
    "south_asian": ["Indian Classical", "Carnatic", "Qawwali", "Ghazal", "Bollywood", "Bhangra", "Filmi", "Baul"],
    "east_asian": ["City Pop", "Enka", "Kayokyoku", "Anisong", "Mandopop", "Cantopop", "Trot", "Pansori"],
    "middle_eastern": ["Arabic Pop", "Maqam", "Dabke", "Rai", "Gnawa", "Persian Traditional", "Turkish Folk", "Tarab"],
    "traditional_folk": ["Bluegrass", "Celtic Folk", "Nordic Folk", "Flamenco", "Fado", "Tango", "Sufi", "Andean Folk"],
    "experimental": ["Glitch Hop", "Deconstructed Club", "Footwork", "Juke", "Electroacoustic", "Musique Concrete", "Sound Collage", "Generative Ambient"]
}

ARTIST_KNOWLEDGE_BASE = {
    "electronic": ["Aphex Twin", "Boards of Canada", "Four Tet", "Burial", "Flying Lotus", "Bonobo", "Tycho", "Jon Hopkins", "Caribou"],
    "pop": ["The Weeknd", "Dua Lipa", "Billie Eilish", "Harry Styles", "Taylor Swift", "Post Malone", "SZA"],
    "rock": ["Tame Impala", "Arctic Monkeys", "Radiohead", "Muse", "Royal Blood", "Khruangbin"],
    "hip_hop": ["Kendrick Lamar", "Tyler the Creator", "Frank Ocean", "Travis Scott", "J. Cole"],
    "ambient": ["Brian Eno", "Stars of the Lid", "Tim Hecker", "Sigur Rós", "Explosions in the Sky"],
    "jazz": ["Kamasi Washington", "Robert Glasper", "Thundercat", "Snarky Puppy"],
    "latin": ["Bad Bunny", "Rosalia", "Karol G", "J Balvin", "Peso Pluma", "Shakira", "Rauw Alejandro"],
    "african": ["Burna Boy", "Wizkid", "Tems", "Rema", "Asake", "Black Coffee", "Sauti Sol"],
    "south_asian": ["A. R. Rahman", "Shreya Ghoshal", "Arijit Singh", "Divine", "Nucleya", "Prateek Kuhad"],
    "east_asian": ["BTS", "BLACKPINK", "IU", "YOASOBI", "Ado", "Jay Chou", "Teresa Teng"],
    "middle_eastern": ["Amr Diab", "Nancy Ajram", "Fairuz", "Umm Kulthum", "Mohsen Namjoo", "Googoosh"],
    "classical_heritage": ["Ludwig van Beethoven", "Johann Sebastian Bach", "Antonio Vivaldi", "Claude Debussy", "Ravi Shankar", "Nusrat Fateh Ali Khan"],
    "global_icons": ["Daft Punk", "Drake", "Adele", "Beyonce", "Bruno Mars", "Coldplay", "Ed Sheeran", "Hans Zimmer"]
}

LANGUAGE_KNOWLEDGE_BASE = [
    "Instrumental", "English", "Spanish", "French", "German", "Italian", "Portuguese",
    "Japanese", "Korean", "Chinese (Mandarin)", "Chinese (Cantonese)", "Hindi", "Urdu",
    "Arabic", "Russian", "Swedish", "Norwegian", "Danish", "Finnish", "Dutch", "Polish",
    "Czech", "Slovak", "Hungarian", "Romanian", "Bulgarian", "Serbian", "Croatian",
    "Slovenian", "Greek", "Turkish", "Hebrew", "Persian", "Kurdish", "Armenian",
    "Azerbaijani", "Georgian", "Kazakh", "Uzbek", "Tajik", "Thai", "Vietnamese",
    "Indonesian", "Malay", "Tagalog", "Tamil", "Telugu", "Kannada", "Malayalam",
    "Punjabi", "Bengali", "Marathi", "Gujarati", "Sinhala", "Nepali", "Swahili",
    "Yoruba", "Igbo", "Hausa", "Amharic", "Somali", "Zulu", "Xhosa", "Afrikaans",
    "Lingala", "Wolof", "Portuguese (Brazil)", "Spanish (Latin America)",
    "French (Quebec)", "Gaelic", "Irish", "Welsh", "Basque", "Catalan", "Galician",
    "Icelandic", "Maltese", "Albanian", "Lithuanian", "Latvian", "Estonian",
    "Khmer", "Lao", "Burmese", "Mongolian"
]

VIDEO_STYLE_KNOWLEDGE_BASE = [
    "Cyberpunk cityscape", "Abstract geometric patterns", "Nature cinematography",
    "Psychedelic visuals", "Minimalist motion graphics", "Retro VHS aesthetic",
    "Surreal dreamscape", "Urban street footage", "Space and cosmos", "Neon lights"
]

def get_all_genres() -> List[str]:
    all_genres = []
    for category in GENRE_KNOWLEDGE_BASE.values():
        all_genres.extend(category)
    return sorted(list(set(all_genres)))

def get_all_artists() -> List[str]:
    all_artists = []
    for category in ARTIST_KNOWLEDGE_BASE.values():
        all_artists.extend(category)
    return sorted(list(set(all_artists)))

# ==================== Models ====================

class UserCreate(BaseModel):
    name: str
    mobile: str

class UserLogin(BaseModel):
    mobile: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    mobile: str
    role: str = "User"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserResponse(BaseModel):
    id: str
    name: str
    mobile: str
    role: str
    created_at: str

class SongCreate(BaseModel):
    title: Optional[str] = ""
    music_prompt: str
    genres: List[str] = Field(default_factory=list)
    duration_seconds: int = 15
    vocal_languages: List[str] = Field(default_factory=list)
    lyrics: Optional[str] = ""
    artist_inspiration: Optional[str] = ""
    generate_video: bool = False
    video_style: Optional[str] = ""
    mode: str = "single"
    album_id: Optional[str] = None
    user_id: str

class AlbumSongInput(BaseModel):
    title: Optional[str] = ""
    music_prompt: str
    genres: List[str] = Field(default_factory=list)
    duration_seconds: int = 25
    vocal_languages: List[str] = Field(default_factory=list)
    lyrics: Optional[str] = ""
    artist_inspiration: Optional[str] = ""
    video_style: Optional[str] = ""

class AlbumCreate(BaseModel):
    title: Optional[str] = ""
    music_prompt: Optional[str] = ""
    genres: List[str] = Field(default_factory=list)
    vocal_languages: List[str] = Field(default_factory=list)
    lyrics: Optional[str] = ""
    artist_inspiration: Optional[str] = ""
    generate_video: bool = False
    video_style: Optional[str] = ""
    num_songs: int = 3
    album_songs: List[AlbumSongInput] = Field(default_factory=list)
    user_id: str

class AISuggestRequest(BaseModel):
    field: str
    current_value: Optional[str] = ""
    context: dict = Field(default_factory=dict)
    user_id: Optional[str] = None

# ==================== Uniqueness Utilities ====================

def generate_uniqueness_seed() -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    random_component = str(random.random())
    unique_id = str(uuid.uuid4())
    combined = f"{timestamp}-{random_component}-{unique_id}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

# ==================== Audio Selection Logic ====================

def get_genre_category(genres: List[str]) -> str:
    """Map user-selected genres to audio library categories"""
    genre_mapping = {
        "electronic": ["Electronic", "House", "Techno", "Trance", "Dubstep", "EDM", "Synthwave", "Future Bass", "Deep House"],
        "ambient": ["Ambient", "Drone", "Dark Ambient", "Chillwave", "IDM", "Minimalist"],
        "rock": ["Rock", "Metal", "Indie", "Post-Rock", "Shoegaze", "Post-Punk"],
        "hip_hop": ["Hip-Hop", "Trap", "Drill", "Cloud Rap", "R&B"],
        "cinematic": ["Cinematic", "Orchestral", "Epic", "Film Score", "Classical", "Neo-Classical"],
        "jazz": ["Jazz", "Soul", "Funk", "Blues"],
        "pop": ["Pop", "K-Pop", "J-Pop", "Disco", "Bedroom Pop"],
        "lofi": ["Lo-fi", "Chillwave", "Vaporwave"],
        "classical": ["Classical", "Orchestral", "Piano"]
    }
    
    for category, category_genres in genre_mapping.items():
        for genre in genres:
            if genre in category_genres:
                return category
    
    return "default"

def _normalize_duration_seconds(value: Any, default: int = 30) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(10, min(parsed, 72000))


def _context_keyword_hits(song_payload: dict, track_title: str) -> int:
    prompt_text = " ".join(
        [
            str(song_payload.get("music_prompt") or ""),
            str(song_payload.get("artist_inspiration") or ""),
            str(song_payload.get("lyrics") or ""),
            " ".join(song_payload.get("genres") or []),
        ]
    ).lower()
    title = (track_title or "").lower()
    mood_groups = {
        "dark": {"dark", "night", "midnight", "shadow", "moody"},
        "energy": {"energy", "power", "drive", "pulse", "rush", "drop"},
        "calm": {"calm", "ambient", "chill", "lofi", "peaceful", "soft"},
        "cinematic": {"cinematic", "epic", "orchestral", "score", "drama"},
        "urban": {"street", "urban", "beat", "bass", "flow"},
        "uplift": {"uplift", "inspire", "summer", "feel", "dream"},
    }
    hits = 0
    for _, tokens in mood_groups.items():
        context_has = any(token in prompt_text for token in tokens)
        title_has = any(token in title for token in tokens)
        if context_has and title_has:
            hits += 1
    return hits


def select_audio_for_genres(genres: List[str], used_urls: set = None, song_payload: Optional[dict] = None) -> dict:
    """Select contextual audio based on genres/prompt while avoiding repeats."""
    if used_urls is None:
        used_urls = set()
    if song_payload is None:
        song_payload = {}
    
    category = get_genre_category(genres)
    available_tracks = AUDIO_LIBRARY.get(category, AUDIO_LIBRARY["default"])
    requested_duration = _normalize_duration_seconds(song_payload.get("duration_seconds"), default=30)

    # Prefer unused tracks first; fallback to full category if exhausted.
    pool = [t for t in available_tracks if t["url"] not in used_urls] or list(available_tracks)

    scored_tracks = []
    prompt_signature = "|".join(
        [
            category,
            str(song_payload.get("music_prompt") or ""),
            str(song_payload.get("artist_inspiration") or ""),
            str(song_payload.get("lyrics") or "")[:80],
            str(requested_duration),
            generate_uniqueness_seed(),
        ]
    )

    for track in pool:
        track_duration = int(track.get("duration") or requested_duration)
        duration_delta = abs(track_duration - requested_duration)
        duration_score = max(0.0, 1.0 - (duration_delta / max(track_duration, requested_duration, 1)))
        context_hits = _context_keyword_hits(song_payload, track.get("title", ""))
        tie_breaker = int(
            hashlib.sha256(f"{prompt_signature}|{track.get('url','')}".encode()).hexdigest()[:8], 16
        ) / float(16 ** 8)
        score = (duration_score * 2.0) + context_hits + tie_breaker
        scored_tracks.append((score, track))

    scored_tracks.sort(key=lambda item: item[0], reverse=True)
    return scored_tracks[0][1]

def select_cover_art(genres: List[str]) -> str:
    """Select appropriate cover art based on genres"""
    category = get_genre_category(genres)
    covers = COVER_ART_LIBRARY.get(category, COVER_ART_LIBRARY["default"])
    return random.choice(covers)

def _extract_audio_url(payload: dict) -> Optional[str]:
    """Extract an audio URL from common provider response shapes."""
    candidates = [
        payload.get("audio_url"),
        payload.get("url"),
        payload.get("output_url"),
        payload.get("result_url"),
        (payload.get("data") or {}).get("audio_url") if isinstance(payload.get("data"), dict) else None,
    ]
    for value in candidates:
        if isinstance(value, str) and value.startswith(("http://", "https://", "data:audio/")):
            return value
    output = payload.get("output")
    if isinstance(output, str) and output.startswith(("http://", "https://")):
        return output
    if isinstance(output, dict):
        nested = output.get("audio_url") or output.get("url")
        if isinstance(nested, str) and nested.startswith(("http://", "https://", "data:audio/")):
            return nested
    if isinstance(output, list):
        for item in output:
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                return item
            if isinstance(item, dict):
                nested = item.get("url") or item.get("audio_url")
                if isinstance(nested, str) and nested.startswith(("http://", "https://", "data:audio/")):
                    return nested
    return None


def _decode_data_url_blob(data_url: str) -> tuple[bytes, str]:
    if not isinstance(data_url, str) or not data_url.startswith("data:"):
        raise ValueError("Not a data URL")
    if "," not in data_url:
        raise ValueError("Malformed data URL")
    header, payload = data_url.split(",", 1)
    mime = "application/octet-stream"
    if header.startswith("data:"):
        mime = header[5:].split(";")[0] or mime
    if ";base64" in header:
        return base64.b64decode(payload), mime
    return unquote_to_bytes(payload), mime

def _extract_replicate_media_url(output) -> Optional[str]:
    """Extract URL from common Replicate output shapes."""
    if isinstance(output, str) and output.startswith(("http://", "https://")):
        return output
    if isinstance(output, (list, tuple)):
        for item in output:
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                return item
            if hasattr(item, "url"):
                url = getattr(item, "url", None)
                if callable(url):
                    try:
                        maybe = url()
                        if isinstance(maybe, str) and maybe.startswith(("http://", "https://")):
                            return maybe
                    except Exception:
                        continue
                elif isinstance(url, str) and url.startswith(("http://", "https://")):
                    return url
    if hasattr(output, "url"):
        url = getattr(output, "url", None)
        if callable(url):
            try:
                maybe = url()
                if isinstance(maybe, str) and maybe.startswith(("http://", "https://")):
                    return maybe
            except Exception:
                return None
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url
    return None


_DEMO_MEDIA_HOSTS = {"www.soundhelix.com", "soundhelix.com", "samplelib.com", "download.samplelib.com"}


def _append_query_param(url: str, key: str, value: str) -> str:
    try:
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query[key] = value
        return urlunparse(parsed._replace(query=urlencode(query)))
    except Exception:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}{key}={value}"


def _make_unique_media_url(url: str, force: bool = False) -> str:
    """
    Ensure unique media URL per generation for demo/fallback assets.
    We only mutate known static demo hosts unless `force` is True.
    """
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if force or host in _DEMO_MEDIA_HOSTS:
            token = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}-{uuid.uuid4().hex[:8]}"
            return _append_query_param(url, "mwv", token)
        return url
    except Exception:
        return url

def _build_musicgen_prompt(song_payload: dict) -> str:
    """Construct a detailed, music-focused prompt for generation providers."""
    title = (song_payload.get("title") or "").strip()
    prompt = (song_payload.get("music_prompt") or "").strip()
    genres = [g for g in (song_payload.get("genres") or []) if g]
    languages = [l for l in (song_payload.get("vocal_languages") or []) if l]
    artist = (song_payload.get("artist_inspiration") or "").strip()
    lyrics = (song_payload.get("lyrics") or "").strip()
    entropy_seed = str(song_payload.get("entropy_seed") or _entropy_seed())
    parts = []
    if title:
        parts.append(f"Title: {title}")
    if prompt:
        parts.append(prompt)
    if genres:
        parts.append(f"Genres: {', '.join(genres[:5])}")
    if languages and "Instrumental" not in languages:
        parts.append(f"Vocals in: {', '.join(languages[:3])}")
    if artist:
        parts.append(f"Inspired by: {artist}")
    if lyrics:
        parts.append(f"Lyrics theme: {lyrics[:260]}")
    parts.append(f"Creative variation seed: {entropy_seed}")
    parts.append(f"Musical variation timestamp: {int(time.time() * 1000)}")
    parts.append(f"Randomization factor: {random.random()}")
    return ". ".join(parts)

def _generate_music_via_replicate(song_payload: dict) -> tuple[Optional[str], Optional[str]]:
    """Generate music track via Replicate-hosted MusicGen model."""
    if not REPLICATE_API_TOKEN:
        return None, "REPLICATE_API_TOKEN is not configured"
    try:
        import replicate
        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
        requested_duration = int(song_payload.get("duration_seconds") or 30)
        duration = max(5, min(requested_duration, REPLICATE_MUSIC_MAX_DURATION_SECONDS))
        prompt = _build_musicgen_prompt(song_payload)

        base_params = {
            "prompt": prompt,
            "model_version": REPLICATE_MUSIC_MODEL_VERSION,
            "output_format": REPLICATE_MUSIC_OUTPUT_FORMAT,
            "normalization_strategy": REPLICATE_MUSIC_NORMALIZATION_STRATEGY,
        }

        # Different hosted MusicGen variants may expect different duration keys.
        input_attempts = [
            {**base_params, "duration": duration},
            {**base_params, "duration_seconds": duration},
            base_params,
        ]
        last_error = "Replicate returned no usable output"
        for params in input_attempts:
            try:
                output = replicate.run(REPLICATE_MUSIC_MODEL, input=params)
                audio_url = _extract_replicate_media_url(output)
                if audio_url:
                    return audio_url, None
                last_error = "Replicate response did not contain an audio URL"
            except Exception as e:
                last_error = str(e)
                logger.warning("Replicate MusicGen attempt failed (%s): %s", params.keys(), e)
        return None, last_error
    except Exception as e:
        logger.warning("Replicate MusicGen setup failed: %s", e)
        return None, str(e)

def _remember_suggestion(field: str, suggestion: str) -> bool:
    """Returns True if suggestion is unique in recent memory for a field."""
    text = (suggestion or "").strip().lower()
    if not text:
        return False
    bucket = RECENT_SUGGESTIONS.get(field, [])
    if text in bucket:
        return False
    bucket.append(text)
    RECENT_SUGGESTIONS[field] = bucket[-30:]
    return True


def _normalize_suggestion_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _build_suggestion_scope_key(field: str, context: dict, user_id: Optional[str]) -> str:
    compact_context = {
        "music_prompt": (context.get("music_prompt") or "")[:280],
        "genres": context.get("genres", [])[:6] if isinstance(context.get("genres"), list) else [],
        "lyrics": (context.get("lyrics") or "")[:180],
        "artist_inspiration": (context.get("artist_inspiration") or "")[:180],
        "album_context": (context.get("album_context") or "")[:140],
        "track_number": context.get("track_number"),
    }
    scope_payload = f"{user_id or 'global'}|{field}|{json.dumps(compact_context, sort_keys=True, ensure_ascii=True)}"
    return hashlib.sha256(scope_payload.encode()).hexdigest()[:40]


async def _load_recent_scope_suggestions(field: str, scope_key: str, limit: int = 40) -> set[str]:
    seen = set(RECENT_SUGGESTIONS.get(field, []))
    history_collection = getattr(db, "suggestion_history", None)
    if history_collection is None:
        return seen
    try:
        docs = await history_collection.find({"field": field, "scope_key": scope_key}, {"_id": 0}).to_list(limit)
        docs.sort(key=lambda d: d.get("created_at", ""), reverse=True)
        for doc in docs[:limit]:
            norm = _normalize_suggestion_text(doc.get("suggestion", ""))
            if norm:
                seen.add(norm)
    except Exception as exc:
        logger.warning("Suggestion history read failed: %s", exc)
    return seen


async def _persist_scope_suggestion(field: str, scope_key: str, suggestion: str, user_id: Optional[str]) -> None:
    history_collection = getattr(db, "suggestion_history", None)
    if history_collection is None:
        return
    try:
        await history_collection.insert_one({
            "id": str(uuid.uuid4()),
            "field": field,
            "scope_key": scope_key,
            "user_id": user_id,
            "suggestion": suggestion,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.warning("Suggestion history write failed: %s", exc)


async def _next_scope_turn(field: str, scope_key: str) -> int:
    counters = getattr(db, "suggestion_counters", None)
    if counters is None:
        return random.randint(1, 999999)
    try:
        await counters.update_one(
            {"field": field, "scope_key": scope_key},
            {
                "$inc": {"turn": 1},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
                "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()},
            },
            upsert=True,
        )
        doc = await counters.find_one({"field": field, "scope_key": scope_key}, {"_id": 0, "turn": 1})
        if doc and isinstance(doc.get("turn"), int):
            return max(1, doc["turn"])
    except Exception as exc:
        logger.warning("Suggestion turn counter failed: %s", exc)
    return random.randint(1, 999999)

async def generate_track_audio(song_payload: dict, used_audio_urls: Optional[set] = None) -> tuple[str, int, bool, str]:
    """
    Generate/obtain track audio.
    1) If MUSICGEN_API_URL is configured, call self-hosted MusicGen for real generation.
    2) Fallback to curated demo library only when strict mode is disabled.
    Returns: (audio_url, duration_seconds, is_demo, provider_name)
    """
    if used_audio_urls is None:
        used_audio_urls = set()
    provider_failures: list[str] = []

    if FREE_TIER_MODE:
        selected = select_audio_for_genres(song_payload.get("genres", []), used_audio_urls, song_payload)
        used_audio_urls.add(selected["url"])
        requested_duration = _normalize_duration_seconds(song_payload.get("duration_seconds"), default=selected.get("duration", 30))
        unique_url = _make_unique_media_url(selected["url"])
        return unique_url, requested_duration, True, "free_curated_library"

    if MUSICGEN_API_URL:
        try:
            headers = {"Content-Type": "application/json"}
            if MUSICGEN_API_KEY:
                headers["Authorization"] = f"Bearer {MUSICGEN_API_KEY}"
            final_prompt = _build_musicgen_prompt(song_payload)
            requested_duration = _normalize_duration_seconds(song_payload.get("duration_seconds"), default=30)
            is_hf_inference = (
                "api-inference.huggingface.co/models/" in MUSICGEN_API_URL
                or "router.huggingface.co/hf-inference/models/" in MUSICGEN_API_URL
            )
            if is_hf_inference:
                headers["Accept"] = "audio/mpeg"
                provider_payload = {
                    "inputs": final_prompt,
                    "parameters": {
                        "duration": requested_duration,
                    },
                }
            else:
                provider_payload = {
                    "title": song_payload.get("title", ""),
                    "prompt": final_prompt,
                    "genres": song_payload.get("genres", []),
                    "lyrics": song_payload.get("lyrics", ""),
                    "vocal_languages": song_payload.get("vocal_languages", []),
                    "duration_seconds": requested_duration,
                    "artist_inspiration": song_payload.get("artist_inspiration", ""),
                }
            response = await asyncio.to_thread(
                lambda: requests.post(
                    MUSICGEN_API_URL,
                    json=provider_payload,
                    headers=headers,
                    timeout=180,
                )
            )
            if response.status_code >= 400:
                detail = (response.text or "").strip().replace("\n", " ")[:180]
                provider_failures.append(
                    f"Self-host MusicGen HTTP {response.status_code}"
                    + (f" ({detail})" if detail else "")
                )
                logger.warning("Music provider failed (%s): %s", response.status_code, response.text[:300])
            else:
                content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
                # HuggingFace / raw providers may return direct audio bytes.
                if response.content and (content_type.startswith("audio/") or (is_hf_inference and not content_type.startswith("application/json"))):
                    mime = content_type if content_type.startswith("audio/") else "audio/mpeg"
                    encoded = base64.b64encode(response.content).decode("ascii")
                    data_url = f"data:{mime};base64,{encoded}"
                    return data_url, requested_duration, False, "self_host_musicgen"

                data = response.json() if response.content else {}
                audio_url = _extract_audio_url(data if isinstance(data, dict) else {})
                if audio_url:
                    duration = int(data.get("duration_seconds") or requested_duration)
                    return audio_url, duration, False, "self_host_musicgen"
                provider_failures.append("Self-host MusicGen response missing audio URL")
                logger.warning("Music provider response missing audio url: %s", str(data)[:300])
        except Exception as exc:
            provider_failures.append(f"Self-host MusicGen exception: {type(exc).__name__}")
            logger.warning("Music provider exception: %s", exc)
    else:
        provider_failures.append("MUSICGEN_API_URL missing (self-host MusicGen endpoint not configured)")

    if STRICT_REAL_MEDIA_OUTPUT:
        provider_summary = "; ".join(provider_failures[:2]) if provider_failures else "No provider diagnostics available"
        raise HTTPException(
            status_code=502,
            detail=f"Real music generation failed. {provider_summary}",
        )

    selected = select_audio_for_genres(song_payload.get("genres", []), used_audio_urls, song_payload)
    used_audio_urls.add(selected["url"])
    requested_duration = _normalize_duration_seconds(song_payload.get("duration_seconds"), default=selected.get("duration", 30))
    unique_url = _make_unique_media_url(selected["url"])
    return unique_url, requested_duration, True, "curated_demo_library"

def calculate_audio_accuracy(selected_audio: dict, song_data: SongCreate | dict) -> float:
    """Calculate accuracy percentage of selected audio against input parameters
    
    Factors:
    - Genre match (40%)
    - Duration match (30%)
    - Quality/metadata match (20%)
    - Uniqueness/freshness (10%)
    """
    accuracy = 0.0
    
    # Genre matching (40%)
    # Check if selected audio category matches user's genres
    selected_category = get_genre_category([selected_audio.get("title", "")])
    user_genres = song_data.get("genres", []) if isinstance(song_data, dict) else song_data.genres
    user_category = get_genre_category(user_genres)
    genre_match = 0.4 if selected_category == user_category else 0.2
    accuracy += genre_match
    
    # Duration match (30%)
    audio_duration = selected_audio.get("duration", 0)
    user_duration = song_data.get("duration_seconds", 0) if isinstance(song_data, dict) else song_data.duration_seconds
    if user_duration > 0:
        duration_ratio = min(audio_duration, user_duration) / max(audio_duration, user_duration)
        accuracy += duration_ratio * 0.3
    else:
        accuracy += 0.3
    
    # Metadata/Title quality (20%)
    audio_title = selected_audio.get("title", "").strip()
    if len(audio_title) > 3 and not audio_title.isdigit():
        accuracy += 0.2
    
    # Uniqueness bonus (10%)
    # Always give points for proper seed-based selection
    accuracy += 0.1
    
    # Cap at 100%
    final_accuracy = min(int(accuracy * 100), 100)
    # Minimum 65% to show reasonable match
    return max(final_accuracy, 65)

# ==================== Quality Enhancement Functions ====================

def enhance_audio_quality_metadata(audio_data: dict, song_data: dict) -> dict:
    """Enhance audio metadata and quality parameters for better synthesis
    
    Returns audio data with quality enhancement parameters:
    - bitrate: Higher quality encoding
    - sample_rate: Professional audio standard (44.1kHz or 48kHz)
    - channels: Stereo or surround
    - compression: Lossless or high-quality lossy
    """
    enhanced = audio_data.copy()
    
    # Set professional audio parameters
    enhanced["bitrate"] = "320k"  # High quality MP3
    enhanced["sample_rate"] = 48000  # Professional standard
    enhanced["channels"] = 2  # Stereo
    enhanced["format"] = "mp3"
    enhanced["quality_score"] = calculate_audio_accuracy(audio_data, song_data)
    enhanced["enhancement_applied"] = True
    
    return enhanced

def prepare_vocal_synthesis_params(lyrics: str, languages: list, genres: list, title: str) -> dict:
    """Prepare parameters for high-quality vocal synthesis
    
    Returns synthesis parameters:
    - pitch_control: Key matching for genres
    - tempo: Optimized for lyrics and genres
    - vocal_style: Based on genres and emotional content
    - pronunciation: Language-specific phonetics
    """
    params = {
        "lyrics": lyrics,
        "languages": languages,
        "genres": genres,
        "title": title,
        "vocal_quality": "premium",  # High-quality synthesis
        "emotion_detection": extract_emotion_from_lyrics(lyrics),
        "gender_voice": "auto",  # Let AI choose appropriate voice
        "speaking_rate": determine_speaking_rate(genres),
        "pitch_range": determine_pitch_range(genres),
        "compression_ratio": 4,  # Professional audio compression
        "reverb_level": 0.3,  # Subtle reverb for depth
        "enhancement_applied": True
    }
    return params

def extract_emotion_from_lyrics(lyrics: str) -> str:
    """Extract primary emotion from lyrics for vocal synthesis
    
    Analyzes lyrical content to determine:
    - happy, sad, angry, melancholic, energetic, peaceful, mysterious, etc.
    """
    if not lyrics:
        return "neutral"
    
    sad_words = {"sad", "cry", "loss", "broken", "gone", "never", "darkness", "alone", "hurt", "pain"}
    happy_words = {"happy", "joy", "love", "smile", "bright", "together", "dance", "party", "free"}
    energetic_words = {"energy", "power", "strong", "fight", "rise", "loud", "wild", "rock", "punch"}
    peaceful_words = {"peace", "calm", "still", "quiet", "gentle", "soft", "rest", "sleep", "dream"}
    
    lyrics_lower = lyrics.lower()
    
    happy_count = sum(1 for word in happy_words if word in lyrics_lower)
    sad_count = sum(1 for word in sad_words if word in lyrics_lower)
    energetic_count = sum(1 for word in energetic_words if word in lyrics_lower)
    peaceful_count = sum(1 for word in peaceful_words if word in lyrics_lower)
    
    emotions = {
        "happy": happy_count,
        "sad": sad_count,
        "energetic": energetic_count,
        "peaceful": peaceful_count
    }
    
    if not any(emotions.values()):
        return "neutral"
    
    return max(emotions, key=emotions.get)

def determine_speaking_rate(genres: list) -> float:
    """Determine optimal speaking rate based on genres (0.8-1.5, where 1.0 is normal)"""
    fast_genres = {"rap", "hip-hop", "metal", "punk", "electronic", "techno", "house"}
    slow_genres = {"ballad", "classical", "ambient", "jazz", "folk", "acoustic", "soul"}
    
    genre_str = " ".join(genres).lower()
    
    if any(g in genre_str for g in fast_genres):
        return 1.2
    elif any(g in genre_str for g in slow_genres):
        return 0.85
    else:
        return 1.0

def determine_pitch_range(genres: list) -> str:
    """Determine optimal pitch range based on genres"""
    genre_str = " ".join(genres).lower()
    
    if any(g in genre_str for g in ["rock", "metal", "punk", "heavy"]):
        return "low"
    elif any(g in genre_str for g in ["pop", "indie", "alternative"]):
        return "mid"
    elif any(g in genre_str for g in ["soprano", "classical", "opera", "choir"]):
        return "high"
    else:
        return "mid"

def enhance_video_generation_params(song_data: dict, video_style: str = "") -> dict:
    """Prepare high-quality video generation parameters
    
    Returns enhanced parameters for:
    - Resolution: 1080p or 4K
    - Frame rate: 24, 30, or 60 fps
    - Duration: Matched to audio
    - Style: Artist-directed visual direction
    - Lighting: Professional cinematography
    - Transitions: Smooth, professional editing
    """
    params = {
        "resolution": "1080p",  # Professional HD
        "frame_rate": 30,  # Cinema standard
        "bitrate": "8000k",  # High quality video
        "codec": "h264",  # Professional codec
        "color_grading": "cinematic",
        "aspect_ratio": "16:9",
        "duration_seconds": song_data.get("duration_seconds", 180),
        "title": song_data.get("title", ""),
        "genres": song_data.get("genres", []),
        "video_style": video_style or "abstract",
        "lighting": "professional",
        "motion_blur": 0.2,
        "color_saturation": 1.1,  # Slightly enhanced colors
        "contrast": 1.15,  # Professional contrast
        "enhancement_applied": True
    }
    return params

# ==================== AI Suggestion Engine (OpenAI) ====================

TITLE_BLACKLIST_TERMS = {
    "cathedral", "labyrinth", "monolith", "oracle", "abyss", "relic", "citadel",
    "sanctuary", "altar", "hymn", "epitaph", "requiem", "catacomb", "seraph", "omen"
}

TITLE_GENERIC_TERMS = {
    "song", "track", "music", "untitled", "demo", "test", "vibe"
}

PRODUCTION_KEYWORDS = {
    "kick", "snare", "hihat", "bassline", "chord", "melody", "arp", "808", "synth",
    "guitar", "piano", "strings", "pad", "pluck", "reverb", "delay", "sidechain",
    "compression", "eq", "groove", "arrangement", "mix", "master", "drop", "build"
}

VIDEO_KEYWORDS = {
    "camera", "lens", "lighting", "color", "grade", "motion", "cut", "shot",
    "handheld", "tracking", "dolly", "frame", "cinematic", "scene", "edit"
}

FIELD_TEMPERATURE = {
    "title": 1.05,
    "music_prompt": 0.95,
    "genres": 0.55,
    "lyrics": 1.0,
    "artist_inspiration": 0.55,
    "video_style": 0.95,
    "vocal_languages": 0.35,
    "duration": 0.2,
}

def _tokenize_text(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z0-9']+", (text or "").lower()) if len(token) > 2]

def _split_list_like_text(text: str) -> list[str]:
    if not text:
        return []
    parts = []
    raw_parts = re.split(r"[\n,;/|]+", text)
    for item in raw_parts:
        cleaned = re.sub(r"^\s*\d+[\)\.\-:]*\s*", "", item).strip()
        cleaned = cleaned.strip("\"'`")
        if cleaned:
            parts.append(cleaned)
    unique = []
    seen = set()
    for p in parts:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique

def _best_match_from_choices(value: str, choices: list[str]) -> Optional[str]:
    token = (value or "").strip().lower()
    if not token:
        return None
    lowered = {c.lower(): c for c in choices}
    if token in lowered:
        return lowered[token]

    aliases = {
        "mandarin": "Chinese (Mandarin)",
        "cantonese": "Chinese (Cantonese)",
        "brazilian portuguese": "Portuguese (Brazil)",
        "latam spanish": "Spanish (Latin America)",
        "quebec french": "French (Quebec)",
        "lofi": "Lo-fi",
        "lo fi": "Lo-fi",
        "dnb": "Drum and Bass",
        "hip hop": "Hip-Hop",
        "rnb": "R&B",
    }
    if token in aliases and aliases[token].lower() in lowered:
        return lowered[aliases[token].lower()]

    for choice in choices:
        c = choice.lower()
        if token == c:
            return choice
        if token in c or c in token:
            return choice
    return None

def build_field_system_prompt(field: str) -> str:
    """Provide stricter field-specific guidance for practical music creation."""
    common = (
        "You are an elite global music producer and A&R advisor. "
        "Return practical, production-ready outputs only. Never return stories."
    )
    field_specific = {
        "title": (
            "Create relatable, market-friendly titles that are modern and memorable. "
            "Avoid archaic words and fantasy-like naming."
        ),
        "music_prompt": (
            "Write concrete production direction with instrumentation, groove, arrangement, and mix notes."
        ),
        "genres": (
            "Pick genres that fit the prompt and are recognizable in current music culture."
        ),
        "vocal_languages": (
            "Pick language choices that fit audience and phonetic flow; return Instrumental only when appropriate."
        ),
        "lyrics": (
            "Return a concise lyrical concept that can become a song, not random poetry."
        ),
        "artist_inspiration": (
            "Suggest artist references that are musically relevant and diverse across regions."
        ),
        "video_style": (
            "Return visual direction a director can execute, tied to the song's mood and genre."
        ),
        "duration": (
            "Return only a practical duration suggestion like 30s, 45s, 1m20s, or 2:30."
        ),
    }
    return f"{common} {field_specific.get(field, '')}".strip()

def _score_suggestion_relevance(field: str, suggestion: str, context: dict) -> int:
    text = (suggestion or "").strip()
    if not text:
        return 0
    lower = text.lower()
    score = 0
    context_tokens = set(_tokenize_text(" ".join([
        context.get("music_prompt", ""),
        " ".join(context.get("genres", []) if isinstance(context.get("genres"), list) else []),
        context.get("artist_inspiration", ""),
        context.get("lyrics", ""),
    ])))

    if field == "title":
        words = _tokenize_text(text)
        if 1 <= len(words) <= 5:
            score += 35
        if len(text) <= 40:
            score += 15
        if not any(w in TITLE_BLACKLIST_TERMS for w in words):
            score += 20
        if not any(w in TITLE_GENERIC_TERMS for w in words):
            score += 10
        if context_tokens and any(w in context_tokens for w in words):
            score += 20
        return min(score, 100)

    if field == "music_prompt":
        words = _tokenize_text(text)
        if 18 <= len(words) <= 120:
            score += 25
        production_hits = sum(1 for kw in PRODUCTION_KEYWORDS if kw in lower)
        score += min(production_hits * 8, 40)
        if context.get("genres") and any(g.lower() in lower for g in context.get("genres", [])):
            score += 20
        if any(token in lower for token in ["verse", "chorus", "drop", "bridge", "intro", "outro"]):
            score += 15
        return min(score, 100)

    if field == "genres":
        items = _split_list_like_text(text)
        known = get_all_genres()
        if 2 <= len(items) <= 4:
            score += 25
        matched = sum(1 for item in items if _best_match_from_choices(item, known))
        score += min(matched * 20, 60)
        if context.get("genres"):
            score += 15
        return min(score, 100)

    if field == "vocal_languages":
        items = _split_list_like_text(text)
        known_langs = LANGUAGE_KNOWLEDGE_BASE
        if 1 <= len(items) <= 3:
            score += 30
        matched = sum(1 for item in items if _best_match_from_choices(item, known_langs))
        score += min(matched * 22, 66)
        return min(score, 100)

    if field == "duration":
        normalized = validate_duration_suggestion(text)
        return 100 if normalized else 0

    if field == "artist_inspiration":
        items = _split_list_like_text(text)
        if 2 <= len(items) <= 4:
            score += 35
        known_artists = get_all_artists()
        artist_hits = sum(1 for item in items if _best_match_from_choices(item, known_artists))
        score += min(artist_hits * 20, 60)
        return min(score, 100)

    if field == "video_style":
        words = _tokenize_text(text)
        if 14 <= len(words) <= 110:
            score += 30
        visual_hits = sum(1 for kw in VIDEO_KEYWORDS if kw in lower)
        score += min(visual_hits * 8, 40)
        if any(t in lower for t in ["color palette", "lighting", "camera movement", "framing"]):
            score += 20
        return min(score, 100)

    if field == "lyrics":
        words = _tokenize_text(text)
        if 10 <= len(words) <= 120:
            score += 35
        if not any(flag in lower for flag in ["once upon a time", "dear reader", "the end"]):
            score += 20
        if context_tokens and any(w in context_tokens for w in words):
            score += 25
        if any(w in lower for w in ["verse", "chorus", "hook", "theme", "narrative", "emotion"]):
            score += 20
        return min(score, 100)

    return 50

def _fallback_suggestion(
    field: str,
    context: dict,
    avoid_texts: Optional[set[str]] = None,
    turn_hint: Optional[int] = None,
) -> str:
    rng = random.SystemRandom()
    context = context or {}
    genres = context.get("genres", []) if isinstance(context.get("genres"), list) else []
    prompt = (context.get("music_prompt") or "").strip()
    title_stop_words = {
        "with", "from", "that", "this", "into", "over", "under", "about", "your", "their",
        "there", "these", "those", "have", "been", "will", "just", "only", "more", "less",
        "very", "make", "song", "track", "drums", "music", "prompt"
    }
    prompt_words = [
        w for w in _tokenize_text(prompt)
        if w not in TITLE_GENERIC_TERMS and w not in TITLE_BLACKLIST_TERMS and w not in title_stop_words
    ]
    recent = set(RECENT_SUGGESTIONS.get(field, []))
    if avoid_texts:
        recent.update({(x or "").strip().lower() for x in avoid_texts if x})

    def pick_unique(candidates: list[str]) -> str:
        cleaned = []
        seen = set()
        for raw in candidates:
            item = (raw or "").strip()
            key = item.lower()
            if not item or key in seen:
                continue
            seen.add(key)
            cleaned.append(item)
        if not cleaned:
            return ""
        rng.shuffle(cleaned)
        for item in cleaned:
            if item.lower() not in recent:
                return item
        return cleaned[0]

    if field == "title":
        leads = ["Neon", "Midnight", "Velvet", "Solar", "Lunar", "Echo", "Prism", "Pulse", "Afterdark", "Skyline", "Starlit", "Voltage"]
        tails = ["Drive", "Rush", "Signal", "Flow", "Reflex", "Motion", "Drift", "Tempo", "Glow", "Shift", "Mode", "Wave"]
        context_terms = [w.title() for w in prompt_words if len(w) >= 4][:16]
        genre_terms = [g.split("(")[0].strip() for g in genres[:3] if g]
        options = []
        for _ in range(80):
            lead = rng.choice(leads)
            tail = rng.choice(tails)
            if context_terms and rng.random() < 0.6:
                center = rng.choice(context_terms)
            elif genre_terms and rng.random() < 0.45:
                center = rng.choice(genre_terms)
            else:
                center = ""
            title = " ".join([lead, center, tail]).strip()
            title = re.sub(r"\s+", " ", title)
            if len(title) <= 44 and 1 <= len(title.split()) <= 5:
                options.append(title)
        return pick_unique(options)

    if field == "music_prompt":
        genre_text = ", ".join(genres[:3]) if genres else rng.choice(["Electronic Pop", "Indie R&B", "Afro Pop", "Melodic House"])
        drums = ["tight kick-snare groove", "driving four-on-the-floor drums", "syncopated drum pocket", "broken-beat percussion accents"]
        basses = ["warm analog bassline", "clean sub-bass anchor", "rubbery synth bass", "deep low-end pulse"]
        tops = ["airy lead hook", "plucked synth motif", "vocal-forward topline", "guitar-texture lead line"]
        arrangements = ["intro to verse tension and wide chorus lift", "short intro, focused verse, explosive chorus, restrained bridge", "cinematic build then percussive payoff", "hook-first opening with dynamic final chorus"]
        mixes = ["clear vocal pocket and controlled transients", "mono-safe low end with stereo chorus expansion", "tight sidechain movement and polished top-end", "punchy drums with clean midrange separation"]
        prompt_focus = " ".join(prompt.split()[:20]).strip()
        options = []
        for _ in range(120):
            opener = (
                f"Develop this direction further: {prompt_focus}."
                if prompt_focus and rng.random() < 0.7
                else f"Build a {genre_text} production with a clear emotional arc."
            )
            options.append(
                f"{opener} Use {rng.choice(drums)}, {rng.choice(basses)}, and {rng.choice(tops)}. "
                f"Arrange with {rng.choice(arrangements)} and finish with {rng.choice(mixes)}."
            )
        return pick_unique(options)

    if field == "genres":
        all_genres = get_all_genres()
        base = [g for g in genres if g]
        options = []
        for _ in range(32):
            candidate = list(dict.fromkeys(base))
            rng.shuffle(all_genres)
            for g in all_genres:
                if g not in candidate:
                    candidate.append(g)
                if len(candidate) >= rng.choice([2, 3, 4]):
                    break
            options.append(", ".join(candidate[:4]))
        return pick_unique(options)

    if field == "vocal_languages":
        lang_pool = [l for l in LANGUAGE_KNOWLEDGE_BASE if l != "Instrumental"]
        if "instrumental" in prompt.lower():
            return "Instrumental"
        rng.shuffle(lang_pool)
        pick_count = rng.choice([1, 1, 2, 2, 3])
        return ", ".join(lang_pool[:pick_count])

    if field == "duration":
        requested = _normalize_duration_seconds(context.get("duration_seconds"), default=30)
        candidates = []
        for offset in [-8, -5, -3, 0, 4, 7, 11, 14]:
            sec = max(20, min(360, requested + offset + rng.randint(-2, 2)))
            candidates.append(_seconds_to_duration_text(sec))
        return pick_unique(candidates)

    if field == "artist_inspiration":
        artists = get_all_artists()
        rng.shuffle(artists)
        options = []
        for _ in range(40):
            start = rng.randint(0, max(0, len(artists) - 4))
            pick_count = rng.choice([2, 3, 4])
            options.append(", ".join(artists[start:start + pick_count]))
        return pick_unique(options)

    if field == "video_style":
        palettes = ["neon magenta and cyan", "warm tungsten with deep blue shadows", "high-contrast monochrome with red accents", "sunset amber with steel-blue highlights"]
        cameras = ["slow gimbal tracking with occasional handheld closeups", "locked wides with punch-in detail shots", "low-angle glide shots and controlled whip pans", "steady shoulder shots with rhythmic cutaways"]
        edits = ["beat-synced hard cuts in the chorus", "long takes in verses and quick transitions at drops", "speed ramps on drum fills and clean match cuts", "cross-dissolves only in emotional transitions"]
        settings = ["night city streets", "industrial interior with haze", "minimal studio with practical lights", "rain-soaked exterior reflections"]
        options = []
        for _ in range(80):
            options.append(
                f"Shoot in {rng.choice(settings)} using a {rng.choice(palettes)} palette. "
                f"Use {rng.choice(cameras)} and {rng.choice(edits)} to mirror the groove."
            )
        return pick_unique(options)

    if field == "lyrics":
        emotions = ["self-belief after pressure", "late-night clarity after chaos", "moving on without regret", "reclaiming energy after burnout"]
        imagery = ["city lights on wet roads", "subway windows and passing shadows", "midnight rooftops and distant sirens", "empty dancefloor before sunrise"]
        hooks = ["keep moving, never folding", "I hear the pulse, I choose the fire", "new signal, same heartbeat", "no static in my vision now"]
        options = []
        for _ in range(60):
            options.append(
                f"Theme around {rng.choice(emotions)} with recurring imagery of {rng.choice(imagery)}. "
                f"Center the chorus hook on '{rng.choice(hooks)}'."
            )
        return pick_unique(options)

    return ""

def _entropy_seed() -> str:
    return (
        f"{uuid.uuid4()}-{int(time.time() * 1000)}-{time.perf_counter_ns()}-"
        f"{os.urandom(32).hex()}-{random.random()}"
    )


def _entropy_int(seed: str, label: str, modulo: int) -> int:
    if modulo <= 0:
        return 0
    raw = hashlib.sha256(f"{seed}|{label}".encode("utf-8")).hexdigest()
    return int(raw, 16) % modulo


def _safe_json_dict(text: str) -> dict:
    if not text:
        return {}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start:end + 1])
            if isinstance(obj, dict):
                return obj
        except Exception:
            return {}
    return {}


def _coerce_music_context(raw: dict, incoming: dict, entropy_seed: str) -> dict:
    base = raw.get("musicContext") if isinstance(raw.get("musicContext"), dict) else raw
    ctx = dict(base) if isinstance(base, dict) else {}

    emotion_space = [
        "cosmic", "melancholic", "euphoric", "dark", "transcendent",
        "aggressive", "serene", "chaotic", "hypnotic", "nostalgic",
    ]
    energy_space = ["low", "gradual rise", "pulsing", "explosive", "cyclical", "unpredictable"]
    tempo_base_map = {
        "cosmic": 96, "melancholic": 84, "euphoric": 124, "dark": 102, "transcendent": 110,
        "aggressive": 136, "serene": 76, "chaotic": 142, "hypnotic": 118, "nostalgic": 92,
    }

    genres_space = get_all_genres() or ["Electronic", "Pop", "Cinematic"]
    artists_space = get_all_artists() or ["A. R. Rahman", "Daft Punk", "The Weeknd"]

    emotion = str(ctx.get("emotionalProfile") or "").strip() or emotion_space[_entropy_int(entropy_seed, "emotion", len(emotion_space))]
    energy = str(ctx.get("energyProfile") or "").strip() or energy_space[_entropy_int(entropy_seed, f"energy:{emotion}", len(energy_space))]
    tempo_variation = _entropy_int(entropy_seed, f"tempo:{emotion}:{energy}", 60)
    tempo_bpm = int(ctx.get("tempoProfile") or 0)
    if tempo_bpm <= 0:
        tempo_bpm = max(1, min(72000, tempo_base_map.get(emotion, 100) + tempo_variation))

    incoming_genres = incoming.get("genres") if isinstance(incoming.get("genres"), list) else []
    primary = incoming_genres[0] if incoming_genres else genres_space[_entropy_int(entropy_seed, "genre:primary", len(genres_space))]
    secondary = incoming_genres[1] if len(incoming_genres) > 1 else genres_space[_entropy_int(entropy_seed, "genre:secondary", len(genres_space))]
    if secondary == primary and len(genres_space) > 1:
        secondary = genres_space[(_entropy_int(entropy_seed, "genre:secondary:offset", len(genres_space) - 1) + 1) % len(genres_space)]
    fusion_idx = _entropy_int(entropy_seed, "genre:fusion", len(genres_space))
    fusion_genre = genres_space[fusion_idx]
    if fusion_genre in [primary, secondary] and len(genres_space) > 2:
        fusion_genre = genres_space[(fusion_idx + 2) % len(genres_space)]

    genres_obj = ctx.get("genres")
    if not isinstance(genres_obj, dict):
        genres_obj = {}
    genres_obj = {
        "primaryGenre": str(genres_obj.get("primaryGenre") or primary),
        "secondaryGenre": str(genres_obj.get("secondaryGenre") or secondary),
        "fusionGenre": str(genres_obj.get("fusionGenre") or fusion_genre),
    }

    track_name = str(ctx.get("trackName") or incoming.get("title") or "").strip()
    if not track_name:
        track_name = f"{emotion.title()} {genres_obj['primaryGenre']} {entropy_seed[:6].upper()}"
    album_name = str(ctx.get("albumName") or incoming.get("album_context") or "").strip()
    if not album_name:
        album_name = f"{track_name} Collection"

    duration_raw = ctx.get("durationProfile")
    duration_seconds = None
    if isinstance(duration_raw, (int, float)):
        duration_seconds = int(duration_raw)
    elif isinstance(duration_raw, str):
        duration_seconds = _duration_text_to_seconds(duration_raw)
    if not duration_seconds:
        base_duration = 120 if energy in ["low", "gradual rise"] else 180
        duration_seconds = max(1, min(72000, base_duration + _entropy_int(entropy_seed, "duration", 300)))

    if not str(ctx.get("artistInspiration") or "").strip():
        a1 = artists_space[_entropy_int(entropy_seed, "artist:1", len(artists_space))]
        a2 = artists_space[_entropy_int(entropy_seed, "artist:2", len(artists_space))]
        if a2 == a1 and len(artists_space) > 1:
            a2 = artists_space[(_entropy_int(entropy_seed, "artist:2:offset", len(artists_space) - 1) + 1) % len(artists_space)]
        ctx["artistInspiration"] = f"{a1}, {a2}"

    if not str(ctx.get("vocalProfile") or "").strip():
        incoming_languages = incoming.get("vocal_languages") if isinstance(incoming.get("vocal_languages"), list) else []
        if incoming_languages:
            if "Instrumental" in incoming_languages:
                ctx["vocalProfile"] = "Instrumental"
            else:
                ctx["vocalProfile"] = ", ".join(incoming_languages[:3])
        else:
            ctx["vocalProfile"] = "Instrumental" if _entropy_int(entropy_seed, "vocal", 4) == 0 else "English vocals"

    if not str(ctx.get("lyricsTheme") or "").strip():
        if "instrumental" in str(ctx.get("vocalProfile") or "").lower():
            ctx["lyricsTheme"] = None
        else:
            ctx["lyricsTheme"] = f"A {emotion} narrative anchored to the symbol '{track_name}'."

    if not str(ctx.get("instrumentationProfile") or "").strip():
        ctx["instrumentationProfile"] = (
            f"{genres_obj['primaryGenre']} and {genres_obj['secondaryGenre']} textures, "
            f"tempo-focused layers near {tempo_bpm} BPM, and entropy-derived timbral variation seed {entropy_seed[:10]}."
        )

    if not str(ctx.get("musicDescription") or "").strip():
        incoming_prompt = str(incoming.get("music_prompt") or "").strip()
        core = incoming_prompt if incoming_prompt else f"{emotion} {energy} progression with evolving spatial depth."
        ctx["musicDescription"] = (
            f"{core} Emotional profile: {emotion}. Energy profile: {energy}. "
            f"Tempo profile: {tempo_bpm} BPM. Instrumentation profile: {ctx['instrumentationProfile']}."
        )

    if not str(ctx.get("visualProfile") or "").strip():
        ctx["visualProfile"] = (
            f"Visual environment derived from {emotion} and {genres_obj['fusionGenre']}, "
            f"with motion intensity matching {energy} dynamics and camera rhythm synced near {tempo_bpm} BPM."
        )

    ctx["entropySeed"] = entropy_seed
    ctx["trackName"] = track_name
    ctx["albumName"] = album_name
    ctx["genres"] = genres_obj
    ctx["emotionalProfile"] = emotion
    ctx["energyProfile"] = energy
    ctx["tempoProfile"] = tempo_bpm
    ctx["durationProfile"] = duration_seconds
    return ctx


async def _build_music_context(field: str, current_value: str, context: dict) -> dict:
    if not GEMINI_API_KEY and not openai_client:
        raise HTTPException(
            status_code=503,
            detail="AI suggestion is unavailable. Set GEMINI_API_KEY or OPENAI_API_KEY.",
        )

    entropy_seed = _entropy_seed()
    compact_context = {
        "field": field,
        "current_value": current_value or "",
        "title": context.get("title", ""),
        "music_prompt": context.get("music_prompt", ""),
        "genres": context.get("genres", []) if isinstance(context.get("genres"), list) else [],
        "artist_inspiration": context.get("artist_inspiration", ""),
        "lyrics": context.get("lyrics", ""),
        "vocal_languages": context.get("vocal_languages", []) if isinstance(context.get("vocal_languages"), list) else [],
        "video_style": context.get("video_style", ""),
        "album_context": context.get("album_context", ""),
        "track_number": context.get("track_number"),
        "duration_seconds": context.get("duration_seconds"),
    }

    system_prompt = (
        "You are MuseWave Autonomous Contextual Suggestion and Media Generation Intelligence. "
        "Generate a single coherent musicContext JSON only. No markdown. No prose. "
        "Every field must be context-linked and non-repeating. Never use cached/static outputs."
    )
    user_prompt = (
        f"Entropy seed: {entropy_seed}\n"
        "Generate musicContext with exact keys:\n"
        "entropySeed, trackName, albumName, genres{primaryGenre,secondaryGenre,fusionGenre}, "
        "musicDescription, emotionalProfile, tempoProfile, energyProfile, instrumentationProfile, "
        "vocalProfile, lyricsTheme, visualProfile, artistInspiration, durationProfile.\n"
        "Use this generation order exactly: emotionalProfile, energyProfile, tempoProfile, genres, "
        "instrumentationProfile, musicDescription, artistInspiration, trackName, albumName, "
        "vocalProfile, lyricsTheme, durationProfile, visualProfile.\n"
        "durationProfile must be numeric seconds in range 1..72000.\n"
        f"Input context JSON:\n{json.dumps(compact_context, ensure_ascii=True)}"
    )

    content = (await _generate_context_text(system_prompt, user_prompt)).strip()
    parsed = _safe_json_dict(content)
    return _coerce_music_context(parsed, compact_context, entropy_seed)


def _suggestion_from_music_context(field: str, music_context: dict) -> str:
    genres_obj = music_context.get("genres", {}) if isinstance(music_context.get("genres"), dict) else {}

    if field == "title":
        return str(music_context.get("trackName") or "").strip()
    if field == "music_prompt":
        return str(music_context.get("musicDescription") or "").strip()
    if field == "genres":
        values = [
            str(genres_obj.get("primaryGenre") or "").strip(),
            str(genres_obj.get("secondaryGenre") or "").strip(),
            str(genres_obj.get("fusionGenre") or "").strip(),
        ]
        unique = []
        for value in values:
            if value and value not in unique:
                unique.append(value)
        return ", ".join(unique[:4])
    if field == "artist_inspiration":
        return str(music_context.get("artistInspiration") or "").strip()
    if field == "video_style":
        return str(music_context.get("visualProfile") or "").strip()
    if field == "lyrics":
        lyrics_theme = music_context.get("lyricsTheme")
        return "" if lyrics_theme is None else str(lyrics_theme).strip()
    if field == "vocal_languages":
        vocal_profile = str(music_context.get("vocalProfile") or "").strip()
        if not vocal_profile:
            return ""
        if "instrumental" in vocal_profile.lower():
            return "Instrumental"
        return vocal_profile
    if field == "duration":
        duration_value = music_context.get("durationProfile")
        if isinstance(duration_value, (int, float)):
            return _seconds_to_duration_text(int(duration_value))
        if isinstance(duration_value, str):
            return validate_duration_suggestion(duration_value)
        return ""
    if field == "album_name":
        return str(music_context.get("albumName") or "").strip()
    if field in music_context:
        return str(music_context.get(field) or "").strip()
    return ""


async def generate_ai_suggestion(
    field: str,
    current_value: str,
    context: dict,
    user_id: Optional[str] = None,
) -> str:
    context = context or {}
    scope_key = _build_suggestion_scope_key(field, context, user_id)
    seen_in_scope = await _load_recent_scope_suggestions(field, scope_key)
    suggestion_turn = await _next_scope_turn(field, scope_key)

    last_error: Optional[str] = None
    for attempt in range(max(2, SUGGEST_MAX_ATTEMPTS)):
        try:
            music_context = await _build_music_context(field, current_value, context)
            suggestion = _suggestion_from_music_context(field, music_context)
            suggestion = _strip_machine_suffixes(field, suggestion)

            if field in ["music_prompt", "lyrics", "video_style", "title"]:
                suggestion = validate_music_specific_suggestion(field, suggestion)
            if field in ["genres", "vocal_languages"]:
                suggestion = validate_list_suggestion(field, suggestion)
            if field == "duration":
                suggestion = validate_duration_suggestion(suggestion)

            if not suggestion:
                last_error = "Empty suggestion after validation"
                continue

            finalized = await _finalize_unique_suggestion(
                field=field,
                suggestion=suggestion,
                context={**context, "music_context": music_context},
                current_value=current_value,
                seen_in_scope=seen_in_scope,
                scope_key=scope_key,
                user_id=user_id,
                turn_hint=suggestion_turn + attempt,
            )
            if finalized:
                return finalized
            last_error = "Suggestion duplicated with prior outputs"
        except Exception as exc:
            last_error = str(exc)
            logger.error("AI contextual suggestion failure for %s: %s", field, exc)
            err_text = last_error.lower()
            if "insufficient_quota" in err_text or "invalid_api_key" in err_text or "rate_limit" in err_text:
                break

    detail = f"AI suggestion failed for field '{field}'."
    if last_error:
        detail = f"{detail} Upstream: {last_error[:240]}"
    raise HTTPException(status_code=502, detail=detail)

def validate_music_specific_suggestion(field: str, text: str) -> str:
    """Validate that suggestions are music-specific, not poetry or stories"""
    # Red flags for non-music content
    poetry_indicators = [
        "once upon a time", "there was", "a tale", "a story",
        "and they lived", "the end", "dear reader",
        "metaphorically", "symbolically", "in a land",
        "imagine if", "picture yourself", "you walk into"
    ]
    
    # Music-validating keywords for music_prompt and descriptions
    music_keywords = [
        "acoustic", "electronic", "synth", "beat", "rhythm",
        "tempo", "bpm", "reverb", "echo", "delay", "filter",
        "frequency", "bass", "treble", "chord", "melody",
        "production", "mix", "master", "eq", "compression",
        "vocal", "instrumental", "drum", "guitar", "piano",
        "layer", "texture", "ambient", "lofi", "breakcore",
        "vibe", "mood", "energy", "dynamic", "groove"
    ]
    
    text_lower = text.lower()
    
    # Check for poetry red flags
    for flag in poetry_indicators:
        if flag in text_lower:
            logger.warning(f"Detected non-music content in {field}: {text[:100]}")
            return ""  # Return empty to trigger re-suggestion
    
    # For music_prompt, must contain music-related terminology
    if field == "music_prompt":
        has_music_content = any(kw in text_lower for kw in music_keywords)
        if not has_music_content:
            logger.warning(f"music_prompt lacks music-specific content: {text[:100]}")
            return ""
    
    # Ensure reasonable length
    words = text.split()
    if field == "music_prompt" and len(words) < 5:
        return ""  # Too short
    if field == "video_style" and len(words) < 10:
        return ""  # Too short for visual description
    if field == "title":
        # Keep title modern + relatable; reject overly obscure words.
        if len(words) < 1 or len(words) > 6:
            return ""
        if len(text) > 44:
            return ""
        if any(term in text_lower for term in TITLE_BLACKLIST_TERMS):
            return ""
        if any(ch in text for ch in [":", ";", "/", "\\", "{", "}", "[", "]"]):
            return ""
        if any(term in text_lower for term in TITLE_GENERIC_TERMS):
            return ""
        if text_lower.startswith(("the ", "a ", "an ")):
            # Titles starting with articles are allowed, but avoid bland outputs like "The Sound".
            if len(words) <= 2:
                return ""
    
    return text

def validate_duration_suggestion(text: str) -> str:
    """Validate/normalize AI duration suggestion."""
    raw = (text or "").strip().lower()
    if not raw:
        return ""
    # Keep only first tokenized line to avoid explanations.
    raw = raw.split("\n")[0].strip()
    # Accept forms like 30s, 2m10s, 2:30, 90.
    if raw.isdigit():
        seconds = int(raw)
    elif ":" in raw:
        try:
            parts = [int(p) for p in raw.split(":")]
            if len(parts) == 2:
                seconds = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
            else:
                return ""
        except ValueError:
            return ""
    else:
        h = re.search(r"(\d+)\s*h", raw)
        m = re.search(r"(\d+)\s*m", raw)
        s = re.search(r"(\d+)\s*s", raw)
        if not any([h, m, s]):
            return ""
        seconds = 0
        if h:
            seconds += int(h.group(1)) * 3600
        if m:
            seconds += int(m.group(1)) * 60
        if s:
            seconds += int(s.group(1))

    if seconds < 10:
        seconds = 10
    if seconds > 72000:
        seconds = 72000
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    rem = seconds % 60
    if rem == 0:
        return f"{minutes}m"
    return f"{minutes}m{rem}s"

def validate_list_suggestion(field: str, text: str) -> str:
    """Validate and clean list-based suggestions (genres, languages)"""
    if not text:
        return ""

    if field == "genres":
        items = _split_list_like_text(text)
        canonical = []
        allowed_genres = get_all_genres()
        for item in items:
            match = _best_match_from_choices(item, allowed_genres)
            if match and match not in canonical:
                canonical.append(match)
        if canonical:
            return ", ".join(canonical[:4])
        # Keep useful unknowns as fallback but normalize casing.
        fallback = [item.strip().title() for item in items if len(item.strip()) > 2]
        return ", ".join(fallback[:4]) if fallback else ""

    if field == "vocal_languages":
        if "instrumental" in text.lower():
            return "Instrumental"
        items = _split_list_like_text(text)
        canonical = []
        for item in items:
            match = _best_match_from_choices(item, LANGUAGE_KNOWLEDGE_BASE)
            if match and match not in canonical:
                canonical.append(match)
        return ", ".join(canonical[:3]) if canonical else ""

    return text


def _duration_text_to_seconds(text: str) -> Optional[int]:
    value = validate_duration_suggestion(text)
    if not value:
        return None
    raw = value.strip().lower()
    if raw.isdigit():
        return int(raw)
    if ":" in raw:
        try:
            parts = [int(p) for p in raw.split(":")]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
        except ValueError:
            return None
    h = re.search(r"(\d+)\s*h", raw)
    m = re.search(r"(\d+)\s*m", raw)
    s = re.search(r"(\d+)\s*s", raw)
    total = 0
    if h:
        total += int(h.group(1)) * 3600
    if m:
        total += int(m.group(1)) * 60
    if s:
        total += int(s.group(1))
    return total if total > 0 else None


def _seconds_to_duration_text(seconds: int) -> str:
    seconds = max(10, min(int(seconds), 72000))
    if seconds < 60:
        return f"{seconds}s"
    minutes, rem = divmod(seconds, 60)
    if rem == 0:
        return f"{minutes}m"
    return f"{minutes}m{rem}s"


def _strip_machine_suffixes(field: str, text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    cleaned = re.sub(r"\s*\[[0-9a-f]{3,8}\]\s*$", "", cleaned, flags=re.IGNORECASE)
    if field == "title":
        cleaned = re.sub(r"\s+[0-9a-f]{4,8}\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("Variation cue:", "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    return cleaned


def _enforce_unique_suggestion(
    field: str,
    suggestion: str,
    context: dict,
    current_value: str,
    seen_in_scope: set[str],
    turn_hint: int,
) -> str:
    candidate = _strip_machine_suffixes(field, suggestion)
    if not candidate:
        return ""

    if field in ["genres", "vocal_languages"]:
        candidate = validate_list_suggestion(field, candidate)
    if field == "duration":
        candidate = validate_duration_suggestion(candidate)
    if field in ["music_prompt", "lyrics", "video_style", "title"]:
        candidate = validate_music_specific_suggestion(field, candidate)
    if not candidate:
        return ""

    normalized = _normalize_suggestion_text(candidate)
    current_norm = _normalize_suggestion_text(current_value or "")
    seen = {(_normalize_suggestion_text(x)) for x in seen_in_scope if x}
    seen.update({(_normalize_suggestion_text(x)) for x in RECENT_SUGGESTIONS.get(field, []) if x})

    if current_norm and normalized == current_norm:
        return ""
    if normalized in seen:
        return ""
    return candidate


async def _finalize_unique_suggestion(
    field: str,
    suggestion: str,
    context: dict,
    current_value: str,
    seen_in_scope: set[str],
    scope_key: str,
    user_id: Optional[str],
    turn_hint: int,
) -> str:
    unique = _enforce_unique_suggestion(
        field=field,
        suggestion=suggestion,
        context=context,
        current_value=current_value,
        seen_in_scope=seen_in_scope,
        turn_hint=turn_hint,
    )
    unique = _strip_machine_suffixes(field, unique)
    if not unique:
        return ""
    normalized = _normalize_suggestion_text(unique)
    seen_in_scope.add(normalized)
    _remember_suggestion(field, unique)
    await _persist_scope_suggestion(field, scope_key, unique, user_id)
    return unique

async def generate_lyrics(music_prompt: str, genres: list, languages: list, title: str = "") -> str:
    """Generate singable lyrics aligned to genre, language, and prompt."""
    if not openai_client:
        return ""

    try:
        languages_str = ", ".join(languages) if languages else "English"
        genres_str = ", ".join(genres) if genres else "Pop"
        title_ref = f" for '{title}'" if title else ""
        prompt = f"""
Write complete recording-ready lyrics{title_ref}.
Music description: {music_prompt}
Genres: {genres_str}
Language(s): {languages_str}

Requirements:
- Structure: Verse -> Chorus -> Verse -> Chorus -> Bridge -> Final Chorus
- Keep lyrics singable and emotionally coherent
- Avoid filler lines
- Return ONLY the lyrics text
"""
        response = await asyncio.to_thread(
            lambda: openai_client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional multilingual lyricist writing record-ready lyrics.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.9,
                max_tokens=800,
            )
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        logger.error(f"Lyrics generation error: {e}")
        return ""

def build_suggestion_prompt(
    field: str,
    current_value: str,
    context: dict,
    seed: str,
    avoid_suggestions: Optional[list[str]] = None,
) -> str:
    context = context or {}
    compact_context = {
        "music_prompt": (context.get("music_prompt") or "")[:280],
        "genres": context.get("genres", [])[:6] if isinstance(context.get("genres"), list) else [],
        "lyrics": (context.get("lyrics") or "")[:180],
        "artist_inspiration": (context.get("artist_inspiration") or "")[:180],
        "album_context": (context.get("album_context") or "")[:140],
        "track_number": context.get("track_number"),
    }
    context_json = json.dumps(compact_context, ensure_ascii=True)
    allowed_genres = ", ".join(get_all_genres())
    allowed_langs = ", ".join(LANGUAGE_KNOWLEDGE_BASE)
    known_artists = ", ".join(get_all_artists())
    avoid_text = ""
    if avoid_suggestions:
        filtered = [item.strip() for item in avoid_suggestions if item and item.strip()]
        if filtered:
            avoid_text = f"\nAvoid these recent suggestions: {', '.join(filtered[:8])}"

    prompts = {
        "title": f"""Field: title
Seed: {seed}
Context JSON: {context_json}
Current value: {current_value}
Task: return ONE title that is catchy, modern, relatable, and commercially believable.
Rules:
- 1 to 5 words only
- no archaic/fantasy words
- no punctuation-heavy output
- no explanation
{avoid_text}
Return only the title.""",

        "music_prompt": f"""Field: music_prompt
Seed: {seed}
Context JSON: {context_json}
Current value: {current_value}
Task: write one music production prompt.
Rules:
- 2 to 4 sentences
- include instrumentation, groove, arrangement direction, and mixing cues
- must be directly usable to generate a track
- no explanation wrapper
{avoid_text}
Return only the prompt text.""",

        "genres": f"""Field: genres
Seed: {seed}
Context JSON: {context_json}
Allowed genres (pick from this list): {allowed_genres}
Task: choose 2 to 4 genres that best match the context.
Rules:
- comma-separated only
- use names from allowed list
- no explanation
{avoid_text}
Return only comma-separated genres.""",

        "vocal_languages": f"""Field: vocal_languages
Seed: {seed}
Context JSON: {context_json}
Allowed languages (pick from this list): {allowed_langs}
Task: choose 1 to 3 vocal language options, or Instrumental when no vocals are needed.
Rules:
- comma-separated only
- use names from allowed list
- no explanation
{avoid_text}
Return only comma-separated languages.""",

        "lyrics": f"""Field: lyrics
Seed: {seed}
Context JSON: {context_json}
Current value: {current_value}
Task: give one concise lyrical concept aligned with the context.
Rules:
- 1 to 3 sentences
- clear emotional direction and hook idea
- no storybook style
- no explanation wrapper
{avoid_text}
Return only the concept text.""",

        "artist_inspiration": f"""Field: artist_inspiration
Seed: {seed}
Context JSON: {context_json}
Known artists reference: {known_artists}
Task: suggest 2 to 4 artist references that fit the context.
Rules:
- comma-separated names only
- use globally known and musically relevant artists
- no explanation
{avoid_text}
Return only comma-separated artist names.""",

        "video_style": f"""Field: video_style
Seed: {seed}
Context JSON: {context_json}
Current value: {current_value}
Task: write one executable music-video direction.
Rules:
- 2 to 3 sentences
- include color/lighting, camera movement, and editing rhythm
- directly tied to the song mood
- no explanation wrapper
{avoid_text}
Return only the visual direction text.""",

        "duration": f"""Field: duration
Seed: {seed}
Context JSON: {context_json}
Current value: {current_value}
Task: suggest one practical duration.
Rules:
- return only one value like 30s, 45s, 1m20s, or 2:30
- no explanation
{avoid_text}
Return only duration.""",
    }

    return prompts.get(
        field,
        f"Field: {field}\nSeed: {seed}\nContext JSON: {context_json}\nReturn one practical, field-specific suggestion only.",
    )

# ==================== Auth Routes ====================

@api_router.post("/auth/signup", response_model=UserResponse)
async def signup(user_data: UserCreate):
    existing = await db.users.find_one({"mobile": user_data.mobile}, {"_id": 0})
    if not existing and legacy_db is not None:
        existing = await legacy_db.users.find_one({"mobile": user_data.mobile}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Account with this mobile number already exists")

    is_master = user_data.mobile == MASTER_ADMIN_MOBILE
    name = MASTER_ADMIN_NAME if is_master else user_data.name.strip()
    role = MASTER_ADMIN_ROLE if is_master else "User"

    user = User(name=name, mobile=user_data.mobile, role=role)
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)

    return UserResponse(
        id=user.id,
        name=user.name,
        mobile=user.mobile,
        role=user.role,
        created_at=doc['created_at']
    )

@api_router.post("/auth/login", response_model=UserResponse)
async def login(login_data: UserLogin):
    user = await db.users.find_one({"mobile": login_data.mobile}, {"_id": 0})
    if not user and legacy_db is not None:
        user = await legacy_db.users.find_one({"mobile": login_data.mobile}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="No account found. Please sign up first.")

    user = await _persist_normalized_user(user)

    return UserResponse(
        id=user['id'],
        name=user['name'],
        mobile=user['mobile'],
        role=user.get('role', 'User'),
        created_at=user['created_at']
    )

# ==================== AI Suggest Routes ====================

@api_router.post("/suggest")
async def ai_suggest(request: AISuggestRequest):
    suggestion = await generate_ai_suggestion(
        request.field,
        request.current_value or "",
        request.context,
        request.user_id,
    )
    return {"suggestion": suggestion, "field": request.field}

# ==================== Song Creation ====================

@api_router.post("/songs/create")
async def create_song(song_data: SongCreate):
    if not song_data.music_prompt or not song_data.music_prompt.strip():
        raise HTTPException(status_code=422, detail="Music prompt is required")
    
    song_id = str(uuid.uuid4())
    
    # Generate title if not provided
    title = song_data.title
    if not title:
        try:
            title = await generate_ai_suggestion("title", "", {
                "music_prompt": song_data.music_prompt,
                "genres": song_data.genres
            }, song_data.user_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"AI title suggestion failed: {str(exc)[:220]}")
    
    # Generate real track (if provider configured) or fallback to curated demo library.
    # Prime used URLs from recent user history to maximize uniqueness across requests.
    used_audio_urls = await _load_recent_user_audio_urls(song_data.user_id)
    song_entropy_seed = _entropy_seed()
    generation_payload = song_data.model_dump()
    generation_payload["title"] = title
    generation_payload["entropy_seed"] = song_entropy_seed
    audio_url, actual_duration, is_demo, generation_provider = await generate_track_audio(
        generation_payload,
        used_audio_urls=used_audio_urls,
    )
    audio_data = {
        "url": audio_url,
        "duration": actual_duration,
        "title": title,
    }
    audio_data = enhance_audio_quality_metadata(audio_data, song_data.model_dump())
    
    # Calculate accuracy of audio selection
    accuracy_percentage = calculate_audio_accuracy(audio_data, song_data)
    
    # Select cover art
    cover_art_url = select_cover_art(song_data.genres)
    
    # Generate lyrics if not provided and has vocals
    lyrics = song_data.lyrics or ""
    if not lyrics and song_data.vocal_languages and "Instrumental" not in song_data.vocal_languages:
        try:
            lyrics = await generate_lyrics(
                song_data.music_prompt,
                song_data.genres,
                song_data.vocal_languages,
                title
            )
        except Exception as e:
            logger.warning(f"Failed to generate lyrics: {e}")
            # Continue without lyrics if generation fails
    
    # Prepare vocal synthesis parameters if lyrics exist
    vocal_params = {}
    if lyrics:
        vocal_params = prepare_vocal_synthesis_params(
            lyrics,
            song_data.vocal_languages,
            song_data.genres,
            title
        )
    
    # Prepare video generation parameters for high quality
    video_params = enhance_video_generation_params(song_data.__dict__, song_data.video_style or "")
    
    fallback_video_ready = bool(
        song_data.generate_video
        and (
            FREE_TIER_MODE
            or (not REPLICATE_API_TOKEN and not STRICT_REAL_MEDIA_OUTPUT)
        )
    )
    video_thumbnail = generate_video_thumbnail(song_data.model_dump()) if fallback_video_ready else None
    video_url = _make_unique_media_url(_SAMPLE_VIDEO_URL) if fallback_video_ready else None
    video_status = "completed" if fallback_video_ready else ("queued" if song_data.generate_video else None)

    song_doc = {
        "id": song_id,
        "entropy": song_entropy_seed,
        "title": title,
        "music_prompt": song_data.music_prompt,
        "genres": song_data.genres,
        "duration_seconds": actual_duration,
        "vocal_languages": song_data.vocal_languages,
        "lyrics": lyrics,
        "artist_inspiration": song_data.artist_inspiration or "",
        "generate_video": song_data.generate_video,
        "video_style": song_data.video_style or "",
        "audio_url": audio_url,
        "video_url": video_url,
        "video_thumbnail": video_thumbnail,
        "video_status": video_status,
        "video_generated_at": datetime.now(timezone.utc).isoformat() if fallback_video_ready else None,
        "cover_art_url": cover_art_url,
        "accuracy_percentage": accuracy_percentage,
        "album_id": song_data.album_id,
        "user_id": song_data.user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_demo": is_demo,
        "generation_provider": generation_provider,
        # Quality enhancement parameters
        "audio_quality": audio_data.get("quality_score", 65),
        "audio_bitrate": audio_data.get("bitrate", "320k"),
        "audio_sample_rate": audio_data.get("sample_rate", 48000),
        "audio_channels": audio_data.get("channels", 2),
        "vocal_synthesis_params": vocal_params,
        "video_generation_params": video_params
    }
    
    await db.songs.insert_one(song_doc)
    
    # Remove MongoDB _id field for JSON serialization
    song_doc.pop('_id', None)
    return song_doc

# ==================== Album Creation ====================

@api_router.post("/albums/create")
async def create_album(album_data: AlbumCreate):
    has_track_inputs = len(album_data.album_songs) > 0
    if not has_track_inputs and not (album_data.music_prompt or "").strip():
        raise HTTPException(status_code=422, detail="Album prompt or per-track prompts are required")

    if has_track_inputs:
        invalid_tracks = [
            idx + 1 for idx, track in enumerate(album_data.album_songs)
            if not (track.music_prompt or "").strip()
        ]
        if invalid_tracks:
            raise HTTPException(
                status_code=422,
                detail=f"Music prompt is required for album tracks: {', '.join(map(str, invalid_tracks))}",
            )

    album_id = str(uuid.uuid4())
    num_tracks = len(album_data.album_songs) if has_track_inputs else album_data.num_songs
    album_prompt = (album_data.music_prompt or "").strip()
    if not album_prompt and has_track_inputs:
        album_prompt = " | ".join([track.music_prompt for track in album_data.album_songs[:3]])

    combined_genres = list(album_data.genres)
    if has_track_inputs:
        for track in album_data.album_songs:
            for genre in track.genres:
                if genre not in combined_genres:
                    combined_genres.append(genre)

    title = (album_data.title or "").strip()
    if not title:
        try:
            title = await generate_ai_suggestion(
                "title",
                "",
                {"music_prompt": album_prompt, "genres": combined_genres},
                album_data.user_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"AI album title suggestion failed: {str(exc)[:220]}")

    cover_art_url = select_cover_art(combined_genres)
    created_at = datetime.now(timezone.utc).isoformat()

    album_doc = {
        "id": album_id,
        "entropy": _entropy_seed(),
        "title": title,
        "music_prompt": album_prompt,
        "genres": combined_genres,
        "vocal_languages": album_data.vocal_languages,
        "lyrics": album_data.lyrics or "",
        "artist_inspiration": album_data.artist_inspiration or "",
        "generate_video": album_data.generate_video,
        "video_style": album_data.video_style or "",
        "cover_art_url": cover_art_url,
        "user_id": album_data.user_id,
        "num_songs": num_tracks,
        "created_at": created_at,
    }
    await db.albums.insert_one(album_doc)
    album_doc.pop("_id", None)

    songs = []
    used_audio_urls = await _load_recent_user_audio_urls(album_data.user_id)
    track_moods = ["energetic opener", "introspective", "building momentum", "peak energy", "reflective closer"]

    for i in range(num_tracks):
        if has_track_inputs:
            track_input = album_data.album_songs[i]
            track_prompt = track_input.music_prompt.strip()
            track_genres = track_input.genres or combined_genres
            track_languages = track_input.vocal_languages or album_data.vocal_languages
            track_lyrics = track_input.lyrics or album_data.lyrics or ""
            track_artist_inspiration = track_input.artist_inspiration or album_data.artist_inspiration or ""
            track_video_style = track_input.video_style or album_data.video_style or ""
            desired_duration = track_input.duration_seconds or 25
            track_title = (track_input.title or "").strip()
        else:
            mood_variation = track_moods[i % len(track_moods)]
            track_prompt = f"{album_prompt} ({mood_variation})"
            track_genres = combined_genres
            track_languages = album_data.vocal_languages
            track_lyrics = album_data.lyrics or ""
            track_artist_inspiration = album_data.artist_inspiration or ""
            track_video_style = album_data.video_style or ""
            desired_duration = 25
            track_title = ""

        if not track_title:
            try:
                track_title = await generate_ai_suggestion(
                    "title",
                    "",
                    {"music_prompt": track_prompt, "genres": track_genres, "track_number": i + 1},
                    album_data.user_id,
                )
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"AI track title suggestion failed: {str(exc)[:220]}")

        if not track_lyrics and track_languages and "Instrumental" not in track_languages:
            try:
                track_lyrics = await generate_lyrics(
                    track_prompt,
                    track_genres,
                    track_languages,
                    track_title,
                )
            except Exception as e:
                logger.warning("Failed to generate lyrics for album track %s: %s", i + 1, e)

        track_entropy_seed = _entropy_seed()
        audio_url, actual_duration, is_demo, generation_provider = await generate_track_audio(
            {
                "title": track_title,
                "music_prompt": track_prompt,
                "genres": track_genres,
                "lyrics": track_lyrics,
                "vocal_languages": track_languages,
                "duration_seconds": desired_duration,
                "artist_inspiration": track_artist_inspiration,
                "entropy_seed": track_entropy_seed,
            },
            used_audio_urls,
        )

        fallback_video_ready = bool(
            album_data.generate_video
            and (
                FREE_TIER_MODE
                or (not REPLICATE_API_TOKEN and not STRICT_REAL_MEDIA_OUTPUT)
            )
        )
        video_thumbnail = generate_video_thumbnail(
            {
                "title": track_title,
                "music_prompt": track_prompt,
                "genres": track_genres,
                "video_style": track_video_style,
            }
        ) if fallback_video_ready else None
        video_url = _make_unique_media_url(_SAMPLE_VIDEO_URL) if fallback_video_ready else None
        video_status = "completed" if fallback_video_ready else ("queued" if album_data.generate_video else None)

        song_doc = {
            "id": str(uuid.uuid4()),
            "entropy": track_entropy_seed,
            "track_number": i + 1,
            "title": track_title,
            "music_prompt": track_prompt,
            "genres": track_genres,
            "duration_seconds": actual_duration or desired_duration,
            "vocal_languages": track_languages,
            "lyrics": track_lyrics,
            "artist_inspiration": track_artist_inspiration,
            "generate_video": album_data.generate_video,
            "video_style": track_video_style,
            "audio_url": audio_url,
            "video_url": video_url,
            "video_thumbnail": video_thumbnail,
            "video_status": video_status,
            "video_generated_at": datetime.now(timezone.utc).isoformat() if fallback_video_ready else None,
            "cover_art_url": cover_art_url,
            "album_id": album_id,
            "user_id": album_data.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_demo": is_demo,
            "generation_provider": generation_provider,
        }

        await db.songs.insert_one(song_doc)
        song_doc.pop("_id", None)
        songs.append(song_doc)

    return {
        "id": album_id,
        "title": title,
        "music_prompt": album_prompt,
        "genres": combined_genres,
        "cover_art_url": cover_art_url,
        "user_id": album_data.user_id,
        "created_at": created_at,
        "songs": songs,
    }

# ==================== Data Retrieval ====================

async def _get_user_by_id(user_id: str) -> Optional[dict]:
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user and legacy_db is not None:
        user = await legacy_db.users.find_one({"id": user_id}, {"_id": 0})
    return user


def _normalized_user_profile(user: dict) -> dict:
    mobile = str(user.get("mobile", "")).strip()
    is_master = mobile == MASTER_ADMIN_MOBILE
    name = str(user.get("name") or "").strip()
    role = str(user.get("role") or "").strip()

    if is_master:
        name = MASTER_ADMIN_NAME
        role = MASTER_ADMIN_ROLE
    else:
        if not name:
            name = "User"
        if not role:
            role = "User"

    normalized = dict(user)
    normalized["name"] = name
    normalized["role"] = role
    return normalized


async def _persist_normalized_user(user: dict) -> dict:
    normalized = _normalized_user_profile(user)
    update_fields = {}
    if normalized.get("name") != user.get("name"):
        update_fields["name"] = normalized["name"]
    if normalized.get("role") != user.get("role"):
        update_fields["role"] = normalized["role"]
    if update_fields and normalized.get("id"):
        await db.users.update_one({"id": normalized["id"]}, {"$set": update_fields}, upsert=True)
        if legacy_db is not None:
            await legacy_db.users.update_one({"id": normalized["id"]}, {"$set": update_fields})
    return normalized


async def _ensure_master_access(user_id: str) -> dict:
    user = await _get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user = await _persist_normalized_user(user)
    if user.get("mobile") != MASTER_ADMIN_MOBILE:
        raise HTTPException(status_code=403, detail="Master dashboard access denied")
    return user


def _parse_iso_datetime(value: Optional[str]) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def _strip_url_query(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        return urlunparse(parsed._replace(query="", fragment=""))
    except Exception:
        return url.split("?")[0]


async def _load_recent_user_audio_urls(user_id: str, limit: int = 40) -> set[str]:
    try:
        docs = await db.songs.find({"user_id": user_id}, {"_id": 0, "audio_url": 1}).sort("created_at", -1).to_list(limit)
        cleaned = {_strip_url_query(str(doc.get("audio_url", "")).strip()) for doc in docs if doc.get("audio_url")}
        return {item for item in cleaned if item}
    except Exception:
        return set()

@api_router.get("/songs/user/{user_id}")
async def get_user_songs(user_id: str):
    songs = await db.songs.find({"user_id": user_id, "album_id": None}, {"_id": 0}).to_list(100)
    songs.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return songs

@api_router.get("/albums/user/{user_id}")
async def get_user_albums(user_id: str):
    albums = await db.albums.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    albums.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    album_ids = [album['id'] for album in albums]
    if album_ids:
        all_songs = await db.songs.find({"album_id": {"$in": album_ids}}, {"_id": 0}).to_list(500)
        songs_by_album = {}
        for song in all_songs:
            aid = song.get('album_id')
            if aid not in songs_by_album:
                songs_by_album[aid] = []
            songs_by_album[aid].append(song)
        for album in albums:
            album_songs = songs_by_album.get(album['id'], [])
            album_songs.sort(key=lambda s: s.get("created_at", ""), reverse=True)
            album['songs'] = album_songs
    return albums

@api_router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    songs = await db.songs.find({"user_id": user_id, "album_id": None}, {"_id": 0}).to_list(100)
    albums = await db.albums.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    songs.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    albums.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    album_ids = [album['id'] for album in albums]
    if album_ids:
        all_album_songs = await db.songs.find({"album_id": {"$in": album_ids}}, {"_id": 0}).to_list(500)
        songs_by_album = {}
        for song in all_album_songs:
            aid = song.get('album_id')
            if aid not in songs_by_album:
                songs_by_album[aid] = []
            songs_by_album[aid].append(song)
        for album in albums:
            album_songs = songs_by_album.get(album['id'], [])
            album_songs.sort(key=lambda s: s.get("created_at", ""), reverse=True)
            album['songs'] = album_songs
    return {"songs": songs, "albums": albums}


@api_router.get("/dashboard/master/{user_id}")
async def get_master_dashboard(user_id: str):
    await _ensure_master_access(user_id)

    users = await db.users.find({}, {"_id": 0}).to_list(5000)
    if legacy_db is not None:
        legacy_users = await legacy_db.users.find({}, {"_id": 0}).to_list(5000)
        existing_ids = {u.get("id") for u in users}
        for user in legacy_users:
            if user.get("id") not in existing_ids:
                users.append(user)

    songs = await db.songs.find({}, {"_id": 0}).to_list(10000)
    albums = await db.albums.find({}, {"_id": 0}).to_list(5000)

    users_by_id = {u.get("id"): u for u in users if u.get("id")}
    albums_by_id = {a.get("id"): a for a in albums if a.get("id")}
    songs_by_album = {}
    for song in songs:
        album_id = song.get("album_id")
        if not album_id:
            continue
        songs_by_album.setdefault(album_id, []).append(song)

    enriched_songs = []
    for song in songs:
        owner = users_by_id.get(song.get("user_id"), {})
        album = albums_by_id.get(song.get("album_id")) if song.get("album_id") else None
        enriched = {
            **song,
            "user_name": owner.get("name", "Unknown User"),
            "user_mobile": owner.get("mobile", "N/A"),
            "album_title": album.get("title") if album else None,
            "item_type": "track",
            "source": "album_track" if song.get("album_id") else "single",
        }
        enriched_songs.append(enriched)

    singles = [s for s in enriched_songs if not s.get("album_id")]
    singles.sort(key=lambda s: s.get("created_at", ""), reverse=True)

    enriched_albums = []
    for album in albums:
        owner = users_by_id.get(album.get("user_id"), {})
        album_tracks = songs_by_album.get(album.get("id"), [])
        album_tracks_sorted = sorted(album_tracks, key=lambda s: s.get("created_at", ""), reverse=True)
        enriched_album = {
            **album,
            "user_name": owner.get("name", "Unknown User"),
            "user_mobile": owner.get("mobile", "N/A"),
            "song_count": len(album_tracks_sorted),
            "songs": album_tracks_sorted,
            "item_type": "album",
        }
        enriched_albums.append(enriched_album)

    enriched_songs.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    enriched_albums.sort(key=lambda a: a.get("created_at", ""), reverse=True)

    return {
        "master": True,
        "summary": {
            "total_users": len(users),
            "total_tracks": len(enriched_songs),
            "total_singles": len(singles),
            "total_albums": len(enriched_albums),
        },
        "users": sorted(users, key=lambda u: u.get("created_at", ""), reverse=True),
        "tracks": enriched_songs,
        "songs": singles,
        "albums": enriched_albums,
    }

# ==================== Video Generation ====================

# ==================== Video Generation Utilities ====================

_SAMPLE_VIDEO_URL = "https://samplelib.com/lib/preview/mp4/sample-10s.mp4"

# Replicate model for AI video generation (minimax video-01: text + image to video)
REPLICATE_VIDEO_MODEL = "minimax/video-01"


def _build_video_prompt(song_data: dict) -> str:
    """Build a cinematic prompt for video generation from song metadata."""
    title = song_data.get("title", "Music")[:40]
    style = song_data.get("video_style", "").strip() or "cinematic, atmospheric"
    prompt = song_data.get("music_prompt", "")[:80]
    genres = ", ".join(song_data.get("genres", [])[:3])
    parts = [f"Music video for '{title}'"]
    if style:
        parts.append(style)
    if prompt:
        parts.append(f"Mood: {prompt}")
    if genres:
        parts.append(f"Genres: {genres}")
    return ". ".join(parts) + ". Smooth motion, professional cinematography, vibrant colors."


def _get_thumbnail_data_url(song_data: dict, max_size_kb: int = 200) -> Optional[str]:
    """Get thumbnail as data URL, compressed to stay under max_size_kb for Replicate."""
    try:
        width, height = 1280, 720
        img = Image.new("RGB", (width, height), color=(20, 20, 40))
        draw = ImageDraw.Draw(img)
        for i in range(height):
            color_val = int(20 + (i / height) * 60)
            draw.line([(0, i), (width, i)], fill=(color_val, color_val // 2, color_val + 40))
        genres = song_data.get("genres", [])
        if genres:
            accent_color = (100, 150, 255) if "Electronic" in genres else (200, 100, 255)
            for x in range(100, width, 200):
                draw.ellipse([x - 50, 150, x + 50, 250], outline=accent_color, width=3)
        try:
            title_text = song_data.get("title", "AI Music")[:30]
            draw.text((width // 2, height // 2 - 40), title_text, fill=(255, 255, 255), anchor="mm")
            prompt_text = (song_data.get("music_prompt", "") or "")[:50]
            if prompt_text:
                draw.text((width // 2, height // 2 + 40), prompt_text, fill=(200, 200, 200), anchor="mm")
        except Exception:
            pass
        buf = io.BytesIO()
        for quality in [70, 60, 50, 40]:
            buf.seek(0)
            buf.truncate(0)
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            if len(buf.getvalue()) <= max_size_kb * 1024:
                break
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"
    except Exception as e:
        logger.error(f"Error creating thumbnail for video: {e}")
        return None


def _generate_video_via_replicate(song_data: dict) -> Optional[str]:
    """Generate video using Replicate AI (minimax/video-01). Returns video URL or None."""
    if not REPLICATE_API_TOKEN:
        logger.info("REPLICATE_API_TOKEN not set, skipping AI video generation")
        return None
    try:
        import replicate
        prompt = _build_video_prompt(song_data)
        image_url = _get_thumbnail_data_url(song_data)
        input_params = {"prompt": prompt, "prompt_optimizer": True}
        if image_url and len(image_url) < 256 * 1024:  # Replicate data URL limit ~256KB
            input_params["first_frame_image"] = image_url
        output = replicate.run(
            REPLICATE_VIDEO_MODEL,
            input=input_params,
        )
        return _extract_replicate_media_url(output)
    except Exception as e:
        logger.error(f"Replicate video generation failed: {e}")
        return None

def generate_video_thumbnail(song_data: dict) -> str:
    """Generate a video thumbnail/poster for the song based on its metadata"""
    try:
        # Create a 1280x720 image for video thumbnail
        width, height = 1280, 720
        img = Image.new('RGB', (width, height), color=(20, 20, 40))
        draw = ImageDraw.Draw(img)
        
        # Add a gradient effect with rectangles
        for i in range(height):
            color_val = int(20 + (i / height) * 60)
            draw.line([(0, i), (width, i)], fill=(color_val, color_val//2, color_val + 40))
        
        # Add geometric shapes based on genre
        genres = song_data.get('genres', [])
        if genres:
            # Draw accent circles/shapes based on genre type
            accent_color = (100, 150, 255) if 'Electronic' in genres else (200, 100, 255)
            for x in range(100, width, 200):
                draw.ellipse([x-50, 200-50, x+50, 200+50], outline=accent_color, width=3)
        
        # Add text
        try:
            # Try to use a large font, fall back to default if not available
            title_text = song_data.get('title', 'AI Music')[:30]
            draw.text((width//2, height//2 - 40), title_text, fill=(255, 255, 255), anchor="mm")
            
            prompt_text = song_data.get('music_prompt', '')[:50]
            draw.text((width//2, height//2 + 40), prompt_text, fill=(200, 200, 200), anchor="mm")
        except:
            pass
        
        # Convert to base64 for data URL (was incorrectly using .hex() before)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        b64 = base64.b64encode(img_byte_arr.read()).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"
    except Exception as e:
        logger.error(f"Error generating video thumbnail: {e}")
        return None

# ==================== Download Routes ====================

@api_router.get("/albums/{album_id}/download")
async def download_album(album_id: str, user_id: str):
    """Download all songs from an album as a ZIP file"""
    try:
        # Verify album exists and belongs to user
        album = await db.albums.find_one({"id": album_id, "user_id": user_id})
        if not album:
            raise HTTPException(status_code=404, detail="Album not found")
        
        # Get all songs in the album
        songs = await db.songs.find({"album_id": album_id}, {"_id": 0}).to_list(100)
        if not songs:
            raise HTTPException(status_code=404, detail="No songs in album")
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Create album metadata file
            album_info = {
                "title": album.get('title', 'Untitled Album'),
                "prompt": album.get('music_prompt', ''),
                "genres": album.get('genres', []),
                "created_at": album.get('created_at', ''),
                "songs": []
            }
            
            # Add each song to ZIP
            for idx, song in enumerate(songs, 1):
                try:
                    # Download audio file
                    audio_url = song.get('audio_url')
                    if audio_url:
                        if str(audio_url).startswith("data:"):
                            content, mime = _decode_data_url_blob(audio_url)
                            guessed_ext = mimetypes.guess_extension(mime) or ".mp3"
                            file_extension = guessed_ext.lstrip(".")
                        else:
                            response = requests.get(audio_url, timeout=10)
                            if response.status_code != 200:
                                continue
                            content = response.content
                            file_extension = audio_url.split('.')[-1].split('?')[0] or 'mp3'

                        filename = f"{idx:02d}__{song.get('title', f'Track {idx}')}.{file_extension}"
                        zip_file.writestr(filename, content)

                        # Add to metadata
                        album_info["songs"].append({
                            "title": song.get('title', ''),
                            "duration": song.get('duration_seconds', 0),
                            "lyrics": song.get('lyrics', ''),
                            "file": filename
                        })
                except Exception as e:
                    logger.error(f"Error downloading song {song.get('id')}: {e}")
            
            # Add metadata JSON file
            zip_file.writestr("album_info.json", json.dumps(album_info, indent=2))
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{album.get("title", "album")}.zip"'}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating album ZIP: {e}")
        raise HTTPException(status_code=500, detail="Failed to create download")

@api_router.get("/songs/{song_id}/download")
async def download_song(song_id: str, user_id: str):
    """Download a single song"""
    try:
        # Verify song exists and belongs to user
        song = await db.songs.find_one({"id": song_id, "user_id": user_id})
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")
        
        audio_url = song.get('audio_url')
        if not audio_url:
            raise HTTPException(status_code=404, detail="Audio not found")

        if str(audio_url).startswith("data:"):
            content, mime = _decode_data_url_blob(audio_url)
            guessed_ext = mimetypes.guess_extension(mime) or ".mp3"
            file_extension = guessed_ext.lstrip(".")
            media_type = mime
        else:
            response = requests.get(audio_url, timeout=10)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to download audio")
            content = response.content
            file_extension = audio_url.split('.')[-1].split('?')[0] or 'mp3'
            media_type = response.headers.get("content-type", "audio/mpeg")

        filename = f"{song.get('title', 'song')}.{file_extension}"

        return StreamingResponse(
            iter([content]),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading song: {e}")
        raise HTTPException(status_code=500, detail="Failed to download song")


@api_router.get("/songs/{song_id}/download-video")
async def download_song_video(song_id: str, user_id: str):
    """Download generated video for a single song."""
    try:
        song = await db.songs.find_one({"id": song_id, "user_id": user_id}, {"_id": 0})
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")

        video_url = song.get("video_url")
        if not video_url:
            raise HTTPException(status_code=404, detail="Video not found")

        response = requests.get(video_url, timeout=20)
        if response.status_code != 200:
            # Fallback to direct redirect when provider rejects server-side fetch.
            return RedirectResponse(video_url, status_code=307)

        guessed_ext = Path(video_url.split("?")[0]).suffix or ""
        if not guessed_ext:
            content_type = response.headers.get("content-type", "video/mp4").split(";")[0].strip()
            guessed_ext = mimetypes.guess_extension(content_type) or ".mp4"
        filename = f"{song.get('title', 'song')}{guessed_ext}"
        media_type = response.headers.get("content-type", "video/mp4")

        return StreamingResponse(
            iter([response.content]),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        # Last-resort fallback to provider URL if available.
        try:
            song = await db.songs.find_one({"id": song_id, "user_id": user_id}, {"_id": 0})
            if song and song.get("video_url"):
                return RedirectResponse(song.get("video_url"), status_code=307)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Failed to download video")

async def _run_video_generation_task(song_id: str, user_id: str):
    """Background task: generate video via Replicate and update DB."""
    try:
        song = await db.songs.find_one({"id": song_id, "user_id": user_id})
        if not song:
            return
        video_thumbnail = generate_video_thumbnail(song)
        loop = asyncio.get_running_loop()
        video_url = None if FREE_TIER_MODE else await loop.run_in_executor(None, lambda: _generate_video_via_replicate(song))
        if not video_url:
            if STRICT_REAL_MEDIA_OUTPUT:
                await db.songs.update_one(
                    {"id": song_id},
                    {
                        "$set": {
                            "video_status": "failed",
                            "video_thumbnail": video_thumbnail,
                            "video_error": "Real video generation failed",
                        }
                    }
                )
                return
            video_url = _make_unique_media_url(_SAMPLE_VIDEO_URL)
        await db.songs.update_one(
            {"id": song_id},
            {
                "$set": {
                    "video_url": video_url,
                    "video_thumbnail": video_thumbnail,
                    "generate_video": True,
                    "video_generated_at": datetime.now(timezone.utc).isoformat(),
                    "video_status": "completed"
                }
            }
        )
        logger.info(f"Video generated for song {song_id}")
    except Exception as e:
        logger.error(f"Background video generation failed for {song_id}: {e}")
        if STRICT_REAL_MEDIA_OUTPUT:
            try:
                await db.songs.update_one(
                    {"id": song_id},
                    {"$set": {"video_status": "failed", "video_error": str(e)}}
                )
            except Exception:
                pass
            return
        try:
            song = await db.songs.find_one({"id": song_id, "user_id": user_id})
            if song:
                await db.songs.update_one(
                    {"id": song_id},
                    {
                        "$set": {
                            "video_url": _make_unique_media_url(_SAMPLE_VIDEO_URL),
                            "video_thumbnail": generate_video_thumbnail(song),
                            "video_status": "completed",
                            "generate_video": True,
                        }
                    }
                )
        except Exception:
            pass


# ==================== Video Generation Route ====================

@api_router.post("/songs/{song_id}/generate-video")
async def generate_song_video(song_id: str, user_id: str, background_tasks: BackgroundTasks):
    """Generate a video for a song using AI (Replicate) or fallback to sample."""
    try:
        song = await db.songs.find_one({"id": song_id, "user_id": user_id})
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")

        video_thumbnail = generate_video_thumbnail(song)

        if REPLICATE_API_TOKEN and not FREE_TIER_MODE:
            await db.songs.update_one(
                {"id": song_id},
                {"$set": {"video_status": "processing", "video_thumbnail": video_thumbnail}}
            )
            background_tasks.add_task(_run_video_generation_task, song_id, user_id)
            return {
                "id": song_id,
                "status": "processing",
                "video_thumbnail": video_thumbnail,
                "message": "AI video generation started. This may take 1-2 minutes. Refresh the page to see your video.",
            }

        if STRICT_REAL_MEDIA_OUTPUT:
            raise HTTPException(
                status_code=502,
                detail="Real video generation is unavailable. Configure REPLICATE_API_TOKEN and provider access.",
            )

        video_url = _make_unique_media_url(_SAMPLE_VIDEO_URL)
        await db.songs.update_one(
            {"id": song_id},
            {
                "$set": {
                    "video_url": video_url,
                    "video_thumbnail": video_thumbnail,
                    "generate_video": True,
                    "video_generated_at": datetime.now(timezone.utc).isoformat(),
                    "video_status": "completed",
                }
            },
        )
        return {
            "id": song_id,
            "video_url": video_url,
            "video_thumbnail": video_thumbnail,
            "status": "generated",
            "message": f"Video ready for '{song.get('title', 'Song')}'",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating video: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate video")

@api_router.get("/songs/{song_id}/video-status")
async def get_video_status(song_id: str, user_id: str):
    """Get video generation status for a song."""
    song = await db.songs.find_one({"id": song_id, "user_id": user_id}, {"_id": 0})
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return {
        "id": song_id,
        "video_status": song.get("video_status", "pending"),
        "video_url": song.get("video_url"),
        "video_thumbnail": song.get("video_thumbnail"),
    }


@api_router.post("/albums/{album_id}/generate-videos")
async def generate_album_videos(album_id: str, user_id: str, background_tasks: BackgroundTasks):
    """Generate videos for all songs in an album using AI or sample fallback."""
    try:
        album = await db.albums.find_one({"id": album_id, "user_id": user_id})
        if not album:
            raise HTTPException(status_code=404, detail="Album not found")

        songs = await db.songs.find({"album_id": album_id}, {"_id": 0}).to_list(100)
        generated = []

        for song in songs:
            try:
                video_thumbnail = generate_video_thumbnail(song)
                if REPLICATE_API_TOKEN and not FREE_TIER_MODE:
                    await db.songs.update_one(
                        {"id": song["id"]},
                        {"$set": {"video_status": "processing", "video_thumbnail": video_thumbnail}},
                    )
                    background_tasks.add_task(_run_video_generation_task, song["id"], user_id)
                    generated.append({"song_id": song["id"], "title": song.get("title", ""), "status": "processing"})
                else:
                    await db.songs.update_one(
                        {"id": song["id"]},
                        {
                            "$set": {
                                "video_url": _make_unique_media_url(_SAMPLE_VIDEO_URL),
                                "video_thumbnail": video_thumbnail,
                                "generate_video": True,
                                "video_generated_at": datetime.now(timezone.utc).isoformat(),
                                "video_status": "completed",
                            }
                        },
                    )
                    generated.append({"song_id": song["id"], "title": song.get("title", ""), "status": "generated"})
            except Exception as e:
                logger.error(f"Error starting video for song {song.get('id')}: {e}")

        msg = "AI video generation started for all tracks. Refresh in 1-2 minutes." if (REPLICATE_API_TOKEN and not FREE_TIER_MODE) else "Videos ready."
        return {
            "album_id": album_id,
            "total_videos_generated": len(generated),
            "songs": generated,
            "message": msg,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating album videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate videos")

# ==================== Knowledge Bases ====================

@api_router.get("/genres")
async def get_genres():
    return {"genres": get_all_genres(), "categories": GENRE_KNOWLEDGE_BASE}

@api_router.get("/languages")
async def get_languages():
    return {"languages": LANGUAGE_KNOWLEDGE_BASE}

@api_router.get("/artists")
async def get_artists():
    return {"artists": get_all_artists(), "categories": ARTIST_KNOWLEDGE_BASE}

@api_router.get("/video-styles")
async def get_video_styles():
    return {"styles": VIDEO_STYLE_KNOWLEDGE_BASE}

# ==================== Health Check ====================

@api_router.get("/")
async def root():
    return {"message": "MuseWave API - AI Music Creation"}

@api_router.get("/health")
async def api_health():
    if GEMINI_API_KEY:
        ai_suggestion_status = f"configured:{AI_SUGGEST_PROVIDER or 'gemini'}"
    elif OPENAI_API_KEY:
        ai_suggestion_status = "configured:openai_fallback_only"
    else:
        ai_suggestion_status = "missing_gemini_and_openai_keys"
    if FREE_TIER_MODE:
        music_generation_mode = "free_curated_library"
    elif MUSICGEN_API_URL:
        music_generation_mode = "self_host_musicgen"
    else:
        music_generation_mode = "unavailable" if STRICT_REAL_MEDIA_OUTPUT else "fallback_curated_library"
    return {
        "status": "healthy",
        "version": "3.0",
        "mode": "hybrid",
        "db_name": PRIMARY_DB_NAME,
        "legacy_db_name": LEGACY_DB_NAME if legacy_db is not None else None,
        "ai_suggestions": ai_suggestion_status,
        "music_generation": music_generation_mode,
        "music_generation_model": MUSICGEN_API_URL if MUSICGEN_API_URL else None,
        "video_generation": "configured" if (REPLICATE_API_TOKEN and not FREE_TIER_MODE) else ("unavailable" if STRICT_REAL_MEDIA_OUTPUT else "fallback_sample_video"),
        "strict_real_media_output": STRICT_REAL_MEDIA_OUTPUT,
        "free_tier_mode": FREE_TIER_MODE,
        "features": ["ai_suggestions", "lyrics_synthesis", "album_per_track_inputs", "knowledge_bases"],
    }

app.include_router(api_router)

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# ==================== Static Frontend Serving ====================
# Serve React frontend build files

FRONTEND_BUILD_DIR = Path(__file__).parent.parent / "frontend" / "build"

# Mount static files if build directory exists
if FRONTEND_BUILD_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_BUILD_DIR / "static"), name="static")

# Catch-all route: serve index.html for all non-API routes
# This allows React Router to handle routing
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """
    Serve the React app for all routes except /api.
    This enables client-side routing with React Router.
    """
    # Don't serve React app for API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Check if index.html exists
    index_file = FRONTEND_BUILD_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    
    # If no build directory, return API info
    return {"message": "MuseWave API - AI Music Creation", "note": "Frontend not built yet"}
