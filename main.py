from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import subprocess
import shutil

app = FastAPI()

# CORS setup to allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Welcome page at root
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
    <head><title>Vireon Downloader</title></head>
    <body style="text-align:center; font-family:sans-serif">
        <h1>✅ Vireon Downloader API is Live</h1>
        <p>Use the <code>/api/download</code> endpoint to fetch videos.</p>
    </body>
    </html>
    """

# POST endpoint to download video or audio
@app.post("/api/download")
async def download(request: Request):
    data = await request.json()
    url = data.get("url")
    format_type = data.get("format", "mp4")  # mp4, mp3, best

    if not url:
        return JSONResponse({"error": "URL not provided"}, status_code=400)

    temp_id = str(uuid.uuid4())
    out_file = f"{temp_id}.%(ext)s"
    output_template = os.path.join("downloads", out_file)

    # Choose yt-dlp options
    if format_type == "mp3":
        ytdlp_args = [
            "yt-dlp", "-x", "--audio-format", "mp3", "-o", output_template, url
        ]
    else:  # mp4 or best
        ytdlp_args = [
            "yt-dlp", "-f", "mp4", "-o", output_template, url
        ]

    os.makedirs("downloads", exist_ok=True)

    try:
        subprocess.run(ytdlp_args, check=True)
        # Find downloaded file
        downloaded_file = next(
            (os.path.join("downloads", f) for f in os.listdir("downloads") if temp_id in f), None
        )

        if not downloaded_file:
            return JSONResponse({"error": "Download failed"}, status_code=500)

        return {
            "filename": os.path.basename(downloaded_file),
            "download_url": f"/api/file/{os.path.basename(downloaded_file)}"
        }

    except subprocess.CalledProcessError:
        return JSONResponse({"error": "yt-dlp failed"}, status_code=500)


# Serve the downloaded file and delete after sending
@app.get("/api/file/{filename}")
async def get_file(filename: str):
    file_path = os.path.join("downloads", filename)
    if not os.path.exists(file_path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    def remove_file(file):
        try:
            os.remove(file)
        except:
            pass

    response = FileResponse(file_path, filename=filename)
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.call_on_close(lambda: remove_file(file_path))
    return response
