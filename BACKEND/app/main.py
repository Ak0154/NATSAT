import os
import requests
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from app.models import User 

from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.models import User
from app.schemas import UserCreate, UserPublic, Token
from app.services import get_user_by_email, create_user
from app.auth import create_access_token, verify_password, get_current_user

# Load environment variables from .env file
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# Initialize FastAPI app
app = FastAPI(title="NANSAT")

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from "public" only if the directory exists
if os.path.isdir("public"):
    app.mount("/public", StaticFiles(directory="public"), name="public")


# --- Startup & Shutdown Events ---
@app.on_event("startup")
async def app_init():
    """Initializes the MongoDB connection and Beanie models."""
    db_client = AsyncIOMotorClient(os.getenv("DATABASE_URL"))
    app.mongodb_client = db_client  # Store client for shutdown
    await init_beanie(
        database=db_client.get_database("nansat_db"),
        document_models=[User]
    )
    print("MongoDB connection initialized and Beanie models loaded.")


@app.on_event("shutdown")
async def app_shutdown():
    """Closes the MongoDB client connection."""
    if hasattr(app, "mongodb_client"):
        app.mongodb_client.close()
    print("MongoDB connection closed.")


# --- Auth & User Routes ---
@app.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """Register a new user."""
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    new_user = await create_user(user_data)
    return UserPublic(
        id=str(new_user.id),
        name=new_user.name,
        email=new_user.email,
        created_at=new_user.created_at
    )


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate a user and return a JWT token."""
    user = await get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return Token(access_token=access_token, token_type="bearer")


@app.get("/users/me", response_model=UserPublic)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get details of the current authenticated user."""
    return UserPublic(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        created_at=current_user.created_at
    )


# --- Root Route ---
@app.get("/")
async def root():
    return FileResponse("public/index.html")


# --- Upload & Analysis ---
@app.post("/upload")
async def upload_and_analyze(
    image1: UploadFile = File(...),
    image2: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    try:
        # Upload images to Cloudinary
        upload_1 = cloudinary.uploader.upload(image1.file)
        upload_2 = cloudinary.uploader.upload(image2.file)

        image_a_url = upload_1["secure_url"]
        image_b_url = upload_2["secure_url"]

        # Call /process_urls
        process_payload = {
            "image_a_url": image_a_url,
            "image_b_url": image_b_url
        }
        process_resp = requests.post("https://api.nansat.tech/process_urls", json=process_payload)
        if process_resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Process URLs failed: {process_resp.text}")
        process_data = process_resp.json()

        # Call /analyze
        analyze_payload = {
            "image_a_url": process_data["image_a_url"],
            "image_b_url": process_data["image_b_url"],
            "change_mask_url": process_data["result_url"]
        }
        analyze_resp = requests.post("https://api.nansat.tech/analyze", json=analyze_payload)
        if analyze_resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Analyze failed: {analyze_resp.text}")
        analysis_data = analyze_resp.json()

        return JSONResponse(content=analysis_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- SPA Fallback ---
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    return FileResponse("public/index.html")
