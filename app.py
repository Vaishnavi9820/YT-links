import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Tuple
from main import extract_weak_areas, search_youtube_videos, generate_video_recommendations

app = FastAPI(title="Skill Improvement Video Recommender",
             description="API to get YouTube video recommendations based on skill assessment reports")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ReportRequest(BaseModel):
    report_text: str

class VideoRecommendation(BaseModel):
    skill: str
    videos: List[Dict[str, str]]

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Skill Improvement Video Recommender API"}

@app.post("/recommend-videos/", response_model=List[VideoRecommendation])
async def recommend_videos(request: ReportRequest):
    try:
        # Generate recommendations using the existing functions
        recommendations = generate_video_recommendations(request.report_text)
        
        # Format the response
        response = []
        for skill, videos in recommendations.items():
            video_list = [{"title": title, "url": url} for title, url in videos]
            response.append({
                "skill": skill,
                "videos": video_list
            })
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
