import os
import sys
import json
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

# Configuration
DEFAULT_SKILLS = ["Communication", "Confidence", "Decision-making"]
DEFAULT_VIDEO_COUNT = int(os.getenv('DEFAULT_VIDEO_COUNT', '2'))
DEFAULT_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
DEFAULT_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.3'))

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
    """Extract weak areas from the report with focus on technical skills."""
    try:
        if not report_text.strip():
            print("Warning: Empty report text provided, using default skills")
            return ["Technical Interview Skills"] + DEFAULT_SKILLS
            
        prompt = """
        Analyze this interview report and identify specific technical areas that need improvement.
        Focus on programming languages, frameworks, and technical concepts mentioned.
        
        Report:
        {report_text}
        
        Return a JSON object with:
        {{
            "technical_skills": ["specific technical topics"],
            "soft_skills": ["other areas"]
        }}
        """.format(report_text=report_text)
        
        # First try with response_format for modern models
        try:
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=DEFAULT_TEMPERATURE,
                response_format={"type": "json_object"} if 'gpt-4' in DEFAULT_MODEL.lower() or 'gpt-3.5-turbo' in DEFAULT_MODEL.lower() else None
            )
        except Exception as e:
            if 'response_format' in str(e):
                # Retry without response_format if it's not supported
                response = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=DEFAULT_TEMPERATURE
                )
            else:
                raise

        raw = response.choices[0].message.content.strip()
        
        # Try to parse as JSON, fallback to extracting skills from text if needed
        try:
            # Clean the response
            if '```json' in raw:
                raw = raw.split('```json')[1].split('```')[0].strip()
            elif '```' in raw:
                raw = raw.split('```')[1].strip()
                
            result = json.loads(raw)
            
            # Extract both technical and soft skills
            technical_skills = result.get('technical_skills', [])
            soft_skills = result.get('soft_skills', [])
            
            # If no technical skills found, add a default one
            if not technical_skills:
                technical_skills = ["Technical Interview Skills"]
                
            # Combine them with technical skills first
            return technical_skills + soft_skills
            
        except (json.JSONDecodeError, AttributeError):
            # Fallback parsing if JSON parsing fails
            print("Warning: Could not parse response as JSON. Attempting to extract skills from text...")
            technical_skills = []
            soft_skills = []
            
            # Look for technical skills first
            for line in raw.split('\n'):
                line = line.lower().strip()
                if any(term in line for term in ['data struct', 'algorithm', 'system design', 'coding', 'programming', 'technical', 'computer science']):
                    skill = ' '.join(word.capitalize() for word in line.split())
                    if skill and skill not in technical_skills and len(skill) < 50:
                        technical_skills.append(skill)
            
            # If no technical skills found, add a default one
            if not technical_skills:
                technical_skills = ["Technical Interview Skills"]
                
            # Get other skills
            for line in raw.split('\n'):
                line = line.strip()
                if line and len(line) < 50 and line[0].isupper():
                    skill = line.split(':', 1)[0].strip()
                    if skill and skill not in technical_skills and skill not in soft_skills and len(skill) < 50:
                        soft_skills.append(skill)
                        
            return technical_skills + (soft_skills if soft_skills else DEFAULT_SKILLS)
        
    except Exception as e:
        print(f"Error extracting weak areas: {e}")
        raise Exception("Failed to extract weak areas from the report")

def search_youtube_videos(query: str, max_results: int = None, is_technical: bool = False) -> List[tuple]:
    """Search for YouTube videos based on a query, with special handling for technical content.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return. If None, uses DEFAULT_VIDEO_COUNT
        is_technical: Whether this is a technical skills search (affects search terms)
        
    Returns:
        List of tuples containing (video_title, video_url)
    """
    if not query or not query.strip():
        print("Error: Empty search query")
        return []
        
    max_results = max_results or DEFAULT_VIDEO_COUNT
    
    if not youtube:
        print("YouTube API not initialized. Please check your YOUTUBE_API_KEY in .env file.")
        return []
    
    try:
        # Enhance query for technical content
        enhanced_query = query.lower()
        if is_technical:
            # Add common technical interview terms if not already present
            tech_terms = ["interview", "interview preparation", "coding interview"]
            if not any(term in enhanced_query for term in tech_terms):
                enhanced_query = f"{enhanced_query} interview preparation"
        
        # Add tutorial/course terms for better results
        content_terms = ["tutorial", "course", "guide", "explained"]
        if not any(term in enhanced_query for term in content_terms):
            enhanced_query = f"{enhanced_query} tutorial"
        
        # Add duration filter for more in-depth content
        request = youtube.search().list(
            q=enhanced_query,
            part="snippet",
            type="video",
            maxResults=max(10, max_results * 2),  # Get more results to filter
            relevanceLanguage="en",
            safeSearch="moderate",
            videoDuration="medium",  # Prefer medium-length videos (4-20 mins)
            order="relevance"
        )
        
        response = request.execute()

        video_links = []
        seen_links = set()
        
        for item in response.get("items", []):
            try:
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]
                description = item["snippet"].get("description", "").lower()
                
                # Skip if we've seen this video already
                if video_id in seen_links:
                    continue
                
                # Skip if title contains unwanted terms
                skip_terms = ["part ", "episode ", "full course", "full tutorial"]
                if any(term in title.lower() for term in skip_terms):
                    continue
                
                # For technical content, prefer videos with code examples
                if is_technical and "code" not in description and "example" not in description:
                    continue
                
                link = f"https://www.youtube.com/watch?v={video_id}"
                video_links.append((title, link))
                seen_links.add(video_id)
                
                # Stop if we have enough results
                if len(video_links) >= max_results:
                    break
                    
            except (KeyError, IndexError) as e:
                print(f"Warning: Error processing video result: {e}")
                continue
        
        return video_links
        
    except HttpError as e:
        print(f"YouTube API error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error while searching YouTube: {e}")
        return []

