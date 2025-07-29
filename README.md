# Skill Improvement Video Recommender

A FastAPI application that analyzes skill assessment reports and recommends relevant YouTube videos for skill improvement.

## Features

- Analyzes skill assessment reports to identify areas for improvement
- Recommends relevant YouTube videos for each skill area
- RESTful API for easy integration with frontend applications

## Prerequisites

- Python 3.9+
- OpenAI API key
- YouTube Data API v3 key

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd skill-improvement-recommender
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory and add your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   YOUTUBE_API_KEY=your_youtube_api_key
   ```

## Running Locally

1. Start the FastAPI server:
   ```bash
   uvicorn app:app --reload
   ```

2. The API will be available at `http://localhost:8000`

## API Endpoints

### POST /recommend-videos/

Analyzes a skill assessment report and returns recommended YouTube videos.

**Request Body:**
```json
{
  "report_text": "[Your skill assessment report text]"
}
```

**Response:**
```json
[
  {
    "skill": "Communication",
    "videos": [
      {
        "title": "Improving Communication Skills - Sample",
        "url": "https://www.youtube.com/watch?v=example1"
      },
      {
        "title": "Effective Communication Techniques - Sample",
        "url": "https://www.youtube.com/watch?v=example2"
      }
    ]
  }
]
```

## Deployment to Render

1. Push your code to a GitHub repository
2. Sign up for a Render account at https://render.com/
3. Click "New" and select "Web Service"
4. Connect your GitHub repository
5. Configure the following settings:
   - Name: `skill-improvement-recommender`
   - Region: Choose the one closest to your users
   - Branch: `main` or your preferred branch
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
6. Add environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `YOUTUBE_API_KEY`: Your YouTube Data API v3 key
7. Click "Create Web Service"

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `YOUTUBE_API_KEY` | Your YouTube Data API v3 key | No (but recommended) |

## License

MIT
