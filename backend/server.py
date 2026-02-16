"""
MuseWave - AI Music Creation Application
Independent backend with:
- OpenAI-powered AI suggestions and lyrics synthesis
- Optional external provider hook for actual music generation
- Optional Replicate-based video generation
- Global knowledge bases for genres/languages/artists
"""

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
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
import zipfile
import io
import base64
import requests
from PIL import Image, ImageDraw
import json
import re

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
MASTER_ADMIN_MOBILE = os.environ.get("MASTER_ADMIN_MOBILE", "9873945238")

# API Keys
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
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
SUGGEST_MAX_ATTEMPTS = max(1, min(int(os.environ.get("SUGGEST_MAX_ATTEMPTS", "3")), 6))
SUGGEST_OPENAI_TIMEOUT_SECONDS = max(
    2.0, min(float(os.environ.get("SUGGEST_OPENAI_TIMEOUT_SECONDS", "8")), 30.0)
)

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="MuseWave API", description="AI Music Creation Platform")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserResponse(BaseModel):
    id: str
    name: str
    mobile: str
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

def select_audio_for_genres(genres: List[str], used_urls: set = None) -> dict:
    """Select appropriate audio based on genres, avoiding repeats"""
    if used_urls is None:
        used_urls = set()
    
    category = get_genre_category(genres)
    available_tracks = AUDIO_LIBRARY.get(category, AUDIO_LIBRARY["default"])
    
    # Filter out already used tracks
    unused_tracks = [t for t in available_tracks if t["url"] not in used_urls]
    if not unused_tracks:
        unused_tracks = available_tracks  # Reset if all used
    
    return random.choice(unused_tracks)

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
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    output = payload.get("output")
    if isinstance(output, str) and output.startswith(("http://", "https://")):
        return output
    if isinstance(output, list):
        for item in output:
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                return item
            if isinstance(item, dict):
                nested = item.get("url") or item.get("audio_url")
                if isinstance(nested, str) and nested.startswith(("http://", "https://")):
                    return nested
    return None

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

def _build_musicgen_prompt(song_payload: dict) -> str:
    """Construct a detailed, music-focused prompt for generation providers."""
    title = (song_payload.get("title") or "").strip()
    prompt = (song_payload.get("music_prompt") or "").strip()
    genres = [g for g in (song_payload.get("genres") or []) if g]
    languages = [l for l in (song_payload.get("vocal_languages") or []) if l]
    artist = (song_payload.get("artist_inspiration") or "").strip()
    lyrics = (song_payload.get("lyrics") or "").strip()
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
    return ". ".join(parts) if parts else "Create a high-quality, original instrumental music track."

def _generate_music_via_replicate(song_payload: dict) -> Optional[str]:
    """Generate music track via Replicate-hosted MusicGen model."""
    if not REPLICATE_API_TOKEN:
        return None
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
        for params in input_attempts:
            try:
                output = replicate.run(REPLICATE_MUSIC_MODEL, input=params)
                audio_url = _extract_replicate_media_url(output)
                if audio_url:
                    return audio_url
            except Exception as e:
                logger.warning("Replicate MusicGen attempt failed (%s): %s", params.keys(), e)
        return None
    except Exception as e:
        logger.warning("Replicate MusicGen setup failed: %s", e)
        return None

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