def generate_video_recommendations(report_text: str, max_videos_per_skill: int = None) -> Dict[str, List[tuple]]:
    """Generate video recommendations based on the report with focus on technical content.
    
    Args:
        report_text: The interview analysis report text
        max_videos_per_skill: Maximum number of videos to return per skill. 
                            If None, uses DEFAULT_VIDEO_COUNT
                            
    Returns:
        Dictionary mapping skills to list of (video_title, video_url) tuples
    """
    if not report_text or not report_text.strip():
        raise ValueError("Report text cannot be empty")
        
    # Extract skills from the report
    skills = extract_weak_areas(report_text)
    if not skills:
        print("No skills found in the report, using default technical skills")
        skills = ["Technical Interview Skills"]
    
    # Separate technical and non-technical skills
    technical_skills = []
    soft_skills = []
    
    technical_terms = ['programming', 'coding', 'algorithm', 'data structure', 
                      'system design', 'technical', 'computer science', 'software']
    
    for skill in skills:
        if not skill or not skill.strip():
            continue
            
        skill_lower = skill.lower()
        if any(term in skill_lower for term in technical_terms):
            technical_skills.append(skill)
        else:
            soft_skills.append(skill)
    
    # If no technical skills found, add a default one
    if not technical_skills:
        technical_skills = ["Technical Interview Skills"]
    
    # Process technical skills first
    recommendations = {}
    
    # Get technical interview videos first
    for skill in technical_skills:
        query = f"{skill} interview preparation"
        results = search_youtube_videos(
            query, 
            max_results=max_videos_per_skill,
            is_technical=True
        )
        if results:
            recommendations[f"{skill} (Technical)"] = results
    
    # Then get soft skills videos if we have space
    max_soft_skills = min(3, len(soft_skills))  # Limit to top 3 soft skills
    for skill in soft_skills[:max_soft_skills]:
        query = f"{skill} for technical interviews"
        results = search_youtube_videos(
            query, 
            max_results=max(1, (max_videos_per_skill or DEFAULT_VIDEO_COUNT) // 2)
        )
        if results:
            recommendations[skill] = results
    
    return recommendations

def display_recommendations(recommendations: Dict[str, List[tuple]]) -> None:
    """Display the video recommendations in a user-friendly format.
    
    Args:
        recommendations: Dictionary mapping skills to list of (title, url) tuples
    """
    if not recommendations:
        print("No video recommendations available.")
        return
        
    print("🎯 Video Recommendations\n" + "="*50)
    
    for skill, videos in recommendations.items():
        if not videos:
            continue
            
        print(f"\n📘 Skill Area: {skill}")
        for i, (title, url) in enumerate(videos, 1):
            print(f"{i}. {title}")
            print(f"   🔗 {url}")


def get_report_from_stdin() -> str:
    """Read report text from standard input."""
    print("\nPlease paste the interview report (press Ctrl+Z then Enter when finished):\n")
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass  # Ctrl+Z was pressed
    
    report_text = '\n'.join(lines).strip()
    if not report_text:
        print("No report text provided. Using default skills for recommendations.")
    return report_text


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate YouTube video recommendations based on interview feedback.')
    parser.add_argument('--report', type=str, help='Path to a text file containing the interview report')
    parser.add_argument('--max-videos', type=int, default=None, 
                       help=f'Maximum number of videos per skill (default: {DEFAULT_VIDEO_COUNT})')
    parser.add_argument('--interactive', action='store_true',
                      help='Enable interactive mode to enter report text directly')
    
    args = parser.parse_args()
    
    try:
        # Get report text from file, stdin, or use default skills
        if args.report:
            try:
                with open(args.report, 'r', encoding='utf-8') as f:
                    report_text = f.read()
            except Exception as e:
                print(f"Error reading report file: {e}")
                return
        elif args.interactive or not sys.stdin.isatty():
            report_text = get_report_from_stdin()
        else:
            print("No report provided. Using default skills for recommendations.")
            report_text = ""
        
        # Generate and display recommendations
        recommendations = generate_video_recommendations(
            report_text, 
            max_videos_per_skill=args.max_videos
        )
        
        display_recommendations(recommendations)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nPlease check the report text and try again.")


# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Add a simple route for testing
@app.route('/')
def home():
    return "YouTube Video Recommendations API is running!"

@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    """API endpoint to get video recommendations for a given report."""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data or 'report' not in data:
            return jsonify({
                'error': 'Missing required field: report',
                'status': 'error'
            }), 400
        
        # Get max_videos parameter if provided
        max_videos = data.get('max_videos')
        
        # Generate recommendations
        recommendations = generate_video_recommendations(
            data['report'],
            max_videos_per_skill=max_videos
        )
        
        # Format the response
        response = {
            'status': 'success',
            'recommendations': [
                {
                    'skill': skill,
                    'videos': [{'title': title, 'url': url} for title, url in videos]
                }
                for skill, videos in recommendations.items()
            ]
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'youtube-recommendations',
        'version': '1.0.0'
    }), 200

def run_web_server(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask web server."""
    port = int(os.environ.get('PORT', port))
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    # If no command line arguments, run the web server
    if len(sys.argv) == 1:
        print("Starting web server...")
        print(f"API available at: http://localhost:5000/api/recommendations")
        print("Send a POST request with JSON body: {\"report\": \"your report text...\"}")
        run_web_server()
    else:
        # Run the command line interface
        main()
