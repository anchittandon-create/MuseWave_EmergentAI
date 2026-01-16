"""
Muzify - AI Music Creation Application
Real Generative System with:
- OpenAI GPT-5.2 for AI Suggestions (unique per request)
- Replicate MusicGen for Real Audio Generation
- Sora 2 for Video Generation
- Global Knowledge Bases
"""

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
import replicate
import random
import hashlib
import asyncio
import httpx

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

# ==================== GLOBAL KNOWLEDGE BASES ====================

GENRE_KNOWLEDGE_BASE = {
    "mainstream": [
        "Pop", "Rock", "Hip-Hop", "R&B", "Electronic", "Jazz", "Classical", "Country", 
        "Reggae", "Blues", "Metal", "Folk", "Indie", "Soul", "Funk", "Disco"
    ],
    "electronic": [
        "House", "Techno", "Trance", "Dubstep", "Drum and Bass", "Ambient", "IDM",
        "Synthwave", "Chillwave", "Future Bass", "Hardstyle", "Breakbeat", "Garage",
        "Deep House", "Progressive House", "Tech House", "Electro", "EDM"
    ],
    "underground": [
        "Lo-fi", "Vaporwave", "Shoegaze", "Post-Punk", "Noise", "Drone", "Dark Ambient",
        "Industrial", "Witch House", "Seapunk", "Chiptune", "Glitch", "Breakcore"
    ],
    "regional": [
        "Afrobeats", "Reggaeton", "K-Pop", "J-Pop", "Bollywood", "Bossa Nova", "Flamenco",
        "Cumbia", "Salsa", "Bachata", "Merengue", "Samba", "Fado", "Qawwali", "Bhangra",
        "Highlife", "Soukous", "Mbalax", "Zouk", "Soca", "Dancehall", "Grime", "UK Garage"
    ],
    "micro_genres": [
        "Trap", "Drill", "Phonk", "Hyperpop", "Bedroom Pop", "Cloud Rap", "Emo Rap",
        "Math Rock", "Post-Rock", "Blackgaze", "Dream Pop", "Slowcore", "Sadcore",
        "Psych Rock", "Stoner Rock", "Doom Metal", "Black Metal", "Death Metal"
    ],
    "cinematic": [
        "Orchestral", "Cinematic", "Epic", "Trailer Music", "Film Score", "Video Game",
        "Ambient Soundscape", "New Age", "World Fusion", "Neo-Classical", "Minimalist"
    ]
}

ARTIST_KNOWLEDGE_BASE = {
    "electronic_producers": [
        "Aphex Twin", "Boards of Canada", "Four Tet", "Burial", "Flying Lotus",
        "Amon Tobin", "Bonobo", "Tycho", "Jon Hopkins", "Caribou", "Nicolas Jaar"
    ],
    "pop_artists": [
        "The Weeknd", "Dua Lipa", "Billie Eilish", "Doja Cat", "Harry Styles",
        "Olivia Rodrigo", "Bad Bunny", "Taylor Swift", "Post Malone", "SZA"
    ],
    "rock_artists": [
        "Tame Impala", "Arctic Monkeys", "The Strokes", "Radiohead", "Muse",
        "Queens of the Stone Age", "Royal Blood", "King Gizzard", "Khruangbin"
    ],
    "hip_hop_artists": [
        "Kendrick Lamar", "Tyler the Creator", "Frank Ocean", "Kanye West", 
        "Travis Scott", "J. Cole", "ASAP Rocky", "Playboi Carti", "21 Savage"
    ],
    "ambient_artists": [
        "Brian Eno", "Stars of the Lid", "Tim Hecker", "Grouper", "Hammock",
        "Sigur Rós", "Explosions in the Sky", "Godspeed You! Black Emperor"
    ],
    "jazz_artists": [
        "Kamasi Washington", "Robert Glasper", "Thundercat", "BadBadNotGood",
        "Snarky Puppy", "Nubya Garcia", "Shabaka Hutchings", "Alfa Mist"
    ]
}

LANGUAGE_KNOWLEDGE_BASE = [
    "Instrumental", "English", "Spanish", "French", "German", "Italian", "Portuguese",
    "Japanese", "Korean", "Chinese (Mandarin)", "Chinese (Cantonese)", "Hindi", "Arabic",
    "Russian", "Swedish", "Dutch", "Turkish", "Greek", "Hebrew", "Thai", "Vietnamese",
    "Indonesian", "Filipino", "Swahili", "Yoruba", "Zulu", "Polish", "Czech", "Hungarian"
]

