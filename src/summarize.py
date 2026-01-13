import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .prompts import SYSTEM_PROMPT, USER_PROMPT
from .typing import SermonSummary

# Load environment variables
load_dotenv()


def summarize_sermon(transcript: str, date: str) -> SermonSummary:
    """
    Summarize a sermon transcript using Gemini API.
    
    Args:
        transcript: The full transcript text
        date: The date of the sermon service (e.g., "January 4, 2026")
    
    Returns:
        SermonSummary object with summary and bible verses
    
    Raises:
        ValueError: If GEMINI_API_KEY is not set
        RuntimeError: If API call fails or response cannot be parsed
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please create a .env file with your API key.")
    
    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-flash"
    
    # Prepare prompts
    system_prompt = SYSTEM_PROMPT
    user_prompt = USER_PROMPT.format(date=date, transcript=transcript)
    
    # Build request
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=user_prompt),
            ],
        ),
    ]
    
    # Configure generation with Pydantic schema
    generate_content_config = types.GenerateContentConfig(
        system_instruction=[
            types.Part.from_text(text=system_prompt),
        ],
        response_mime_type="application/json",
        response_json_schema=SermonSummary.model_json_schema(),
    )
    
    print("Sending transcript to Gemini API for summarization...", flush=True)
    
    try:
        # Generate content
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        
        if not response.text:
            raise RuntimeError("Empty response from Gemini API")
        
        # Validate response using Pydantic model
        try:
            summary = SermonSummary.model_validate_json(response.text)
        except Exception as e:
            raise RuntimeError(f"Failed to validate JSON response from Gemini API: {e}\nResponse: {response.text}")
        
        print("Summary generated successfully.", flush=True)
        return summary
    
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"Error calling Gemini API: {e}") from e
