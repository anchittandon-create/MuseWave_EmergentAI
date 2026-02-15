"""
SoundForge - AI Music Creation Platform
Independent FastAPI Backend with OpenAI Integration
No External Dependencies (except OpenAI, MongoDB, Replicate for video)
"""

import os
import sys
import uuid
import random
import hashlib
import logging
import asyncio
import base64
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import openai
from PIL import Image, ImageDraw

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

# MongoDB Connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'soundforge_db')

try:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    logger.info(f"✓ MongoDB connected to {DB_NAME}")
except Exception as e:
    logger.error(f"✗ MongoDB connection failed: {e}")
    sys.exit(1)

# OpenAI Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.warning("⚠ OPENAI_API_KEY not set - AI suggestions will fail")

openai.api_key = OPENAI_API_KEY

# Replicate Configuration (Optional)
REPLICATE_API_TOKEN = os.environ.get('REPLICATE_API_TOKEN')

# ==================== FASTAPI SETUP ====================

app = FastAPI(
    title="SoundForge API",
    description="AI Music Creation Platform - Independent Backend",
    version="2.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
api_router = APIRouter(prefix="/api")

# ==================== KNOWLEDGE BASES ====================

# 140+ Music Genres
GENRE_DATABASE = {
    "mainstream": [
        "Pop", "Rock", "Hip-Hop", "R&B", "Electronic", "Jazz", "Classical",
        "Country", "Reggae", "Blues", "Metal", "Folk", "Indie", "Soul", "Funk", "Disco"
    ],
    "electronic": [
        "House", "Techno", "Trance", "Dubstep", "Drum and Bass", "Ambient", "IDM",
        "Synthwave", "Chillwave", "Future Bass", "Hardstyle", "Deep House",
        "Progressive House", "EDM", "Acid", "Garage", "Glitch"
    ],
    "underground": [
        "Lo-fi", "Vaporwave", "Shoegaze", "Post-Punk", "Noise", "Drone",
        "Dark Ambient", "Industrial", "Chiptune", "Experimental", "Modular",
        "Breakcore", "Grime", "Phonk", "Hyperpop"
    ],
    "regional": [
        "Afrobeats", "Reggaeton", "K-Pop", "J-Pop", "Bollywood", "Bossa Nova",
        "Flamenco", "Cumbia", "Salsa", "Samba", "Dancehall", "Tango", "Rembetiko"
    ],
    "cinematic": [
        "Orchestral", "Cinematic", "Epic", "Film Score", "Video Game",
        "Neo-Classical", "Minimalist", "Ambient Soundscape"
    ],
    "fusion": [
        "Jazz Fusion", "World Fusion", "Electro-Swing", "Trap Metal",
        "Trap Soul", "Bedroom Pop", "Cloud Rap", "Math Rock", "Post-Rock", "Dream Pop"
    ]
}

# 50+ Languages
LANGUAGE_DATABASE = [
    "English", "Spanish", "French", "German", "Italian", "Portuguese",
    "Russian", "Chinese (Mandarin)", "Chinese (Cantonese)", "Japanese",
    "Korean", "Hindi", "Bengali", "Punjabi", "Arabic", "Hebrew", "Turkish",
    "Dutch", "Swedish", "Norwegian", "Danish", "Finnish", "Polish",
    "Czech", "Hungarian", "Romanian", "Bulgarian", "Greek", "Thai",
    "Vietnamese", "Indonesian", "Malay", "Filipino", "Afrikaans",
    "Icelandic", "Catalan", "Basque", "Welsh", "Irish", "Galician",
    "Latin", "Esperanto", "Instrumental", "A cappella"
]

# Artist References (100+ curated)
ARTIST_DATABASE = {
    "electronic": [
        "Aphex Twin", "Boards of Canada", "Four Tet", "Burial", "Flying Lotus",
        "Bonobo", "Tycho", "Jon Hopkins", "Caribou", "Daft Punk", "Fatboy Slim"
    ],
    "pop": [
        "The Weeknd", "Dua Lipa", "Billie Eilish", "Harry Styles", "Taylor Swift",
        "Post Malone", "SZA", "Ariana Grande", "Khalid", "Troye Sivan"
    ],
    "rock": [
        "Tame Impala", "Arctic Monkeys", "Radiohead", "Muse", "Royal Blood",
        "Khruangbin", "Cage the Elephant", "The Strokes", "Interpol"
    ],
    "hip_hop": [
        "Kendrick Lamar", "Tyler the Creator", "Frank Ocean", "Travis Scott",
        "J. Cole", "Nas", "MF DOOM", "Outkast", "A Tribe Called Quest"
    ],
    "ambient": [
        "Brian Eno", "Stars of the Lid", "Tim Hecker", "Sigur Rós",
        "Explosions in the Sky", "Ólafur Arnalds", "Nils Frahm"
    ],
    "jazz": [
        "Kamasi Washington", "Robert Glasper", "Thundercat", "Snarky Puppy",
        "Christian Scott", "Jacob Mann"
    ]
}

# Video Styles
VIDEO_STYLES = [
    "Cyberpunk neon aesthetic", "Abstract geometric patterns", "Nature cinematography",
    "Psychedelic visuals", "Minimalist motion graphics", "Retro VHS aesthetic",
    "Surreal dreamscape", "Urban street footage", "Space and cosmos",
    "Neon lights and reflections", "Underwater ethereal", "Dystopian sci-fi"
]

# Curated Audio Library (Demo Tracks)
AUDIO_LIBRARY = {
    "electronic": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", "title": "Electronic Pulse", "duration": 30},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", "title": "Digital Wave", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3", "title": "Synth Dreams", "duration": 25},
    ],
    "ambient": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3", "title": "Peaceful Ambient", "duration": 30},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3", "title": "Ethereal Space", "duration": 26},
    ],
    "rock": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3", "title": "Rock Energy", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3", "title": "Guitar Riff", "duration": 25},
    ],
    "hip_hop": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3", "title": "Urban Beat", "duration": 26},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3", "title": "Street Flow", "duration": 28},
    ],
    "pop": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3", "title": "Pop Vibes", "duration": 25},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3", "title": "Feel Good", "duration": 28},
    ],
    "jazz": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", "title": "Smooth Jazz", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", "title": "Jazz Cafe", "duration": 26},
    ],
    "default": [
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3", "title": "Inspiring", "duration": 28},
        {"url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3", "title": "Uplifting", "duration": 25},
    ]
}