VIDEO_STYLE_KNOWLEDGE_BASE = [
    "Cyberpunk cityscape", "Abstract geometric patterns", "Nature cinematography",
    "Psychedelic visuals", "Minimalist motion graphics", "Retro VHS aesthetic",
    "Anime-inspired animation", "Surreal dreamscape", "Urban street footage",
    "Underwater photography", "Space and cosmos", "Noir film aesthetic",
    "Glitch art", "Neon lights and reflections", "Desert landscapes",
    "Forest and mountains", "Ocean waves", "City timelapse", "Concert visuals"
]

def get_all_genres() -> List[str]:
    """Flatten all genres into a single list"""
    all_genres = []
    for category in GENRE_KNOWLEDGE_BASE.values():
        all_genres.extend(category)
    return sorted(list(set(all_genres)))

def get_all_artists() -> List[str]:
    """Flatten all artists into a single list"""
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
    duration_seconds: int = 10
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

# ==================== Uniqueness & Randomness Utilities ====================

def generate_uniqueness_seed() -> str:
    """Generate a unique seed for each request to ensure non-deterministic outputs"""
    timestamp = datetime.now(timezone.utc).isoformat()
    random_component = str(random.random())
    unique_id = str(uuid.uuid4())
    combined = f"{timestamp}-{random_component}-{unique_id}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def get_temperature_variation() -> float:
    """Return slightly varied temperature for unique outputs"""
    return round(random.uniform(0.75, 0.95), 2)

# ==================== AI Suggestion Engine (Real GPT-5.2) ====================

async def generate_ai_suggestion(field: str, current_value: str, context: dict) -> str:
    """
    Generate UNIQUE AI suggestions using GPT-5.2
    Each request produces different output through:
    - Unique session IDs
    - Temperature variation
    - Explicit uniqueness instructions
    - Context-aware semantic expansion
    """
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="AI service not configured")
    
    uniqueness_seed = generate_uniqueness_seed()
    temperature = get_temperature_variation()
    
    system_prompt = f"""You are a creative music AI assistant. Your role is to provide UNIQUE, NON-REPETITIVE suggestions.

CRITICAL RULES:
1. Every response MUST be completely different from any previous response
2. Use the uniqueness seed to vary your output: {uniqueness_seed}
3. Be creative, specific, and evocative
4. Never give generic or template-like responses
5. Draw from diverse musical knowledge across all cultures and eras
6. If refining existing input, ADD specificity without changing intent

Current timestamp for uniqueness: {datetime.now(timezone.utc).isoformat()}
Random variation factor: {random.random()}"""

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
    """Build field-specific prompts with context awareness"""
    
    context_parts = []
    if context.get("music_prompt"):
        context_parts.append(f"Music Description: {context['music_prompt']}")
    if context.get("genres"):
        context_parts.append(f"Genres: {', '.join(context['genres'])}")
    if context.get("lyrics"):
        context_parts.append(f"Lyrics/Theme: {context['lyrics'][:300]}")
    if context.get("artist_inspiration"):
        context_parts.append(f"Artist Inspiration: {context['artist_inspiration']}")
    
    context_str = "\n".join(context_parts) if context_parts else "No context provided yet"
    
    prompts = {
        "title": f"""Generate a UNIQUE, creative song/album title.
Context: {context_str}
Current title (if any): '{current_value}'

Requirements:
- Be evocative and memorable
- Match the mood implied by context
- This specific suggestion seed: {seed}
- Return ONLY the title, nothing else""",

        "music_prompt": f"""Create a UNIQUE, vivid music description.
Context: {context_str}
Current description: '{current_value}'

Requirements:
- Describe mood, energy, atmosphere, sonic textures
- Be specific about instrumentation and production style
- Include emotional journey and dynamics
- Unique seed: {seed}
- Return ONLY the description (2-4 sentences)""",

        "genres": f"""Suggest 2-4 music genres that fit this context.
Context: {context_str}

Requirements:
- Consider mood, energy, and cultural elements
- Mix mainstream and specific sub-genres when appropriate
- Unique seed: {seed}
- Return ONLY comma-separated genre names""",

        "lyrics": f"""Generate a lyrical theme or concept.
Context: {context_str}
Current lyrics: '{current_value}'

Requirements:
- Create an evocative theme, not full lyrics
- Match the emotional tone of the music
- Be poetic but accessible
- Unique seed: {seed}
- Return ONLY the theme/concept (2-3 sentences)""",

        "artist_inspiration": f"""Suggest 2-4 artist influences for this music.
Context: {context_str}

Requirements:
- Reference diverse artists across eras and cultures
- Explain the stylistic connection briefly
- Unique seed: {seed}
- Return as: "Artist1 (reason), Artist2 (reason)"
- Return ONLY the artist suggestions""",

        "video_style": f"""Suggest a unique visual style for a music video.
Context: {context_str}

Requirements:
- Match the sonic atmosphere
- Be specific about visual elements, colors, movements
- Reference visual aesthetics or art movements
- Unique seed: {seed}
- Return ONLY the style description (1-2 sentences)""",

        "vocal_languages": f"""Suggest appropriate vocal language(s).
Context: {context_str}
Lyrics provided: {bool(context.get('lyrics'))}

Requirements:
- If no lyrics and instrumental mood, suggest "Instrumental"
- Otherwise, infer from cultural context or suggest fitting language
- Unique seed: {seed}
- Return ONLY the language name(s), comma-separated"""
    }
    
    return prompts.get(field, f"Generate a creative suggestion for {field}. Context: {context_str}. Seed: {seed}")

