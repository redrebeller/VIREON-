from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import os
import uuid

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class DownloadRequest(BaseModel):
    url: str
    format: str = "best"

@app.post("/api/download")
async def download_video(request: DownloadRequest):
    uid = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{uid}.%(ext)s")

    ydl_opts = {
        'format': request.format,
        'outtmpl': output_template,
        'quiet': True,
        'noplaylist': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(request.url, download=True)
        ext = info.get('ext', 'mp4')
        filename = f"{uid}.{ext}"

    return {
        "title": info.get("title"),
        "filename": filename,
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "url": f"/api/file/{filename}"
    }

def delete_file_after_send(path: str):
    try:
        os.remove(path)
    except Exception as e:
        print(f"Error deleting file: {e}")

@app.get("/api/file/{filename}")
async def serve_file(filename: str, background_tasks: BackgroundTasks):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    
    background_tasks.add_task(delete_file_after_send, file_path)
    return FileResponse(file_path, filename=filename, media_type='application/octet-stream')