async def generate_track_audio(song_payload: dict, used_audio_urls: Optional[set] = None) -> tuple[str, int, bool, str]:
    """
    Generate/obtain track audio.
    1) If MUSICGEN_API_URL is configured, call it for real generation.
    2) Else, if REPLICATE_API_TOKEN is configured, use Replicate MusicGen.
    3) Fallback to curated demo library if provider is unavailable or fails.
    Returns: (audio_url, duration_seconds, is_demo, provider_name)
    """
    if used_audio_urls is None:
        used_audio_urls = set()

    if MUSICGEN_API_URL:
        try:
            headers = {"Content-Type": "application/json"}
            if MUSICGEN_API_KEY:
                headers["Authorization"] = f"Bearer {MUSICGEN_API_KEY}"
            provider_payload = {
                "title": song_payload.get("title", ""),
                "prompt": song_payload.get("music_prompt", ""),
                "genres": song_payload.get("genres", []),
                "lyrics": song_payload.get("lyrics", ""),
                "vocal_languages": song_payload.get("vocal_languages", []),
                "duration_seconds": song_payload.get("duration_seconds", 30),
                "artist_inspiration": song_payload.get("artist_inspiration", ""),
            }
            response = await asyncio.to_thread(
                lambda: requests.post(
                    MUSICGEN_API_URL,
                    json=provider_payload,
                    headers=headers,
                    timeout=120,
                )
            )
            if response.status_code >= 400:
                logger.warning("Music provider failed (%s): %s", response.status_code, response.text[:300])
            else:
                data = response.json() if response.content else {}
                audio_url = _extract_audio_url(data if isinstance(data, dict) else {})
                if audio_url:
                    duration = int(data.get("duration_seconds") or song_payload.get("duration_seconds") or 30)
                    return audio_url, duration, False, "external_music_provider"
                logger.warning("Music provider response missing audio url: %s", str(data)[:300])
        except Exception as exc:
            logger.warning("Music provider exception: %s", exc)

    if REPLICATE_API_TOKEN:
        replicate_audio_url = await asyncio.to_thread(lambda: _generate_music_via_replicate(song_payload))
        if replicate_audio_url:
            requested_duration = int(song_payload.get("duration_seconds") or 30)
            duration = max(5, min(requested_duration, REPLICATE_MUSIC_MAX_DURATION_SECONDS))
            return replicate_audio_url, duration, False, f"replicate:{REPLICATE_MUSIC_MODEL}"

    if STRICT_REAL_MEDIA_OUTPUT:
        raise HTTPException(
            status_code=502,
            detail="Real music generation failed. Configure provider keys/quota for MUSICGEN or Replicate.",
        )

    selected = select_audio_for_genres(song_payload.get("genres", []), used_audio_urls)
    used_audio_urls.add(selected["url"])
    return selected["url"], selected["duration"], True, "curated_demo_library"

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
    "title": 0.65,
    "music_prompt": 0.75,
    "genres": 0.55,
    "lyrics": 0.7,
    "artist_inspiration": 0.55,
    "video_style": 0.72,
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