# ==================== Music Generation (Real Replicate MusicGen) ====================

async def generate_music_with_replicate(
    prompt: str,
    duration: int,
    genres: List[str],
    artist_inspiration: str,
    vocal_info: str
) -> dict:
    """
    Generate REAL music using Replicate's MusicGen model.
    Each generation is unique due to model's inherent randomness.
    """
    if not REPLICATE_API_TOKEN:
        raise HTTPException(status_code=500, detail="Music generation service not configured")
    
    # Build comprehensive music prompt with all context
    full_prompt_parts = [prompt]
    
    if genres:
        full_prompt_parts.append(f"Genre: {', '.join(genres)}")
    
    if artist_inspiration:
        full_prompt_parts.append(f"Style influenced by: {artist_inspiration}")
    
    if vocal_info and vocal_info != "Instrumental":
        full_prompt_parts.append(f"With vocals in {vocal_info}")
    elif vocal_info == "Instrumental" or not vocal_info:
        full_prompt_parts.append("Instrumental, no vocals")
    
    full_prompt = ". ".join(full_prompt_parts)
    
    # MusicGen has 30 second limit, scale duration appropriately
    music_duration = min(duration, 30)
    
    logger.info(f"Generating music with prompt: {full_prompt[:100]}... Duration: {music_duration}s")
    
    try:
        # Use Replicate's MusicGen model
        output = replicate.run(
            "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
            input={
                "prompt": full_prompt,
                "duration": music_duration,
                "model_version": "stereo-melody-large",
                "output_format": "mp3",
                "normalization_strategy": "loudness"
            }
        )
        
        # Output is a URL to the generated audio
        audio_url = str(output) if output else None
        
        if not audio_url:
            raise Exception("No audio URL returned from generation")
        
        logger.info(f"Music generated successfully: {audio_url[:50]}...")
        
        return {
            "audio_url": audio_url,
            "duration": music_duration,
            "prompt_used": full_prompt
        }
        
    except Exception as e:
        logger.error(f"Music generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Music generation failed: {str(e)}")

# ==================== Video Generation (Real Sora 2) ====================

async def generate_video_with_sora(
    prompt: str,
    music_prompt: str,
    duration: int = 4
) -> Optional[str]:
    """
    Generate REAL video using Sora 2.
    Video is generated based on music description and visual style.
    """
    if not EMERGENT_LLM_KEY:
        logger.warning("Video generation not configured - EMERGENT_LLM_KEY missing")
        return None
    
    # Build video prompt combining music context and visual style
    video_prompt = f"""Create a music video visual:
Music atmosphere: {music_prompt}
Visual style: {prompt}
Make it cinematic, rhythmic, and visually compelling. 
Sync the visual energy with the implied musical energy."""

    # Sora supports 4, 8, or 12 second durations
    video_duration = 4 if duration <= 10 else (8 if duration <= 20 else 12)
    
    logger.info(f"Generating video with Sora 2. Duration: {video_duration}s")
    
    try:
        video_gen = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)
        
        video_bytes = video_gen.text_to_video(
            prompt=video_prompt,
            model="sora-2",
            size="1280x720",
            duration=video_duration,
            max_wait_time=600
        )
        
        if video_bytes:
            # Save video and return path/URL
            video_filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
            video_path = f"/app/generated_videos/{video_filename}"
            
            os.makedirs("/app/generated_videos", exist_ok=True)
            video_gen.save_video(video_bytes, video_path)
            
            logger.info(f"Video generated successfully: {video_path}")
            return video_path
        
        return None
        
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        return None  # Video failure shouldn't block audio success

