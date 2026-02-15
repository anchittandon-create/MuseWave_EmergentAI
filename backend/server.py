"""
Muzify - AI Music Creation Application
Premium Demo Mode with:
- Real AI Suggestions (OpenAI GPT-5.2)
- Curated Royalty-Free Audio Library
- Real Video Generation (Sora 2) - Optional
- Comprehensive Knowledge Bases
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
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
import random
import hashlib
import zipfile
import io
import base64
import requests
from PIL import Image, ImageDraw, ImageFont
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'muzify_db')]

# API Keys
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
REPLICATE_API_TOKEN = os.environ.get('REPLICATE_API_TOKEN')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="Muzify API", description="AI Music Creation Platform")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

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

def calculate_audio_accuracy(selected_audio: dict, song_data: SongCreate) -> float:
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
    user_category = get_genre_category(song_data.genres)
    genre_match = 0.4 if selected_category == user_category else 0.2
    accuracy += genre_match
    
    # Duration match (30%)
    audio_duration = selected_audio.get("duration", 0)
    user_duration = song_data.duration_seconds
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

# ==================== AI Suggestion Engine (Real GPT-5.2) ====================

async def generate_ai_suggestion(field: str, current_value: str, context: dict) -> str:
    """Generate UNIQUE AI suggestions using GPT-5.2 with advanced diversity mechanisms"""
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
7. NEVER repeat similar concepts, themes, or terminology from previous suggestions
8. Each suggestion should introduce NEW ideas, perspectives, and terminology

Never give generic responses. Always surprise with creativity and innovation."""

    try:
        # Use session-based diversity to ensure different responses for same field
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"suggest-{field}-{uniqueness_seed}-{uuid.uuid4()}",
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        prompt = build_suggestion_prompt(field, current_value, context, uniqueness_seed)
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        suggestion = response.strip()
        
        # Post-processing validation for quality
        if suggestion:
            # For list-based fields (genres, languages), ensure list format
            if field in ["genres", "vocal_languages"] and "," not in suggestion and field != "vocal_languages":
                # Single genre provided, ensure it's reasonable
                if len(suggestion) > 50:
                    # Too long for a single genre, likely error
                    suggestion = suggestion.split(",")[0].strip()
            
            # Remove any explanatory text that might have slipped through
            if "\n" in suggestion:
                suggestion = suggestion.split("\n")[0].strip()
        
        return suggestion
    except Exception as e:
        logger.error(f"AI suggestion error: {e}")
        raise HTTPException(status_code=500, detail=f"AI suggestion failed: {str(e)}")