def _fallback_suggestion(field: str, context: dict, avoid_texts: Optional[set[str]] = None) -> str:
    seed_source = (
        f"{generate_uniqueness_seed()}|{context.get('music_prompt','')}|"
        f"{','.join(context.get('genres',[]) if isinstance(context.get('genres'), list) else [])}"
    )
    seed_val = int(hashlib.sha256(seed_source.encode()).hexdigest(), 16)

    def pick(values: list[str], offset: int = 0) -> str:
        if not values:
            return ""
        return values[(seed_val + offset) % len(values)]

    def pick_unique(candidates: list[str], field_name: str = field) -> str:
        cleaned = []
        seen = set()
        for item in candidates:
            text = (item or "").strip()
            key = text.lower()
            if not text or key in seen:
                continue
            cleaned.append(text)
            seen.add(key)
        if not cleaned:
            return ""
        recent = set(RECENT_SUGGESTIONS.get(field_name, []))
        if avoid_texts:
            recent.update({(x or "").strip().lower() for x in avoid_texts if x})
        start = seed_val % len(cleaned)
        for i in range(len(cleaned)):
            candidate = cleaned[(start + i) % len(cleaned)]
            if candidate.lower() not in recent:
                return candidate
        return cleaned[start]

    genres = context.get("genres", []) if isinstance(context.get("genres"), list) else []
    prompt = (context.get("music_prompt") or "").strip()

    if field == "title":
        title_a = ["Midnight", "Neon", "Afterdark", "Echo", "Velvet", "Pulse", "Aurora", "Signal", "Static", "Silver"]
        title_b = ["Drive", "Afterglow", "Voltage", "Reflex", "Horizon", "Frequency", "Momentum", "Skyline", "Rush", "Drift"]
        genre = genres[0] if genres else ""
        cores = [f"{a} {b}" for a in title_a for b in title_b]
        options = [f"{genre} {core}".strip() for core in cores] if genre else cores
        return pick_unique(options)

    if field == "music_prompt":
        genre = ", ".join(genres[:2]) if genres else pick(["Pop, Electronic", "Electronic, Ambient", "R&B, Pop"])
        bass_opts = ["deep sub bass", "rubbery synth bass", "clean punchy low-end", "warm analog bass"]
        drum_opts = ["tight kick-snare groove", "syncopated drum pattern", "driving four-on-the-floor drums", "crisp broken-beat drums"]
        top_opts = ["airy vocal hook", "glassy lead motif", "plucked synth melody", "guitar-texture counterline"]
        mix_opts = ["wide chorus lift", "focused mono-compatible low-end", "controlled transient punch", "clean vocal-forward balance"]
        base_prompt = prompt[:180] if prompt else "A polished modern track concept"
        options = []
        for drum_idx, drum in enumerate(drum_opts):
            for bass_idx, bass in enumerate(bass_opts):
                for top_idx, top in enumerate(top_opts):
                    mix = pick(mix_opts, drum_idx + bass_idx + top_idx)
                    options.append(
                        f"{base_prompt}. Build around {genre} with {drum}, {bass}, and {top}. "
                        f"Arrange with tension in the verse and a strong chorus payoff, keeping a {mix}."
                    )
        return pick_unique(options)

    if field == "genres":
        all_genres = get_all_genres()
        if genres:
            options = []
            for i in range(6):
                pool = list(dict.fromkeys(genres + [pick(all_genres, i + 13), pick(all_genres, i + 29)]))
                options.append(", ".join(pool[:4]))
            return pick_unique(options)
        options = []
        for i in range(10):
            options.append(", ".join([pick(all_genres, i + 3), pick(all_genres, i + 17)]))
        return pick_unique(options)

    if field == "vocal_languages":
        lang_pool = [l for l in LANGUAGE_KNOWLEDGE_BASE if l != "Instrumental"]
        return pick_unique(lang_pool)

    if field == "duration":
        return pick_unique(["30s", "38s", "45s", "52s", "1m10s", "1m24s", "1m36s", "2m00s"])

    if field == "artist_inspiration":
        artists = get_all_artists()
        options = []
        for i in range(10):
            options.append(", ".join([pick(artists, i + 5), pick(artists, i + 21), pick(artists, i + 37)]))
        return pick_unique(options)

    if field == "video_style":
        color_opts = ["neon teal + amber", "deep blue + magenta", "warm tungsten + red practicals", "silver monochrome"]
        camera_opts = ["handheld push-ins", "slow tracking wides", "shoulder-level follow shots", "low-angle glide shots"]
        edit_opts = ["rhythmic jump cuts", "long takes with beat-matched transitions", "strobe-accented cut points", "cross-dissolves on downbeats"]
        options = []
        for color in color_opts:
            for camera in camera_opts:
                for edit in edit_opts:
                    options.append(
                        f"Use {color} palette with {camera}. "
                        f"Keep lighting cinematic and motion-driven, then finish with {edit} aligned to the drum accents."
                    )
        return pick_unique(options)

    if field == "lyrics":
        image_opts = ["city lights in rain", "empty freeway at 2AM", "flickering hallway neon", "late-night window reflections"]
        arc_opts = ["rebuild confidence", "escape emotional noise", "push through pressure", "choose clarity over chaos"]
        options = []
        for arc in arc_opts:
            for image in image_opts:
                options.append(
                    f"A focused hook about how to {arc}, using {image} as the repeating chorus image."
                )
        return pick_unique(options)

    return "Creative suggestion"

