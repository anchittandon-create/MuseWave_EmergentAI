"""
Muzify - AI Music Creation Application
Premium Demo Mode with:
- Real AI Suggestions (OpenAI GPT-5.2)
- Curated Royalty-Free Audio Library
- Real Video Generation (Sora 2) - Optional
- Comprehensive Knowledge Bases
"""

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
import random
import hashlib

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'muzify_db')]

# API Keys
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="Muzify API", description="AI Music Creation Platform")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== CURATED AUDIO LIBRARY ====================
# High-quality royalty-free tracks organized by mood/genre

AUDIO_LIBRARY = {
    "electronic": [
        {"url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3", "title": "Electronic Future", "duration": 30},
        {"url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_8cb749d484.mp3", "title": "Synthwave Drive", "duration": 25},
        {"url": "https://cdn.pixabay.com/download/audio/2023/07/30/audio_e5b7a41da5.mp3", "title": "Digital Dreams", "duration": 28},
        {"url": "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946bc3eb5b.mp3", "title": "Cyber Pulse", "duration": 22},
    ],
    "ambient": [
        {"url": "https://cdn.pixabay.com/download/audio/2022/02/22/audio_d1718ab41b.mp3", "title": "Peaceful Ambient", "duration": 30},
        {"url": "https://cdn.pixabay.com/download/audio/2021/11/25/audio_91b32e02f9.mp3", "title": "Ethereal Space", "duration": 26},
        {"url": "https://cdn.pixabay.com/download/audio/2022/08/02/audio_884fe92c21.mp3", "title": "Calm Waters", "duration": 24},
    ],
    "rock": [
        {"url": "https://cdn.pixabay.com/download/audio/2022/11/22/audio_a89df97458.mp3", "title": "Rock Energy", "duration": 28},
        {"url": "https://cdn.pixabay.com/download/audio/2023/03/18/audio_69a3b0f31c.mp3", "title": "Guitar Riff", "duration": 25},
        {"url": "https://cdn.pixabay.com/download/audio/2022/04/27/audio_67bcb97489.mp3", "title": "Power Chords", "duration": 30},
    ],
    "hip_hop": [
        {"url": "https://cdn.pixabay.com/download/audio/2023/09/20/audio_82b1a60920.mp3", "title": "Urban Beat", "duration": 26},
        {"url": "https://cdn.pixabay.com/download/audio/2022/08/25/audio_4f3b0a8a67.mp3", "title": "Street Flow", "duration": 28},
        {"url": "https://cdn.pixabay.com/download/audio/2023/05/16/audio_167152083e.mp3", "title": "Boom Bap", "duration": 24},
    ],
    "cinematic": [
        {"url": "https://cdn.pixabay.com/download/audio/2022/02/07/audio_b9bd4170e4.mp3", "title": "Epic Journey", "duration": 30},
        {"url": "https://cdn.pixabay.com/download/audio/2021/08/04/audio_12b0c7443c.mp3", "title": "Dramatic Score", "duration": 28},
        {"url": "https://cdn.pixabay.com/download/audio/2022/05/16/audio_5717667e89.mp3", "title": "Orchestral Rise", "duration": 25},
    ],
    "jazz": [
        {"url": "https://cdn.pixabay.com/download/audio/2022/08/31/audio_419263a59b.mp3", "title": "Smooth Jazz", "duration": 28},
        {"url": "https://cdn.pixabay.com/download/audio/2023/01/16/audio_5a40d34a40.mp3", "title": "Jazz Cafe", "duration": 26},
    ],
    "pop": [
        {"url": "https://cdn.pixabay.com/download/audio/2023/10/19/audio_c3b4f85d7e.mp3", "title": "Pop Vibes", "duration": 25},
        {"url": "https://cdn.pixabay.com/download/audio/2022/10/18/audio_2146216cc7.mp3", "title": "Feel Good", "duration": 28},
        {"url": "https://cdn.pixabay.com/download/audio/2023/04/19/audio_8c4a16a6b1.mp3", "title": "Summer Hit", "duration": 24},
    ],
    "lofi": [
        {"url": "https://cdn.pixabay.com/download/audio/2022/05/17/audio_69a61cd6d6.mp3", "title": "Lofi Study", "duration": 30},
        {"url": "https://cdn.pixabay.com/download/audio/2022/11/16/audio_7e3c4b39ca.mp3", "title": "Chill Beats", "duration": 26},
        {"url": "https://cdn.pixabay.com/download/audio/2023/02/15/audio_8dca2c54bc.mp3", "title": "Rainy Day", "duration": 28},
    ],
    "classical": [
        {"url": "https://cdn.pixabay.com/download/audio/2022/01/20/audio_d0c6ff1bcd.mp3", "title": "Piano Sonata", "duration": 30},
        {"url": "https://cdn.pixabay.com/download/audio/2022/09/06/audio_47fa8af5f4.mp3", "title": "Strings Ensemble", "duration": 28},
    ],
    "default": [
        {"url": "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8a73467.mp3", "title": "Inspiring", "duration": 28},
        {"url": "https://cdn.pixabay.com/download/audio/2022/08/04/audio_2dde668d05.mp3", "title": "Uplifting", "duration": 25},
        {"url": "https://cdn.pixabay.com/download/audio/2023/06/21/audio_3d955ac6af.mp3", "title": "Creative Flow", "duration": 30},
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
    "cinematic": ["Orchestral", "Cinematic", "Epic", "Film Score", "Video Game", "Ambient Soundscape", "Neo-Classical", "Minimalist"]
}

ARTIST_KNOWLEDGE_BASE = {
    "electronic": ["Aphex Twin", "Boards of Canada", "Four Tet", "Burial", "Flying Lotus", "Bonobo", "Tycho", "Jon Hopkins", "Caribou"],
    "pop": ["The Weeknd", "Dua Lipa", "Billie Eilish", "Harry Styles", "Taylor Swift", "Post Malone", "SZA"],
    "rock": ["Tame Impala", "Arctic Monkeys", "Radiohead", "Muse", "Royal Blood", "Khruangbin"],
    "hip_hop": ["Kendrick Lamar", "Tyler the Creator", "Frank Ocean", "Travis Scott", "J. Cole"],
    "ambient": ["Brian Eno", "Stars of the Lid", "Tim Hecker", "Sigur Rós", "Explosions in the Sky"],
    "jazz": ["Kamasi Washington", "Robert Glasper", "Thundercat", "Snarky Puppy"]
}

LANGUAGE_KNOWLEDGE_BASE = [
    "Instrumental", "English", "Spanish", "French", "German", "Italian", "Portuguese",
    "Japanese", "Korean", "Chinese (Mandarin)", "Hindi", "Arabic", "Russian", "Swedish"
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
    genres: List[str] = []
    duration_seconds: int = 15
    vocal_languages: List[str] = []
    lyrics: Optional[str] = ""
    artist_inspiration: Optional[str] = ""
    generate_video: bool = False
    video_style: Optional[str] = ""
    mode: str = "single"
    album_id: Optional[str] = None
    user_id: str

class AlbumCreate(BaseModel):
    title: str
    music_prompt: str
    genres: List[str] = []
    vocal_languages: List[str] = []
    lyrics: Optional[str] = ""
    artist_inspiration: Optional[str] = ""
    generate_video: bool = False
    video_style: Optional[str] = ""
    num_songs: int = 3
    user_id: str

class AISuggestRequest(BaseModel):
    field: str
    current_value: Optional[str] = ""
    context: dict = {}

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

# ==================== AI Suggestion Engine (Real GPT-5.2) ====================

async def generate_ai_suggestion(field: str, current_value: str, context: dict) -> str:
    """Generate UNIQUE AI suggestions using GPT-5.2"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="AI service not configured")
    
    uniqueness_seed = generate_uniqueness_seed()
    
    system_prompt = f"""You are an elite music industry creative director with deep knowledge across all genres, cultures, and eras.

CRITICAL RULES:
1. Every response MUST be completely unique and creative
2. Be specific, evocative, and professional
3. Use vivid sensory language
4. Reference specific production techniques when relevant
5. Draw from diverse musical knowledge
6. Uniqueness seed: {uniqueness_seed}

Never give generic responses. Always surprise with creativity."""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"suggest-{uniqueness_seed}-{uuid.uuid4()}",
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        prompt = build_suggestion_prompt(field, current_value, context, uniqueness_seed)
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return response.strip()
    except Exception as e:
        logger.error(f"AI suggestion error: {e}")
        raise HTTPException(status_code=500, detail=f"AI suggestion failed: {str(e)}")

def build_suggestion_prompt(field: str, current_value: str, context: dict, seed: str) -> str:
    context_parts = []
    if context.get("music_prompt"):
        context_parts.append(f"Music Description: {context['music_prompt']}")
    if context.get("genres"):
        context_parts.append(f"Genres: {', '.join(context['genres'])}")
    if context.get("lyrics"):
        context_parts.append(f"Lyrics/Theme: {context['lyrics'][:300]}")
    if context.get("artist_inspiration"):
        context_parts.append(f"Artist Inspiration: {context['artist_inspiration']}")
    
    context_str = "\n".join(context_parts) if context_parts else "No context provided"
    
    prompts = {
        "title": f"""Create a UNIQUE, memorable song/album title.
Context: {context_str}
Current title: '{current_value}'
Requirements: Be evocative, poetic, memorable. Match the mood. Return ONLY the title.""",

        "music_prompt": f"""Create a vivid, detailed music description.
Context: {context_str}
Current: '{current_value}'
Requirements: Describe mood, energy, instrumentation, production style, emotional arc. Be specific about sonic textures. 2-4 sentences. Return ONLY the description.""",

        "genres": f"""Suggest 2-4 fitting music genres.
Context: {context_str}
Requirements: Mix mainstream and specific sub-genres. Return ONLY comma-separated genre names.""",

        "lyrics": f"""Generate a lyrical theme or concept.
Context: {context_str}
Current: '{current_value}'
Requirements: Create an evocative theme (not full lyrics). Be poetic. 2-3 sentences. Return ONLY the theme.""",

        "artist_inspiration": f"""Suggest 2-4 artist influences.
Context: {context_str}
Requirements: Reference diverse artists. Format: "Artist1 (reason), Artist2 (reason)". Return ONLY the suggestions.""",

        "video_style": f"""Suggest a visual style for a music video.
Context: {context_str}
Requirements: Be specific about colors, movements, aesthetics. 1-2 sentences. Return ONLY the description.""",

        "vocal_languages": f"""Suggest appropriate vocal language(s).
Context: {context_str}
Requirements: If instrumental mood, suggest "Instrumental". Otherwise infer from context. Return ONLY language name(s)."""
    }
    
    return prompts.get(field, f"Generate a creative suggestion for {field}. Context: {context_str}")

# ==================== Auth Routes ====================

@api_router.post("/auth/signup", response_model=UserResponse)
async def signup(user_data: UserCreate):
    existing = await db.users.find_one({"mobile": user_data.mobile}, {"_id": 0})
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
    if not user:
        raise HTTPException(status_code=404, detail="No account found. Please sign up first.")
    
    return UserResponse(id=user['id'], name=user['name'], mobile=user['mobile'], created_at=user['created_at'])

# ==================== AI Suggest Routes ====================

@api_router.post("/suggest")
async def ai_suggest(request: AISuggestRequest):
    suggestion = await generate_ai_suggestion(request.field, request.current_value or "", request.context)
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
            })
        except:
            title = f"Track {uuid.uuid4().hex[:6].upper()}"
    
    # Select appropriate audio from library
    audio_data = select_audio_for_genres(song_data.genres)
    audio_url = audio_data["url"]
    actual_duration = audio_data["duration"]
    
    # Select cover art
    cover_art_url = select_cover_art(song_data.genres)
    
    song_doc = {
        "id": song_id,
        "title": title,
        "music_prompt": song_data.music_prompt,
        "genres": song_data.genres,
        "duration_seconds": actual_duration,
        "vocal_languages": song_data.vocal_languages,
        "lyrics": song_data.lyrics or "",
        "artist_inspiration": song_data.artist_inspiration or "",
        "generate_video": song_data.generate_video,
        "video_style": song_data.video_style or "",
        "audio_url": audio_url,
        "video_url": None,
        "cover_art_url": cover_art_url,
        "album_id": song_data.album_id,
        "user_id": song_data.user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_demo": True
    }
    
    await db.songs.insert_one(song_doc)
    
    # Remove MongoDB _id field for JSON serialization
    song_doc.pop('_id', None)
    return song_doc

# ==================== Album Creation ====================

@api_router.post("/albums/create")
async def create_album(album_data: AlbumCreate):
    if not album_data.music_prompt or not album_data.music_prompt.strip():
        raise HTTPException(status_code=422, detail="Music prompt is required")
    
    album_id = str(uuid.uuid4())
    
    # Generate title if not provided
    title = album_data.title
    if not title:
        try:
            title = await generate_ai_suggestion("title", "", {
                "music_prompt": album_data.music_prompt,
                "genres": album_data.genres
            })
        except:
            title = f"Album {uuid.uuid4().hex[:6].upper()}"
    
    cover_art_url = select_cover_art(album_data.genres)
    
    album_doc = {
        "id": album_id,
        "title": title,
        "music_prompt": album_data.music_prompt,
        "genres": album_data.genres,
        "vocal_languages": album_data.vocal_languages,
        "lyrics": album_data.lyrics or "",
        "artist_inspiration": album_data.artist_inspiration or "",
        "generate_video": album_data.generate_video,
        "video_style": album_data.video_style or "",
        "cover_art_url": cover_art_url,
        "user_id": album_data.user_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.albums.insert_one(album_doc)
    # Remove MongoDB _id field for JSON serialization
    album_doc.pop('_id', None)
    
    # Generate tracks with variation
    songs = []
    used_audio_urls = set()
    
    track_moods = ["energetic opener", "introspective", "building momentum", "peak energy", "reflective closer"]
    
    for i in range(album_data.num_songs):
        mood_variation = track_moods[i % len(track_moods)]
        
        # Generate unique track title
        try:
            track_title = await generate_ai_suggestion("title", "", {
                "music_prompt": f"{album_data.music_prompt} - {mood_variation}",
                "genres": album_data.genres
            })
        except:
            track_title = f"{title} - Track {i + 1}"
        
        audio_data = select_audio_for_genres(album_data.genres, used_audio_urls)
        used_audio_urls.add(audio_data["url"])
        
        song_doc = {
            "id": str(uuid.uuid4()),
            "title": track_title,
            "music_prompt": f"{album_data.music_prompt} ({mood_variation})",
            "genres": album_data.genres,
            "duration_seconds": audio_data["duration"],
            "vocal_languages": album_data.vocal_languages,
            "lyrics": album_data.lyrics or "",
            "artist_inspiration": album_data.artist_inspiration or "",
            "generate_video": False,
            "video_style": "",
            "audio_url": audio_data["url"],
            "video_url": None,
            "cover_art_url": cover_art_url,
            "album_id": album_id,
            "user_id": album_data.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_demo": True
        }
        
        await db.songs.insert_one(song_doc)
        # Remove MongoDB _id field for JSON serialization
        song_doc.pop('_id', None)
        songs.append({
            "id": song_doc["id"],
            "title": song_doc["title"],
            "audio_url": song_doc["audio_url"],
            "video_url": song_doc["video_url"],
            "cover_art_url": song_doc["cover_art_url"],
            "duration_seconds": song_doc["duration_seconds"]
        })
    
    return {
        "id": album_id,
        "title": title,
        "music_prompt": album_data.music_prompt,
        "genres": album_data.genres,
        "cover_art_url": cover_art_url,
        "user_id": album_data.user_id,
        "created_at": album_doc['created_at'],
        "songs": songs
    }

# ==================== Data Retrieval ====================

@api_router.get("/songs/user/{user_id}")
async def get_user_songs(user_id: str):
    songs = await db.songs.find({"user_id": user_id, "album_id": None}, {"_id": 0}).to_list(100)
    return songs

@api_router.get("/albums/user/{user_id}")
async def get_user_albums(user_id: str):
    albums = await db.albums.find({"user_id": user_id}, {"_id": 0}).to_list(100)
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
            album['songs'] = songs_by_album.get(album['id'], [])
    return albums

@api_router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    songs = await db.songs.find({"user_id": user_id, "album_id": None}, {"_id": 0}).to_list(100)
    albums = await db.albums.find({"user_id": user_id}, {"_id": 0}).to_list(100)
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
            album['songs'] = songs_by_album.get(album['id'], [])
    return {"songs": songs, "albums": albums}

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
    return {"message": "Muzify API - AI Music Creation"}

@api_router.get("/health")
async def api_health():
    return {"status": "healthy", "version": "2.1", "mode": "demo", "features": ["ai_suggestions", "curated_audio", "knowledge_bases"]}

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