# ==================== Cover Art Generation ====================

def generate_cover_art_url(genres: List[str], mood: str) -> str:
    """Generate contextually appropriate cover art URL based on genres and mood"""
    # Use Unsplash for dynamic cover art based on music context
    search_terms = []
    
    if any(g.lower() in ["electronic", "techno", "house", "edm", "synthwave"] for g in genres):
        search_terms = ["neon", "abstract", "cyberpunk", "digital art"]
    elif any(g.lower() in ["rock", "metal", "punk"] for g in genres):
        search_terms = ["dark", "urban", "grunge", "concert"]
    elif any(g.lower() in ["jazz", "blues", "soul"] for g in genres):
        search_terms = ["jazz", "vintage", "moody", "saxophone"]
    elif any(g.lower() in ["classical", "orchestral", "ambient"] for g in genres):
        search_terms = ["elegant", "minimal", "nature", "ethereal"]
    elif any(g.lower() in ["hip-hop", "rap", "trap"] for g in genres):
        search_terms = ["street", "urban", "graffiti", "city"]
    else:
        search_terms = ["music", "abstract", "colorful", "artistic"]
    
    # Add randomness to ensure unique covers
    random_term = random.choice(search_terms)
    random_id = random.randint(1, 1000)
    
    return f"https://source.unsplash.com/400x400/?{random_term},music&sig={random_id}"

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
    """Generate unique AI suggestion for any field"""
    suggestion = await generate_ai_suggestion(
        request.field, 
        request.current_value or "", 
        request.context
    )
    return {"suggestion": suggestion, "field": request.field}

# ==================== Song Creation (Real Generation) ====================

@api_router.post("/songs/create")
async def create_song(song_data: SongCreate, background_tasks: BackgroundTasks):
    """Create a song with REAL AI music generation"""
    
    if not song_data.music_prompt or not song_data.music_prompt.strip():
        raise HTTPException(status_code=422, detail="Music prompt is required")
    
    # Generate unique IDs
    song_id = str(uuid.uuid4())
    
    # Determine vocal language string
    vocal_lang = ", ".join(song_data.vocal_languages) if song_data.vocal_languages else "Instrumental"
    
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
    
    logger.info(f"Creating song: {title}")
    
    # Generate REAL music
    try:
        music_result = await generate_music_with_replicate(
            prompt=song_data.music_prompt,
            duration=min(song_data.duration_seconds, 30),  # MusicGen limit
            genres=song_data.genres,
            artist_inspiration=song_data.artist_inspiration or "",
            vocal_info=vocal_lang
        )
        audio_url = music_result["audio_url"]
        actual_duration = music_result["duration"]
    except Exception as e:
        logger.error(f"Music generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Music generation failed: {str(e)}")
    
    # Generate video if requested (in background to not block)
    video_url = None
    if song_data.generate_video and song_data.video_style:
        try:
            video_url = await generate_video_with_sora(
                prompt=song_data.video_style,
                music_prompt=song_data.music_prompt,
                duration=actual_duration
            )
        except Exception as e:
            logger.warning(f"Video generation failed (non-blocking): {e}")
    
    # Generate cover art
    cover_art_url = generate_cover_art_url(song_data.genres, song_data.music_prompt)
    
    # Create song document
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
        "video_url": video_url,
        "cover_art_url": cover_art_url,
        "album_id": song_data.album_id,
        "user_id": song_data.user_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.songs.insert_one(song_doc)
    
    return song_doc

# ==================== Album Creation (Real Generation with Variation) ====================