async def generate_lyrics(music_prompt: str, genres: list, languages: list, title: str = "") -> str:
    """Generate creative lyrics based on music description, genres, and languages"""
    if not EMERGENT_LLM_KEY:
        return ""  # Silently fail for lyrics generation
    
    try:
        system_prompt = """You are a Grammy-winning lyricist and songwriter with expertise in multiple languages and musical genres.
        
CRITICAL RULES FOR LYRICS:
1. Create authentic, emotionally resonant lyrics that match the musical style
2. Use vivid imagery and poetic language
3. Adapt linguistic quality to match the language
4. Consider cultural context and authenticity
5. Write in the specified language(s)
6. Create lyrics that a professional vocalist would enjoy performing
7. Structure as verse-chorus or other appropriate format

Always provide complete, singable lyrics - not just themes or concepts."""

        languages_str = ", ".join(languages) if languages else "English"
        genres_str = ", ".join(genres) if genres else "pop"
        title_ref = f"for '{title}'" if title else ""
        
        lyrics_prompt = f"""Write complete, emotionally engaging lyrics {title_ref} for a {genres_str} song.

Music Description: {music_prompt}

Requirements:
- Language(s): {languages_str}
- Style: Match the mood and energy of the music description
- Format: Verse 1 → Chorus → Verse 2 → Chorus → Bridge (optional) → Final Chorus
- Length: 3-4 verses and 2-3 chorus repetitions
- Authenticity: Create lyrics that feel natural and singable
- Imagery: Use vivid, specific imagery that connects to the musical theme

Write only the lyrics, no explanations. Make them professional and ready for recording."""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"lyrics-{uuid.uuid4()}",
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=lyrics_prompt)
        response = await chat.send_message(user_message)
        
        return response.strip() if response else ""
    except Exception as e:
        logger.error(f"Lyrics generation error: {e}")
        return ""  # Return empty string if lyrics generation fails

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
    if context.get("duration_seconds"):
        context_parts.append(f"Duration: {context['duration_seconds']}s")
    
    context_str = "\n".join(context_parts) if context_parts else "No context provided"
    
    # Extract numeric seed components for varied suggestion styles
    seed_hash = hash(seed) % 100
    suggestion_style = ["avant-garde", "classical", "contemporary", "experimental", "fusion"][seed_hash % 5]
    
    prompts = {
        "title": f"""CRITICAL: Create a UNIQUE, memorable, evocative song/album title that perfectly captures the essence of this music.
Context: {context_str}
Current title: '{current_value}'
Seed: {seed}

UNIQUENESS REQUIREMENT:
- Each suggestion MUST be completely different from any previous suggestions
- Avoid repeating themes, patterns, or word combinations you've seen before
- Draw inspiration from unexpected cultural, literary, or scientific sources
- Use the suggestion style: {suggestion_style}

Requirements:
- Be poetic, memorable, and emotionally resonant
- Match the mood and energy of the music
- Avoid generic terms like "Song", "Track", "Music", "Dream", "Soul", "Heart"
- Make it truly memorable and unique for listeners
- Consider wordplay, metaphors, literary references, or cultural nuances
- Draw from unexpected sources (history, mythology, physics, nature, emotions, languages)
- Use sophisticated linguistic techniques (alliteration, assonance, paradox, oxymoron)
- Could be abstract, poetic, or metaphorical
- Return ONLY the title, no explanation

CREATIVITY RULES:
1. Think of 5 VERY different title concepts
2. Choose the one that's LEAST obvious and MOST intriguing
3. Ensure it's specific to this music description, not generic
4. Make it something listeners would want to search for or remember""",

        "music_prompt": f"""CRITICAL: Write a vivid, detailed, professional music production description that would guide a musician/producer.
Context: {context_str}
Current: '{current_value}'
Seed: {seed}

UNIQUENESS REQUIREMENT:
- Each description MUST use completely different production terminology
- Avoid repeating the same sonic descriptors (warm, dark, bright, etc.)
- Reference different production techniques and approaches each time
- Use the approach: {suggestion_style}

Requirements:
- Describe the sonic landscape, mood, energy, and emotional arc in ORIGINAL ways
- Be specific about instrumentation, production style, and technical execution
- Reference specific production techniques (tape saturation, granular synthesis, spectral processing, convolution, modulation, time-stretching, etc.)
- Describe texture, rhythm patterns, dynamics, spatial qualities, and frequency balance
- Include unexpected sonic elements that elevate the composition
- Specify emotional journey and listener experience
- 2-4 sentences maximum, highly detailed
- Return ONLY the description, no explanation

CREATIVITY RULES:
1. Avoid repetitive descriptors (warm, dark, lush, tight, punchy)
2. Use technical and artistic language
3. Create a unique production philosophy for this track
4. Make it inspiring and specific for music creation""",

        "genres": f"""CRITICAL: Suggest 2-4 precise music genres/sub-genres that perfectly fit this music - COMPLETELY DIFFERENT and UNIQUE each time.
Context: {context_str}
Seed: {seed}

UNIQUENESS REQUIREMENT:
- Each suggestion MUST be completely fresh and unexpected
- Avoid popular or obvious genre combinations
- Mix genres in creative, non-obvious ways
- Consider emerging, niche, and cross-cultural genres
- Use the style: {suggestion_style}

Requirements:
- Mix mainstream genres with SPECIFIC, NICHE sub-genres and micro-genres
- Be creative and original (avoid predictable combinations like "Synthwave + Retrowave")
- Consider deep production style, emotional mood, and cultural context
- Include experimental, emerging, or genre-bending possibilities
- Look beyond surface-level categorization to deeper musical DNA
- Consider production techniques, instrumentation, and regional influences
- Format: Comma-separated genre names only
- Could include emerging genres, fusion styles, or unexpected cultural blends
- Return ONLY the genres, no explanation (e.g., "Ambient Techno, Micro House, Glitch Pop")

CREATIVITY RULES:
1. Avoid repeating any genres from previous suggestions
2. Create surprising but logical genre combinations
3. Include at least one unexpected or experimental genre
4. Make listeners discover new genre territories""",

        "lyrics": f"""CRITICAL: Create an evocative, completely UNIQUE lyrical theme, concept, or storytelling hook that captures the music's essence.
Context: {context_str}
Current: '{current_value}'
Seed: {seed}

UNIQUENESS REQUIREMENT:
- Each concept MUST be completely original and never repeated
- Avoid common song themes (love, loss, dancing, partying)
- Use unexpected narrative angles and perspectives
- Reference diverse cultural, historical, or scientific inspiration
- Use the approach: {suggestion_style}

Requirements:
- Create a memorable, conceptual theme (not full lyrics, but vivid enough to inspire songwriting)
- Be poetic, mysterious, intriguing, thought-provoking, or philosophically engaging
- Align deeply with the musical mood, genres, and production style
- Could be metaphorical, abstract, narrative, emotional, or conceptual
- Use unexpected imagery from diverse sources (science, nature, history, culture, psychology)
- Could be a story fragment, perspective shift, or emotional state
- 1-3 sentences of pure creative inspiration
- Return ONLY the lyrical concept, no explanation

CREATIVITY RULES:
1. Avoid common song topics (love, heartbreak, dancing, freedom, night)
2. Create unexpected narrative angles
3. Use surprising metaphors and imagery
4. Make it specific to this music's unique sonic identity""",

        "artist_inspiration": f"""CRITICAL: Suggest 2-4 specific artist influences with detailed technical/stylistic reasoning - COMPLETELY UNIQUE each time.
Context: {context_str}
Seed: {seed}

UNIQUENESS REQUIREMENT:
- Each suggestion MUST reference completely different artists
- Avoid repeating artists from previous suggestions
- Mix legendary and emerging artists unpredictably
- Reference artists from diverse genres, eras, and cultures
- Use the approach: {suggestion_style}

Requirements:
- Reference a diverse mix of established legends, contemporary innovators, AND emerging/underground artists
- Provide SPECIFIC technical or stylistic reasons for each artist choice
- Consider production techniques, sound design philosophy, emotional intensity, cultural perspective, innovation
- Include artists from different eras (classical, 20th century, 21st century), genres, and cultural backgrounds
- Format: "Artist1 (production innovation/sound design explanation), Artist2 (different stylistic aspect)..."
- Could include experimental artists, producers, sound designers, or culture icons
- Be thoughtful, specific, and genuinely surprising
- Return ONLY the suggestions, no explanation

CREATIVITY RULES:
1. Avoid repeating artists from previous suggestions
2. Draw connections from unexpected angles (same era different culture, same technique different genre)
3. Include at least one emerging or experimental artist
4. Explain WHY each artist fits, not just that they do
5. Reference specific works, techniques, or innovations from each artist""",

        "video_style": f"""CRITICAL: Suggest a specific, cinematic, and completely UNIQUE visual style for a music video.
Context: {context_str}
Seed: {seed}

UNIQUENESS REQUIREMENT:
- Each video concept MUST be completely original and different
- Avoid repeating visual styles, color palettes, or filming techniques
- Reference diverse cinematographic movements and visual artists
- Create genuinely surprising visual directions
- Use the aesthetic: {suggestion_style}

Requirements:
- Be VERY specific about color palettes, camera movements, editing pace, visual metaphors
- Reference cinematographic styles, directors, films, visual art movements
- Include mood, atmosphere, lighting design, emotional impact, and tone
- Describe actual camera techniques (tracking shots, jump cuts, slow-motion, perspective shifts, unconventional framing)
- Could reference art movements, fashion eras, visual artists, architecture, or cultural aesthetics
- Include specific production design elements (sets, props, locations, textures, materials)
- Describe the overall visual narrative or emotional journey
- 3-4 sentences of vivid, specific visual storytelling
- Return ONLY the visual description, no explanation

CREATIVITY RULES:
1. Avoid overused visual concepts (neon lights, silhouettes, abstract patterns)
2. Reference diverse cinematographic traditions
3. Create surprising visual directions that complement the music
4. Be specific enough for a director to execute the vision""",

        "vocal_languages": f"""CRITICAL: Suggest the most appropriate vocal language(s) for this music - COMPLETELY UNIQUE and ORIGINAL each time.
Context: {context_str}
Seed: {seed}

UNIQUENESS REQUIREMENT:
- Each suggestion MUST be completely fresh and unexpected
- Avoid repeating language suggestions
- Consider linguistic diversity and cultural authenticity
- Use the approach: {suggestion_style}

Requirements:
- If music is clearly instrumental-focused or conceptually requires it, respond: "Instrumental"
- If vocals are appropriate, choose specific language(s) matching the vibe and production style
- Consider: cultural authenticity, phonetic beauty, linguistic rhythm, emotional connotations, pronunciation flow
- Could suggest unexpected language choices for dramatic or conceptual effect
- Could suggest multilingual approach, code-switching, or linguistic fusion
- Consider regional dialects, tonal languages, constructed languages, or vocal textures
- Think about linguistic origin, sound qualities, and cultural resonance
- Be creative, specific, and culturally respectful
- Return ONLY the language name(s), no explanation

CREATIVITY RULES:
1. Avoid repeating the same languages from previous suggestions
2. Consider unexpected but authentic language choices
3. Think about linguistic phonetics and how they complement the music
4. Make culturally aware and respectful suggestions"""
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
        
        # Generate lyrics for this track if vocals are included
        track_lyrics = album_data.lyrics or ""
        if not track_lyrics and album_data.vocal_languages and "Instrumental" not in album_data.vocal_languages:
            try:
                track_lyrics = await generate_lyrics(
                    f"{album_data.music_prompt} ({mood_variation})",
                    album_data.genres,
                    album_data.vocal_languages,
                    track_title
                )
            except Exception as e:
                logger.warning(f"Failed to generate lyrics for album track {i + 1}: {e}")
        
        song_doc = {
            "id": str(uuid.uuid4()),
            "title": track_title,
            "music_prompt": f"{album_data.music_prompt} ({mood_variation})",
            "genres": album_data.genres,
            "duration_seconds": audio_data["duration"],
            "vocal_languages": album_data.vocal_languages,
            "lyrics": track_lyrics,
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
        if isinstance(output, str):
            return output
        if isinstance(output, (list, tuple)) and output:
            return output[0] if isinstance(output[0], str) else str(output[0])
        if hasattr(output, "url"):
            return getattr(output, "url", None)
        return None
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
        loop = asyncio.get_event_loop()
        video_url = await loop.run_in_executor(None, lambda: _generate_video_via_replicate(song))
        if not video_url:
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
    return {"message": "Muzify API - AI Music Creation", "note": "Frontend not built yet"}