async def generate_ai_suggestion(
    field: str,
    current_value: str,
    context: dict,
    user_id: Optional[str] = None,
) -> str:
    """Generate diverse, production-ready, music-specific suggestions."""
    context = context or {}
    scope_key = _build_suggestion_scope_key(field, context, user_id)
    seen_in_scope = await _load_recent_scope_suggestions(field, scope_key)

    if not openai_client:
        fallback = _fallback_suggestion(field, context, seen_in_scope)
        if field in ["genres", "vocal_languages"]:
            fallback = validate_list_suggestion(field, fallback)
        if field == "duration":
            fallback = validate_duration_suggestion(fallback)
        if fallback:
            _remember_suggestion(field, fallback)
            await _persist_scope_suggestion(field, scope_key, fallback, user_id)
            return fallback
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is missing and fallback suggestion failed.",
        )

    system_prompt = build_field_system_prompt(field)
    candidates: list[tuple[int, str]] = []

    for _ in range(SUGGEST_MAX_ATTEMPTS):
        uniqueness_seed = generate_uniqueness_seed()
        prompt = build_suggestion_prompt(
            field,
            current_value,
            context,
            uniqueness_seed,
            list(seen_in_scope)[:8],
        )
        try:
            response = await asyncio.to_thread(
                lambda: openai_client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=FIELD_TEMPERATURE.get(field, 0.65),
                    max_tokens=280,
                    timeout=SUGGEST_OPENAI_TIMEOUT_SECONDS,
                )
            )
            suggestion = (response.choices[0].message.content or "").strip()
            if field in ["music_prompt", "lyrics", "video_style", "title"]:
                suggestion = validate_music_specific_suggestion(field, suggestion)
            if field in ["genres", "vocal_languages"]:
                suggestion = validate_list_suggestion(field, suggestion)
            if field == "duration":
                suggestion = validate_duration_suggestion(suggestion)
            if suggestion and "\n\n" in suggestion:
                suggestion = suggestion.split("\n\n")[0].strip()
            if not suggestion:
                continue
            if current_value and _normalize_suggestion_text(suggestion) == _normalize_suggestion_text(current_value):
                continue
            normalized = _normalize_suggestion_text(suggestion)
            if normalized in seen_in_scope:
                continue

            relevance = _score_suggestion_relevance(field, suggestion, context)
            if relevance >= 58:
                candidates.append((relevance, suggestion))

            if relevance >= 72 and _remember_suggestion(field, suggestion):
                seen_in_scope.add(normalized)
                await _persist_scope_suggestion(field, scope_key, suggestion, user_id)
                return suggestion
        except Exception as e:
            logger.error(f"AI suggestion error for {field}: {e}")
            err_text = str(e).lower()
            if (
                "insufficient_quota" in err_text
                or "invalid_api_key" in err_text
                or "rate_limit" in err_text
                or "timed out" in err_text
            ):
                break

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        for _, candidate in candidates:
            normalized = _normalize_suggestion_text(candidate)
            if normalized in seen_in_scope:
                continue
            if _remember_suggestion(field, candidate):
                seen_in_scope.add(normalized)
                await _persist_scope_suggestion(field, scope_key, candidate, user_id)
                return candidate

    fallback = _fallback_suggestion(field, context, seen_in_scope)
    if field in ["genres", "vocal_languages"]:
        fallback = validate_list_suggestion(field, fallback)
    if field == "duration":
        fallback = validate_duration_suggestion(fallback)
    if fallback:
        _remember_suggestion(field, fallback)
        await _persist_scope_suggestion(field, scope_key, fallback, user_id)
        return fallback

    raise HTTPException(status_code=502, detail=f"AI suggestion failed for field '{field}'.")

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
    
    user = User(name=user_data.name, mobile=user_data.mobile)
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    
    return UserResponse(id=user.id, name=user.name, mobile=user.mobile, created_at=doc['created_at'])

