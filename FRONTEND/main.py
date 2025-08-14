import os
import requests
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

app = FastAPI()

# Serve static files from the root directory
app.mount("/", StaticFiles(directory="."), name="static")

@app.get("/")
async def root():
    return FileResponse("index.html")

@app.get("/analysis")
async def analysis_page():
    return FileResponse("public/analysis.html")

@app.post("/upload")
async def upload_and_analyze(
    image1: UploadFile = File(...),
    image2: UploadFile = File(...)
):
    try:
        # 1️⃣ Upload images to Cloudinary
        upload_1 = cloudinary.uploader.upload(image1.file)
        upload_2 = cloudinary.uploader.upload(image2.file)

        # Extract URLs
        image_a_url = upload_1["secure_url"]
        image_b_url = upload_2["secure_url"]

        # 2️⃣ Call /process_urls
        process_payload = {
            "image_a_url": image_a_url,
            "image_b_url": image_b_url
        }
        process_resp = requests.post("https://api.nansat.tech/process_urls", json=process_payload)
        if process_resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Process URLs failed: {process_resp.text}")
        process_data = process_resp.json()

        # 3️⃣ Call /analyze
        analyze_payload = {
            "image_a_url": process_data["image_a_url"],
            "image_b_url": process_data["image_b_url"],
            "change_mask_url": process_data["result_url"]
        }
        analyze_resp = requests.post("https://api.nansat.tech/analyze", json=analyze_payload)
        if analyze_resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Analyze failed: {analyze_resp.text}")
        analysis_data = analyze_resp.json()

        # 4️⃣ Return the final analysis JSON to frontend
        return JSONResponse(content=analysis_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Optional SPA fallback
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    return FileResponse("public/index.html")