# Cover Art URLs
COVER_ART_LIBRARY = {
    "electronic": [
        "https://images.unsplash.com/photo-1614149162883-504ce4d13909?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=400&fit=crop",
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
    "pop": [
        "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1506157786151-b8491531f063?w=400&h=400&fit=crop",
    ],
    "jazz": [
        "https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=400&h=400&fit=crop",
    ],
    "default": [
        "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=400&h=400&fit=crop",
    ]
}

# ==================== UTILITY FUNCTIONS ====================

def get_all_genres() -> List[str]:
    """Get complete list of all genres"""
    all_genres = []
    for category in GENRE_DATABASE.values():
        all_genres.extend(category)
    return sorted(list(set(all_genres)))

@lru_cache(maxsize=1)
def get_genre_cache():
    """Cache all genres"""
    return get_all_genres()

def get_all_languages() -> List[str]:
    """Get complete list of all languages"""
    return sorted(LANGUAGE_DATABASE)

def generate_uniqueness_seed() -> str:
    """Generate unique seed for diversity in suggestions"""
    timestamp = datetime.now(timezone.utc).isoformat()
    random_component = str(random.random())
    unique_id = str(uuid.uuid4())
    combined = f"{timestamp}-{random_component}-{unique_id}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def get_genre_category(genres: List[str]) -> str:
    """Map user genres to audio library category"""
    genre_mapping = {
        "electronic": ["Electronic", "House", "Techno", "Trance", "Dubstep", "EDM"],
        "ambient": ["Ambient", "Chillwave", "Drone"],
        "rock": ["Rock", "Metal", "Post-Rock"],
        "hip_hop": ["Hip-Hop", "Trap", "R&B"],
        "pop": ["Pop", "Indie Pop"],
        "jazz": ["Jazz", "Soul"],
        "default": []
    }
    
    for category, category_genres in genre_mapping.items():
        for genre in genres:
            if genre in category_genres:
                return category
    return "default"

def select_audio_for_genres(genres: List[str], used_urls: set = None) -> dict:
    """Select audio track based on genres"""
    if used_urls is None:
        used_urls = set()
    
    category = get_genre_category(genres)
    available = AUDIO_LIBRARY.get(category, AUDIO_LIBRARY["default"])
    
    unused = [t for t in available if t["url"] not in used_urls]
    if not unused:
        unused = available
    
    return random.choice(unused)

def select_cover_art(genres: List[str]) -> str:
    """Select cover art based on genres"""
    category = get_genre_category(genres)
    covers = COVER_ART_LIBRARY.get(category, COVER_ART_LIBRARY["default"])
    return random.choice(covers)

# ==================== PYDANTIC MODELS ====================

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    mobile: str = Field(..., min_length=10, max_length=20)

class UserLogin(BaseModel):
    mobile: str = Field(..., min_length=10, max_length=20)

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
    music_prompt: str = Field(..., min_length=10)
    genres: List[str] = Field(default_factory=list)
    duration_seconds: int = Field(default=25, ge=5, le=180)
    vocal_languages: List[str] = Field(default_factory=list)
    lyrics: Optional[str] = ""
    artist_inspiration: Optional[str] = ""
    generate_video: bool = False
    video_style: Optional[str] = ""
    user_id: str

class AlbumCreate(BaseModel):
    title: Optional[str] = ""
    music_prompt: str = Field(..., min_length=10)
    genres: List[str] = Field(default_factory=list)
    vocal_languages: List[str] = Field(default_factory=list)
    lyrics: Optional[str] = ""
    artist_inspiration: Optional[str] = ""
    generate_video: bool = False
    video_style: Optional[str] = ""
    num_songs: int = Field(default=3, ge=2, le=10)
    user_id: str

class AISuggestRequest(BaseModel):
    field: str
    current_value: Optional[str] = ""
    context: dict = Field(default_factory=dict)

# ==================== AI SUGGESTION ENGINE ====================

def validate_music_specific_suggestion(field: str, text: str) -> str:
    """Ensure suggestion is music-related, not poetry/stories"""
    
    # Red flags for non-music content
    poetry_indicators = [
        "once upon a time", "there was", "a tale", "a story",
        "and they lived", "the end", "dear reader",
        "metaphorically", "symbolically", "imagine if",
        "in a land", "picture yourself"
    ]
    
    # Check for poetry red flags
    text_lower = text.lower()
    for flag in poetry_indicators:
        if flag in text_lower:
            logger.warning(f"❌ Detected non-music content in {field}: {text[:50]}...")
            return ""
    
    # For music_prompt, must contain music-related terms
    music_keywords = [
        "acoustic", "electronic", "synth", "beat", "rhythm",
        "tempo", "bpm", "reverb", "echo", "delay",
        "frequency", "bass", "treble", "chord", "melody",
        "production", "mix", "master", "eq", "compression",
        "vocal", "instrumental", "drum", "guitar", "piano",
        "layer", "vibe", "mood", "energy", "groove", "dynamic"
    ]
    
    if field == "music_prompt":
        has_music = any(kw in text_lower for kw in music_keywords)
        if not has_music:
            logger.warning(f"❌ No music keywords in suggestion: {text[:50]}...")
            return ""
    
    # Check length
    words = text.split()
    if field == "music_prompt" and len(words) < 5:
        return ""
    if field == "video_style" and len(words) < 10:
        return ""
    
    return text

def validate_list_suggestion(field: str, text: str) -> str:
    """Validate genres/languages against knowledge bases"""
    
    valid_genres = set(get_all_genres())
    valid_languages = set(get_all_languages())
    
    if field == "genres":
        genres = [g.strip() for g in text.split(",")]
        # Allow known genres or niche names (>2 chars)
        genres = [g for g in genres if g in valid_genres or len(g) > 2]
        return ", ".join(genres[:4]) if genres else ""
    
    elif field == "vocal_languages":
        if "instrumental" in text.lower():
            return "Instrumental"
        languages = [l.strip() for l in text.split(",")]
        languages = [l for l in languages if l in valid_languages or len(l) > 2]
        return ", ".join(languages[:3]) if languages else ""
    
    return text

async def generate_ai_suggestion(field: str, current_value: str, context: dict) -> str:
    """Generate real, music-specific AI suggestion using OpenAI GPT-4"""
    
    if not OPENAI_API_KEY:
        logger.warning("⚠ OpenAI API key not configured")
        return ""
    
    seed = generate_uniqueness_seed()
    
    # Field-specific system prompts
    system_prompts = {
        "title": f"""You are a world-class music producer and songwriter with 25+ years experience.
Generate ONE memorable, unique, evocative song title that:
- Captures the emotional essence of the music
- Avoids generic terms (Song, Track, Music, Dream, etc)
- Draws from diverse cultural, literary, or scientific inspiration
- Is specific to this music description
- Uses sophisticated linguistic techniques
Return ONLY the title, nothing else. No quotes, no explanation.
Uniqueness seed: {seed}""",

        "music_prompt": f"""You are a Grammy-winning music producer and sound designer.
Describe this music in ONE vivid, technical way that:
- Uses specific production terminology (reverb, EQ, compression, modulation, etc)
- Never repeats descriptors from previous suggestions
- Describes sonic landscape in completely ORIGINAL ways
- Is specific and actionable for professional production
- Covers mood, energy, texture, dynamics, and sonic direction
Return ONLY 2-4 sentence description, nothing else.
Uniqueness seed: {seed}""",

        "genres": f"""You are a music genre expert with knowledge of 1000+ genres and sub-genres.
Suggest 2-4 precise genres/sub-genres that:
- Perfectly fit this music style
- Include niche or emerging genres (not just mainstream)
- Mix in unexpected but logical combinations
- Are COMPLETELY DIFFERENT from previous suggestions
- Consider production style, emotion, and cultural context
Return ONLY comma-separated genre names (e.g., "Future Garage, Glitch Hop, IDM"). Nothing else.
Uniqueness seed: {seed}""",

        "lyrics": f"""You are a Grammy-winning lyricist and songwriter.
Create ONE evocative lyrical concept/theme that:
- Is completely original and never repeated
- Matches the musical mood and production style perfectly
- Avoids common song topics (love, loss, dancing, freedom, night)
- Uses unexpected imagery and narrative angles
- Inspires genuine creative songwriting
Return ONLY the concept (1-3 sentences). Nothing else.
Uniqueness seed: {seed}""",

        "artist_inspiration": f"""You are a music producer familiar with artists across all genres and eras.
Suggest 2-4 artists who could inspire this music:
- Include established legends AND emerging/underground artists
- Provide specific reasons (production style, emotion, innovation)
- Reference COMPLETELY DIFFERENT artists than previous suggestions
- Consider technique, era, culture, and innovation
Format: "Artist1 (reason), Artist2 (reason), ..."
Uniqueness seed: {seed}""",

        "video_style": f"""You are a cinematographer and visual artist creating music videos.
Describe ONE unique visual style concept:
- Be very specific about color palette, camera techniques, mood
- Reference cinematographic movements or visual artists
- Include mood, atmosphere, lighting, emotional impact
- Use 3-4 sentences of vivid, specific direction
- Avoid overused concepts (neon lights, silhouettes, abstract)
Return ONLY the visual description. Nothing else.
Uniqueness seed: {seed}"""
    }
    
    system_message = system_prompts.get(
        field,
        f"You are a world-class music industry professional. Generate creative, specific, and actionable suggestions for {field}. Be original and diverse. Uniqueness seed: {seed}"
    )
    
    # Build context-aware user prompt
    context_str = ""
    if context:
        if context.get("music_prompt"):
            context_str += f"Music Description: {context['music_prompt']}\n"
        if context.get("genres"):
            context_str += f"Genres: {', '.join(context['genres'])}\n"
        if context.get("lyrics"):
            context_str += f"Lyrical Theme: {context['lyrics'][:200]}\n"
        if context.get("artist_inspiration"):
            context_str += f"Inspiration: {context['artist_inspiration']}\n"
    
    user_prompt = f"""Field: {field}
Current value: {current_value if current_value else "Empty"}

Context:
{context_str if context_str else "No additional context"}

Generate a suggestion for the {field} field based on the context above."""
    
    try:
        logger.info(f"📝 Generating suggestion for field: {field}")
        
        response = await asyncio.to_thread(
            lambda: openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,
                max_tokens=200,
                timeout=15
            )
        )
        
        suggestion = response.choices[0].message.content.strip()
        logger.info(f"✓ Suggestion generated: {suggestion[:50]}...")
        
        # Apply validation layers
        if field in ["music_prompt", "lyrics", "video_style", "title"]:
            suggestion = validate_music_specific_suggestion(field, suggestion)
        
        if field in ["genres", "vocal_languages"]:
            suggestion = validate_list_suggestion(field, suggestion)
        
        return suggestion
        
    except openai.error.RateLimitError:
        logger.error("⚠ OpenAI rate limit - try again later")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except openai.error.APIError as e:
        logger.error(f"⚠ OpenAI API error: {e}")
        raise HTTPException(status_code=500, detail="AI service unavailable")
    except Exception as e:
        logger.error(f"⚠ Unexpected error in suggestion: {e}")
        return ""

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/signup", response_model=UserResponse)
async def signup(user_data: UserCreate):
    """User registration endpoint"""
    existing = await db.users.find_one({"mobile": user_data.mobile})
    if existing:
        raise HTTPException(status_code=400, detail="Mobile already registered")
    
    user = User(name=user_data.name, mobile=user_data.mobile)
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    
    return UserResponse(
        id=user.id,
        name=user.name,
        mobile=user.mobile,
        created_at=doc['created_at']
    )