@api_router.post("/albums/create")
async def create_album(album_data: AlbumCreate):
    """Create an album with REAL AI generation and controlled variation between tracks"""
    
    if not album_data.music_prompt or not album_data.music_prompt.strip():
        raise HTTPException(status_code=422, detail="Music prompt is required")
    
    album_id = str(uuid.uuid4())
    
    # Generate album title if not provided
    title = album_data.title
    if not title:
        try:
            title = await generate_ai_suggestion("title", "", {
                "music_prompt": album_data.music_prompt,
                "genres": album_data.genres
            })
        except:
            title = f"Album {uuid.uuid4().hex[:6].upper()}"
    
    logger.info(f"Creating album: {title} with {album_data.num_songs} tracks")
    
    # Generate cover art for album
    cover_art_url = generate_cover_art_url(album_data.genres, album_data.music_prompt)
    
    # Create album document
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
    
    # Generate songs with CONTROLLED VARIATION
    songs = []
    vocal_lang = ", ".join(album_data.vocal_languages) if album_data.vocal_languages else "Instrumental"
    
    # Variation parameters for album coherence
    track_variations = [
        {"energy": "high", "structure": "intro/verse/chorus"},
        {"energy": "medium", "structure": "verse/bridge/outro"},
        {"energy": "low", "structure": "ambient/build/release"},
        {"energy": "building", "structure": "minimal to maximal"},
        {"energy": "dynamic", "structure": "verse/drop/breakdown"},
    ]
    
    for i in range(album_data.num_songs):
        variation = track_variations[i % len(track_variations)]
        
        # Create varied prompt for each track
        track_prompt = f"{album_data.music_prompt}. Track {i+1} variation: {variation['energy']} energy, {variation['structure']} structure. Make this track DISTINCT from others while maintaining album coherence."
        
        # Generate unique track title
        try:
            track_title = await generate_ai_suggestion("title", "", {
                "music_prompt": track_prompt,
                "genres": album_data.genres
            })
        except:
            track_title = f"{title} - Track {i + 1}"
        
        # Generate REAL music for each track
        try:
            music_result = await generate_music_with_replicate(
                prompt=track_prompt,
                duration=random.randint(15, 30),  # Varied duration
                genres=album_data.genres,
                artist_inspiration=album_data.artist_inspiration or "",
                vocal_info=vocal_lang
            )
            audio_url = music_result["audio_url"]
            actual_duration = music_result["duration"]
        except Exception as e:
            logger.error(f"Track {i+1} generation failed: {e}")
            continue  # Skip failed tracks but continue with others
        
        # Optional video generation
        video_url = None
        if album_data.generate_video and album_data.video_style:
            try:
                video_url = await generate_video_with_sora(
                    prompt=album_data.video_style,
                    music_prompt=track_prompt,
                    duration=actual_duration
                )
            except Exception as e:
                logger.warning(f"Video generation failed for track {i+1}: {e}")
        
        song_doc = {
            "id": str(uuid.uuid4()),
            "title": track_title,
            "music_prompt": track_prompt,
            "genres": album_data.genres,
            "duration_seconds": actual_duration,
            "vocal_languages": album_data.vocal_languages,
            "lyrics": album_data.lyrics or "",
            "artist_inspiration": album_data.artist_inspiration or "",
            "generate_video": album_data.generate_video,
            "video_style": album_data.video_style or "",
            "audio_url": audio_url,
            "video_url": video_url,
            "cover_art_url": cover_art_url,
            "album_id": album_id,
            "user_id": album_data.user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.songs.insert_one(song_doc)
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

# ==================== Data Retrieval Routes ====================

@api_router.get("/songs/user/{user_id}")
async def get_user_songs(user_id: str):
    songs = await db.songs.find({"user_id": user_id, "album_id": None}, {"_id": 0}).to_list(100)
    return songs

@api_router.get("/albums/user/{user_id}")
async def get_user_albums(user_id: str):
    albums = await db.albums.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    # Batch fetch all songs for efficiency
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
    
    # Batch fetch album songs
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

# ==================== Knowledge Base Routes ====================

@api_router.get("/genres")
async def get_genres():
    """Return comprehensive genre knowledge base"""
    return {
        "genres": get_all_genres(),
        "categories": GENRE_KNOWLEDGE_BASE
    }

@api_router.get("/languages")
async def get_languages():
    """Return language knowledge base"""
    return {"languages": LANGUAGE_KNOWLEDGE_BASE}

@api_router.get("/artists")
async def get_artists():
    """Return artist knowledge base for inspiration"""
    return {
        "artists": get_all_artists(),
        "categories": ARTIST_KNOWLEDGE_BASE
    }

@api_router.get("/video-styles")
async def get_video_styles():
    """Return video style suggestions"""
    return {"styles": VIDEO_STYLE_KNOWLEDGE_BASE}

# ==================== Health Check ====================

@api_router.get("/")
async def root():
    return {"message": "Muzify API - Real AI Music Generation"}

@api_router.get("/health")
async def api_health():
    return {"status": "healthy", "version": "2.0", "features": ["real_music_gen", "real_video_gen", "ai_suggestions"]}

# Include router and add root health check
app.include_router(api_router)

@app.get("/health")
async def health():
    return {"status": "healthy"}

# CORS Middleware
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
