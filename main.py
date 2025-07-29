import os
import json
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize YouTube API
youtube = None
if os.getenv('YOUTUBE_API_KEY'):
    try:
        youtube = build("youtube", "v3", developerKey=os.getenv('YOUTUBE_API_KEY'))
    except Exception as e:
        print(f"Warning: Failed to initialize YouTube API: {e}")

def extract_weak_areas(report_text: str) -> List[str]:
    """Extract weak areas from the report using OpenAI's API."""
    try:
        prompt = """
        You are a smart AI. Given the interview analysis report below, extract the top 3-5 skill areas 
        the user needs to improve, focusing only on areas with low scores or weaknesses. 
        Return them as a valid JSON array of strings.

        Report:
        {report_text}
        
        Response format (JSON):
        {{
            "skills": ["skill1", "skill2", "skill3"]
        }}
        """.format(report_text=report_text)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)
        return result.get("skills", ["Communication", "Confidence", "Decision-making"])
        
    except Exception as e:
        print(f"Error extracting weak areas: {e}")
        return ["Communication", "Confidence", "Decision-making"]  # fallback

def search_youtube_videos(query: str, max_results: int = 2) -> List[tuple]:
    """Search for YouTube videos based on a query."""
    if not youtube:
        print("YouTube API not initialized. Returning sample data.")
        # Return sample data if YouTube API is not available
        return [
            (f"{query} - Sample Video 1", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            (f"{query} - Sample Video 2", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        ]
    
    try:
        request = youtube.search().list(
            q=f"{query} tutorial",
            part="snippet",
            type="video",
            maxResults=max_results,
            relevanceLanguage="en",
            safeSearch="moderate"
        )
        response = request.execute()

        video_links = []
        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            link = f"https://www.youtube.com/watch?v={video_id}"
            video_links.append((title, link))
        
        return video_links
        
    except HttpError as e:
        print(f"YouTube API error: {e}")
        # Return sample data if there's an error
        return [
            (f"{query} - Sample Video 1", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            (f"{query} - Sample Video 2", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        ]

def generate_video_recommendations(report_text: str) -> Dict[str, List[tuple]]:
    """Generate video recommendations based on the report."""
    try:
        skills = extract_weak_areas(report_text)
        recommendations = {}

        for skill in skills:
            query = f"{skill} improvement for interviews"
            results = search_youtube_videos(query, max_results=2)
            recommendations[skill] = results

        return recommendations
        
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        # Return a default recommendation in case of error
        return {
            "Communication": [
                ("Improving Communication Skills - Sample", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            ]
        }

# Example Report Input
report = """Scoring:

Technical Proficiency: 2/10
Communication: 1/10
Decision-making: 1/10
Confidence: 1/10
Language Fluency: 2/10
Overall: 7/50
Analysis:

Technical proficiency: The user provided limited information about their technical skills. They mentioned having experience with Java, but did not elaborate on other skills or provide specific examples of how they used their skills in past projects.

For improvement, the user can refer to these resources:

Book: "The Complete Software Developer's Career Guide" by John Sonmez
YouTube: Traversy Media for learning about multiple coding languages and technologies
Website: Codecademy, LeetCode for practice
Communication: The answers provided were incomplete and did not fully address the questions asked. In many cases, the user did not provide any answer at all.

For improvement, the user can refer to these resources:

Book: "How to Win Friends and Influence People" by Dale Carnegie
YouTube: Amy Cuddy's TED talk on body language and communication
Website: Coursera offers courses on communication skills
Decision-making: The user did not provide enough information to evaluate their decision-making skills.

For improvement, the user can refer to these resources:

Book: "Thinking, Fast and Slow" by Daniel Kahneman
YouTube: Brian Tracy's videos on decision-making
Website: Lynda.com offers courses on decision-making in the business context
Confidence: The user did not display confidence in their responses. Many of the answers were incomplete or not given at all.

For improvement, the user can refer to these resources:

Book: "The Confidence Code" by Katty Kay and Claire Shipman
YouTube: Tony Robbins' videos on confidence and personal growth
Website: TED Talks offer many presentations on confidence and self-improvement
Language Fluency: The user demonstrated basic language fluency, though their responses were very brief and lacked detail.

For improvement, the user can refer to these resources:

Book: "Fluent Forever" by Gabriel Wyner
YouTube: English Lessons with Adam - Learn English [engVid]
Website: Duolingo, Rosetta Stone for improving language proficiency
Overall, the user needs significant improvement in all areas. They should focus on developing their technical skills, improving their communication and decision-making abilities, building confidence, and enhancing their language fluency. They are encouraged to use the resources suggested for self-improvement.
"""

# Run the recommender
videos = generate_video_recommendations(report)

# Display Results
for skill, links in videos.items():
    print(f"\n📘 Skill Area: {skill}")
    for title, url in links:
        print(f"🔗 {title}: {url}")