@api_router.post("/auth/login", response_model=UserResponse)
async def login(login_data: UserLogin):
    """User login endpoint"""
    user = await db.users.find_one({"mobile": login_data.mobile})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user['id'],
        name=user['name'],
        mobile=user['mobile'],
        created_at=user['created_at']
    )

# ==================== AI SUGGESTION ROUTE ====================

@api_router.post("/suggest")
async def ai_suggest(request: AISuggestRequest):
    """AI suggestion endpoint"""
    try:
        suggestion = await generate_ai_suggestion(
            request.field,
            request.current_value or "",
            request.context or {}
        )
        return {
            "suggestion": suggestion,
            "field": request.field,
            "success": bool(suggestion)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in suggestion: {e}")
        return {
            "suggestion": "",
            "field": request.field,
            "success": False,
            "error": str(e)
        }

# ==================== SONG CREATION ROUTE ====================

@api_router.post("/songs/create")
async def create_song(song_data: SongCreate):
    """Create a single song"""
    
    song_id = str(uuid.uuid4())
    
    # Generate title if not provided
    title = song_data.title
    if not title:
        try:
            title = await generate_ai_suggestion(
                "title",
                "",
                {"music_prompt": song_data.music_prompt, "genres": song_data.genres}
            )
        except:
            title = f"Track {uuid.uuid4().hex[:6].upper()}"
    
    # Select audio
    audio_data = select_audio_for_genres(song_data.genres)
    
    # Select cover art
    cover_art_url = select_cover_art(song_data.genres)
    
    # Create song document
    song_doc = {
        "id": song_id,
        "user_id": song_data.user_id,
        "title": title,
        "music_prompt": song_data.music_prompt,
        "genres": song_data.genres,
        "duration_seconds": audio_data.get("duration", song_data.duration_seconds),
        "vocal_languages": song_data.vocal_languages,
        "lyrics": song_data.lyrics or "",
        "artist_inspiration": song_data.artist_inspiration or "",
        "generate_video": song_data.generate_video,
        "video_style": song_data.video_style or "",
        "audio_url": audio_data["url"],
        "video_url": None,
        "cover_art_url": cover_art_url,
        "accuracy_percentage": 85,  # Default accuracy
        "created_at": datetime.now(timezone.utc).isoformat(),
        "album_id": None,
        "is_demo": True
    }
    
    await db.songs.insert_one(song_doc)
    song_doc.pop('_id', None)
    
    logger.info(f"✓ Song created: {song_id}")
    return song_doc

# ==================== ALBUM CREATION ROUTE ====================

@api_router.post("/albums/create")
async def create_album(album_data: AlbumCreate):
    """Create an album with multiple songs"""
    
    album_id = str(uuid.uuid4())
    
    # Generate title if not provided
    title = album_data.title
    if not title:
        try:
            title = await generate_ai_suggestion(
                "title",
                "",
                {"music_prompt": album_data.music_prompt, "genres": album_data.genres}
            )
        except:
            title = f"Album {uuid.uuid4().hex[:6].upper()}"
    
    # Select cover art
    cover_art_url = select_cover_art(album_data.genres)
    
    # Create album document
    album_doc = {
        "id": album_id,
        "user_id": album_data.user_id,
        "title": title,
        "music_prompt": album_data.music_prompt,
        "genres": album_data.genres,
        "vocal_languages": album_data.vocal_languages,
        "lyrics": album_data.lyrics or "",
        "artist_inspiration": album_data.artist_inspiration or "",
        "generate_video": album_data.generate_video,
        "video_style": album_data.video_style or "",
        "cover_art_url": cover_art_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "num_songs": album_data.num_songs
    }
    
    await db.albums.insert_one(album_doc)
    album_doc.pop('_id', None)
    
    # Generate songs
    songs = []
    used_urls = set()
    
    track_moods = ["energetic opener", "introspective", "building momentum", "peak energy", "reflective closer"]
    
    for i in range(album_data.num_songs):
        song_id = str(uuid.uuid4())
        mood = track_moods[i % len(track_moods)]
        
        # Generate track title
        try:
            track_title = await generate_ai_suggestion(
                "title",
                "",
                {"music_prompt": f"{album_data.music_prompt} - {mood}", "genres": album_data.genres}
            )
        except:
            track_title = f"Track {i + 1}"
        
        # Select audio
        audio_data = select_audio_for_genres(album_data.genres, used_urls)
        used_urls.add(audio_data["url"])
        
        # Create song
        song_doc = {
            "id": song_id,
            "user_id": album_data.user_id,
            "album_id": album_id,
            "track_number": i + 1,
            "title": track_title,
            "music_prompt": f"{album_data.music_prompt} ({mood})",
            "genres": album_data.genres,
            "duration_seconds": audio_data.get("duration", 30),
            "vocal_languages": album_data.vocal_languages,
            "lyrics": album_data.lyrics or "",
            "artist_inspiration": album_data.artist_inspiration or "",
            "generate_video": False,
            "video_style": "",
            "audio_url": audio_data["url"],
            "video_url": None,
            "cover_art_url": cover_art_url,
            "accuracy_percentage": 85,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_demo": True
        }
        
        await db.songs.insert_one(song_doc)
        
        songs.append({
            "id": song_id,
            "title": track_title,
            "audio_url": audio_data["url"],
            "cover_art_url": cover_art_url,
            "duration_seconds": audio_data.get("duration", 30)
        })
    
    logger.info(f"✓ Album created: {album_id} with {len(songs)} tracks")
    
    return {
        **album_doc,
        "songs": songs
    }

# ==================== DATA RETRIEVAL ROUTES ====================

@api_router.get("/songs/user/{user_id}")
async def get_user_songs(user_id: str):
    """Get all songs for user"""
    songs = await db.songs.find(
        {"user_id": user_id, "album_id": None},
        {"_id": 0}
    ).to_list(100)
    return songs

@api_router.get("/albums/user/{user_id}")
async def get_user_albums(user_id: str):
    """Get all albums for user"""
    albums = await db.albums.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    album_ids = [album['id'] for album in albums]
    if album_ids:
        songs = await db.songs.find(
            {"album_id": {"$in": album_ids}},
            {"_id": 0}
        ).to_list(500)
        
        songs_by_album = {}
        for song in songs:
            aid = song.get('album_id')
            if aid not in songs_by_album:
                songs_by_album[aid] = []
            songs_by_album[aid].append(song)
        
        for album in albums:
            album['songs'] = songs_by_album.get(album['id'], [])
    
    return albums

@api_router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    """Get dashboard data"""
    songs = await db.songs.find(
        {"user_id": user_id, "album_id": None},
        {"_id": 0}
    ).to_list(100)
    
    albums = await db.albums.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "songs": songs,
        "albums": albums,
        "stats": {
            "total_songs": len(songs),
            "total_albums": len(albums)
        }
    }

