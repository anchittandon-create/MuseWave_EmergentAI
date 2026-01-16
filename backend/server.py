from fastapi import FastAPI, APIRouter, HTTPException
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

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
    duration_seconds: int = 180
    vocal_languages: List[str] = []
    lyrics: Optional[str] = ""
    artist_inspiration: Optional[str] = ""
    generate_video: bool = False
    video_style: Optional[str] = ""
    mode: str = "single"  # single or album
    album_id: Optional[str] = None
    user_id: str

class Song(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    music_prompt: str
    genres: List[str]
    duration_seconds: int
    vocal_languages: List[str]
    lyrics: str
    artist_inspiration: str
    generate_video: bool
    video_style: str
    audio_url: str
    video_url: Optional[str] = None
    cover_art_url: str
    album_id: Optional[str] = None
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

class Album(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    music_prompt: str
    genres: List[str]
    vocal_languages: List[str]
    lyrics: str
    artist_inspiration: str
    generate_video: bool
    video_style: str
    cover_art_url: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AISuggestRequest(BaseModel):
    field: str
    current_value: Optional[str] = ""
    context: dict = {}

# ==================== Helper Functions ====================

SAMPLE_AUDIO_URLS = [
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3",
]

COVER_ART_URLS = [
    "https://images.unsplash.com/photo-1645919268997-e8f6d5ee81e6?w=400",
    "https://images.unsplash.com/photo-1645919268978-35253dfb1d75?w=400",
    "https://images.unsplash.com/photo-1765445665997-6553bd993ff1?w=400",
    "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400",
    "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400",
]

def get_random_audio_url():
    return random.choice(SAMPLE_AUDIO_URLS)

def get_random_cover_art():
    return random.choice(COVER_ART_URLS)

async def get_ai_suggestion(field: str, current_value: str, context: dict) -> str:
    """Generate AI suggestions using OpenAI GPT-5.2"""
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        return get_fallback_suggestion(field, current_value, context)
    
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"suggest-{uuid.uuid4()}",
            system_message="You are a creative music assistant helping users craft better music descriptions. Be concise, creative, and helpful. Return only the suggestion text, no explanations."
        ).with_model("openai", "gpt-5.2")
        
        prompt = build_suggestion_prompt(field, current_value, context)
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        return response.strip()
    except Exception as e:
        logging.error(f"AI suggestion error: {e}")
        return get_fallback_suggestion(field, current_value, context)

def build_suggestion_prompt(field: str, current_value: str, context: dict) -> str:
    context_str = ""
    if context.get("music_prompt"):
        context_str += f"Music prompt: {context['music_prompt']}\n"
    if context.get("genres"):
        context_str += f"Genres: {', '.join(context['genres'])}\n"
    if context.get("lyrics"):
        context_str += f"Lyrics/Theme: {context['lyrics'][:200]}\n"
    
    prompts = {
        "title": f"Suggest a creative, memorable title for a song. {context_str}\nCurrent title: '{current_value}'\nSuggest a better title or create one if empty:",
        "music_prompt": f"Create a vivid music description including mood, energy, atmosphere.\n{context_str}\nCurrent description: '{current_value}'\nSuggest an improved or new description:",
        "genres": f"Suggest 1-3 appropriate music genres.\n{context_str}\nReturn genres as comma-separated list:",
        "lyrics": f"Suggest a theme or short lyrics concept.\n{context_str}\nCurrent lyrics: '{current_value}'\nSuggest an improvement or theme:",
        "artist_inspiration": f"Suggest stylistic artist references that match the mood.\n{context_str}\nSuggest 2-3 artists:",
        "video_style": f"Suggest a visual style for a music video.\n{context_str}\nSuggest a creative video style:",
        "vocal_languages": f"Based on the content, suggest appropriate vocal language(s).\n{context_str}\nSuggest language(s):",
    }
    return prompts.get(field, f"Suggest a creative value for {field}: {current_value}")

def get_fallback_suggestion(field: str, current_value: str, context: dict) -> str:
    fallbacks = {
        "title": "Midnight Echoes",
        "music_prompt": "An atmospheric, dreamy soundscape with pulsing synths and ethereal vocals",
        "genres": "Electronic, Ambient, Synthwave",
        "lyrics": "A journey through neon-lit streets, searching for connection",
        "artist_inspiration": "Tame Impala, The Weeknd, M83",
        "video_style": "Cyberpunk cityscape with neon reflections",
        "vocal_languages": "Instrumental",
    }
    return fallbacks.get(field, "Creative suggestion")

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
    
    return UserResponse(
        id=user.id,
        name=user.name,
        mobile=user.mobile,
        created_at=doc['created_at']
    )

@api_router.post("/auth/login", response_model=UserResponse)
async def login(login_data: UserLogin):
    user = await db.users.find_one({"mobile": login_data.mobile}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this mobile number. Please sign up first.")
    
    return UserResponse(
        id=user['id'],
        name=user['name'],
        mobile=user['mobile'],
        created_at=user['created_at']
    )

# ==================== AI Suggest Routes ====================

@api_router.post("/suggest")
async def ai_suggest(request: AISuggestRequest):
    suggestion = await get_ai_suggestion(request.field, request.current_value or "", request.context)
    return {"suggestion": suggestion, "field": request.field}

# ==================== Song Routes ====================

@api_router.post("/songs/create")
async def create_song(song_data: SongCreate):
    # Simulate music generation (mocked)
    song = Song(
        title=song_data.title or f"Untitled Track {random.randint(1000, 9999)}",
        music_prompt=song_data.music_prompt,
        genres=song_data.genres,
        duration_seconds=song_data.duration_seconds,
        vocal_languages=song_data.vocal_languages,
        lyrics=song_data.lyrics or "",
        artist_inspiration=song_data.artist_inspiration or "",
        generate_video=song_data.generate_video,
        video_style=song_data.video_style or "",
        audio_url=get_random_audio_url(),
        video_url="https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4" if song_data.generate_video else None,
        cover_art_url=get_random_cover_art(),
        album_id=song_data.album_id,
        user_id=song_data.user_id
    )
    
    doc = song.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.songs.insert_one(doc)
    
    return {
        "id": song.id,
        "title": song.title,
        "music_prompt": song.music_prompt,
        "genres": song.genres,
        "duration_seconds": song.duration_seconds,
        "vocal_languages": song.vocal_languages,
        "lyrics": song.lyrics,
        "artist_inspiration": song.artist_inspiration,
        "generate_video": song.generate_video,
        "video_style": song.video_style,
        "audio_url": song.audio_url,
        "video_url": song.video_url,
        "cover_art_url": song.cover_art_url,
        "album_id": song.album_id,
        "user_id": song.user_id,
        "created_at": doc['created_at']
    }

@api_router.get("/songs/user/{user_id}")
async def get_user_songs(user_id: str):
    songs = await db.songs.find({"user_id": user_id, "album_id": None}, {"_id": 0}).to_list(100)
    return songs

# ==================== Album Routes ====================

@api_router.post("/albums/create")
async def create_album(album_data: AlbumCreate):
    album = Album(
        title=album_data.title or f"Untitled Album {random.randint(1000, 9999)}",
        music_prompt=album_data.music_prompt,
        genres=album_data.genres,
        vocal_languages=album_data.vocal_languages,
        lyrics=album_data.lyrics or "",
        artist_inspiration=album_data.artist_inspiration or "",
        generate_video=album_data.generate_video,
        video_style=album_data.video_style or "",
        cover_art_url=get_random_cover_art(),
        user_id=album_data.user_id
    )
    
    doc = album.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.albums.insert_one(doc)
    
    # Generate songs for the album
    songs = []
    for i in range(album_data.num_songs):
        song = Song(
            title=f"{album.title} - Track {i + 1}",
            music_prompt=album_data.music_prompt,
            genres=album_data.genres,
            duration_seconds=random.randint(150, 300),
            vocal_languages=album_data.vocal_languages,
            lyrics=album_data.lyrics or "",
            artist_inspiration=album_data.artist_inspiration or "",
            generate_video=album_data.generate_video,
            video_style=album_data.video_style or "",
            audio_url=get_random_audio_url(),
            video_url="https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4" if album_data.generate_video else None,
            cover_art_url=album.cover_art_url,
            album_id=album.id,
            user_id=album_data.user_id
        )
        song_doc = song.model_dump()
        song_doc['created_at'] = song_doc['created_at'].isoformat()
        await db.songs.insert_one(song_doc)
        songs.append({
            "id": song.id,
            "title": song.title,
            "audio_url": song.audio_url,
            "video_url": song.video_url,
            "cover_art_url": song.cover_art_url,
            "duration_seconds": song.duration_seconds
        })
    
    return {
        "id": album.id,
        "title": album.title,
        "music_prompt": album.music_prompt,
        "genres": album.genres,
        "cover_art_url": album.cover_art_url,
        "user_id": album.user_id,
        "created_at": doc['created_at'],
        "songs": songs
    }

@api_router.get("/albums/user/{user_id}")
async def get_user_albums(user_id: str):
    albums = await db.albums.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    # Get songs for each album
    for album in albums:
        songs = await db.songs.find({"album_id": album['id']}, {"_id": 0}).to_list(50)
        album['songs'] = songs
    
    return albums

@api_router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    songs = await db.songs.find({"user_id": user_id, "album_id": None}, {"_id": 0}).to_list(100)
    albums = await db.albums.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    for album in albums:
        album_songs = await db.songs.find({"album_id": album['id']}, {"_id": 0}).to_list(50)
        album['songs'] = album_songs
    
    return {"songs": songs, "albums": albums}

# ==================== Genre List ====================

@api_router.get("/genres")
async def get_genres():
    return {
        "genres": [
            "Pop", "Rock", "Hip-Hop", "R&B", "Electronic", "Jazz", "Classical",
            "Country", "Reggae", "Blues", "Metal", "Folk", "Indie", "Soul",
            "Funk", "Disco", "House", "Techno", "Ambient", "Synthwave",
            "Lo-fi", "Trap", "Drill", "Afrobeats", "Latin", "K-Pop", "J-Pop",
            "World", "Experimental", "Cinematic", "Orchestral"
        ]
    }

@api_router.get("/languages")
async def get_languages():
    return {
        "languages": [
            "Instrumental", "English", "Spanish", "French", "German", "Italian",
            "Portuguese", "Japanese", "Korean", "Chinese", "Hindi", "Arabic",
            "Russian", "Swedish", "Dutch", "Turkish", "Greek", "Hebrew"
        ]
    }

# ==================== Health Check ====================

@api_router.get("/")
async def root():
    return {"message": "Muzify API is running"}

@api_router.get("/health")
async def health():
    return {"status": "healthy"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