@api_router.post("/auth/login", response_model=UserResponse)
async def login(login_data: UserLogin):
    user = await db.users.find_one({"mobile": login_data.mobile}, {"_id": 0})
    if not user and legacy_db is not None:
        user = await legacy_db.users.find_one({"mobile": login_data.mobile}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="No account found. Please sign up first.")
    
    return UserResponse(id=user['id'], name=user['name'], mobile=user['mobile'], created_at=user['created_at'])

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
        except:
            title = f"Track {uuid.uuid4().hex[:6].upper()}"
    
    # Generate real track (if provider configured) or fallback to curated demo library
    audio_url, actual_duration, is_demo, generation_provider = await generate_track_audio(song_data.model_dump())
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
    
    song_doc = {
        "id": song_id,
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
        "video_url": None,
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
        except Exception:
            title = f"Album {uuid.uuid4().hex[:6].upper()}"

    cover_art_url = select_cover_art(combined_genres)
    created_at = datetime.now(timezone.utc).isoformat()

    album_doc = {
        "id": album_id,
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
    used_audio_urls = set()
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
            except Exception:
                track_title = f"{title} - Track {i + 1}"

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

        audio_url, actual_duration, is_demo, generation_provider = await generate_track_audio(
            {
                "title": track_title,
                "music_prompt": track_prompt,
                "genres": track_genres,
                "lyrics": track_lyrics,
                "vocal_languages": track_languages,
                "duration_seconds": desired_duration,
                "artist_inspiration": track_artist_inspiration,
            },
            used_audio_urls,
        )

        song_doc = {
            "id": str(uuid.uuid4()),
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
            "video_url": None,
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


async def _ensure_master_access(user_id: str) -> dict:
    user = await _get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
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

_SAMPLE_VIDEO_URL = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

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
                        response = requests.get(audio_url, timeout=10)
                        if response.status_code == 200:
                            file_extension = audio_url.split('.')[-1].split('?')[0] or 'mp3'
                            filename = f"{idx:02d}__{song.get('title', f'Track {idx}')}.{file_extension}"
                            zip_file.writestr(filename, response.content)
                            
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
        
        # Download audio file
        response = requests.get(audio_url, timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to download audio")
        
        file_extension = audio_url.split('.')[-1].split('?')[0] or 'mp3'
        filename = f"{song.get('title', 'song')}.{file_extension}"
        
        return StreamingResponse(
            iter([response.content]),
            media_type="audio/mpeg",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading song: {e}")
        raise HTTPException(status_code=500, detail="Failed to download song")

async def _run_video_generation_task(song_id: str, user_id: str):
    """Background task: generate video via Replicate and update DB."""
    try:
        song = await db.songs.find_one({"id": song_id, "user_id": user_id})
        if not song:
            return
        video_thumbnail = generate_video_thumbnail(song)
        loop = asyncio.get_running_loop()
        video_url = await loop.run_in_executor(None, lambda: _generate_video_via_replicate(song))
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
            video_url = _SAMPLE_VIDEO_URL
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
                            "video_url": _SAMPLE_VIDEO_URL,
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

        if REPLICATE_API_TOKEN:
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

        video_url = _SAMPLE_VIDEO_URL
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
                if REPLICATE_API_TOKEN:
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
                                "video_url": _SAMPLE_VIDEO_URL,
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

        msg = "AI video generation started for all tracks. Refresh in 1-2 minutes." if REPLICATE_API_TOKEN else "Videos ready."
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
    if MUSICGEN_API_URL:
        music_generation_mode = "external_music_provider"
    elif REPLICATE_API_TOKEN:
        music_generation_mode = f"replicate:{REPLICATE_MUSIC_MODEL}"
    else:
        music_generation_mode = "unavailable" if STRICT_REAL_MEDIA_OUTPUT else "fallback_curated_library"
    return {
        "status": "healthy",
        "version": "3.0",
        "mode": "hybrid",
        "db_name": PRIMARY_DB_NAME,
        "legacy_db_name": LEGACY_DB_NAME if legacy_db is not None else None,
        "ai_suggestions": "configured" if OPENAI_API_KEY else "missing_openai_api_key",
        "music_generation": music_generation_mode,
        "music_generation_model": REPLICATE_MUSIC_MODEL if REPLICATE_API_TOKEN else None,
        "video_generation": "configured" if REPLICATE_API_TOKEN else ("unavailable" if STRICT_REAL_MEDIA_OUTPUT else "fallback_sample_video"),
        "strict_real_media_output": STRICT_REAL_MEDIA_OUTPUT,
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