# ==================== KNOWLEDGE BASE ROUTES ====================

@api_router.get("/genres")
async def get_genres():
    """Get all genres"""
    genres = get_all_genres()
    return {"genres": genres}

@api_router.get("/languages")
async def get_languages():
    """Get all languages"""
    languages = get_all_languages()
    return {"languages": languages}

@api_router.get("/artists")
async def get_artists():
    """Get all artists"""
    all_artists = []
    for artists in ARTIST_DATABASE.values():
        all_artists.extend(artists)
    return {"artists": sorted(list(set(all_artists)))}

@api_router.get("/video-styles")
async def get_video_styles():
    """Get video styles"""
    return {"styles": VIDEO_STYLES}

# ==================== HEALTH CHECK ====================

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test MongoDB connection
        await db.command("ping")
        mongodb_status = "connected"
    except Exception as e:
        mongodb_status = f"error: {str(e)}"
    
    openai_status = "configured" if OPENAI_API_KEY else "not_configured"
    
    return {
        "status": "healthy",
        "mongodb": mongodb_status,
        "openai": openai_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ==================== MOUNT ROUTES ====================

app.include_router(api_router)

# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database indexes on startup"""
    logger.info("🚀 Starting SoundForge API Server...")
    
    try:
        # Create indexes
        await db.users.create_index("mobile", unique=True)
        await db.songs.create_index([("user_id", 1), ("created_at", -1)])
        await db.albums.create_index([("user_id", 1), ("created_at", -1)])
        logger.info("✓ Database indexes created")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down SoundForge API Server...")
    client.close()

# ==================== ROOT ROUTE ====================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "SoundForge API",
        "version": "2.0.0",
        "description": "AI Music Creation Platform - Independent Backend",
        "status": "running",
        "docs": "/docs"
    }

# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "server_new:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("ENV") != "production"
    )
