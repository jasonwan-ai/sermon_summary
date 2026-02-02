import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .io_helpers import APIKeyRotator
from .prompts import (
    SUMMARIZE_SYSTEM_PROMPT,
    SUMMARIZE_SUMMARY_PROMPT,
    EXTRACT_TIMESTAMP_PROMPT,
)
from .typing import SermonSummary, TimestampResponse

# Load environment variables
load_dotenv()

# Initialize key rotator
key_rotator = APIKeyRotator()

# @singleton client - will be recreated when keys are rotated
client = genai.Client(api_key=key_rotator.get_current_key())


def _is_transient_error(error: Exception) -> bool:
    msg = str(error).lower()
    transient_markers = (
        "503",
        "unavailable",
        "overloaded",
        "try again later",
        "rate limit",
        "temporarily",
    )
    return any(marker in msg for marker in transient_markers)


def _is_rate_limit_error(error: Exception) -> bool:
    """Check if the error is specifically a rate limit error."""
    msg = str(error).lower()
    return "rate limit" in msg or "429" in msg


def _call_gemini_with_retry(
    *,
    model: str,
    contents,
    config,
    action_label: str,
    max_attempts: int = 3,
    base_backoff: float = 2.0,
):
    global client

    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as e:
            is_rate_limited = _is_rate_limit_error(e)
            is_transient = _is_transient_error(e)

            # If rate limited, try rotating to a fallback key
            if (
                is_rate_limited
                and key_rotator.get_current_key_index()
                < key_rotator.get_total_keys() - 1
            ):
                try:
                    next_key = key_rotator.rotate_key()
                    client = genai.Client(api_key=next_key)
                    print(
                        f"Gemini {action_label} rate limited; retrying with fallback key...",
                        flush=True,
                    )
                    # Retry immediately with new key
                    continue
                except RuntimeError as rotate_error:
                    print(f"Key rotation failed: {rotate_error}", flush=True)
                    raise

            # For other transient errors, use backoff retry
            if not is_transient or attempt == max_attempts:
                raise

            sleep_time = base_backoff ** (attempt - 1)
            print(
                f"Gemini {action_label} request failed ({e}); retrying in {sleep_time:.1f}s [{attempt}/{max_attempts}]...",
                flush=True,
            )
            time.sleep(sleep_time)


def summarize_sermon(transcript: str, date: str) -> tuple[SermonSummary, int, int]:
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
    model = "gemini-2.5-flash"

    # Prepare prompts
    system_prompt = SUMMARIZE_SYSTEM_PROMPT
    user_prompt = SUMMARIZE_SUMMARY_PROMPT.format(transcript=transcript)

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

    # Log API call details
    print("Sending transcript to Gemini API for summarization...", flush=True)
    print(f"\n{'='*60}", flush=True)
    print(f"API Call Details - Summarization:", flush=True)
    print(f"  Model: {model}", flush=True)
    print(f"  System Prompt:", flush=True)
    print(f"  {system_prompt}", flush=True)
    print(
        f"  User Prompt Template (transcript length: {len(transcript)} characters):",
        flush=True,
    )
    prompt_parts = SUMMARIZE_SUMMARY_PROMPT.split("{transcript}")
    if len(prompt_parts) > 1:
        print(f"  {prompt_parts[0]}", flush=True)
        print(f"  [Transcript text - see above for full content]", flush=True)
        print(f"  {prompt_parts[1]}", flush=True)
    else:
        print(f"  {SUMMARIZE_SUMMARY_PROMPT}", flush=True)
    print(f"{'='*60}\n", flush=True)

    try:

        api_start = time.perf_counter()
        response = _call_gemini_with_retry(
            model=model,
            contents=contents,
            config=generate_content_config,
            action_label="summarization",
        )
        api_time = time.perf_counter() - api_start

        if not response.text:
            raise RuntimeError("Empty response from Gemini API")

        # Validate response using Pydantic model
        try:
            summary = SermonSummary.model_validate_json(response.text)
        except Exception as e:
            raise RuntimeError(
                f"Failed to validate JSON response from Gemini API: {e}\nResponse: {response.text}"
            )

        tokens_sent, tokens_received = 0, 0

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_sent = getattr(response.usage_metadata, "prompt_token_count", 0)
            tokens_received = getattr(
                response.usage_metadata, "candidates_token_count", 0
            )

        print("Summary generated successfully.", flush=True)
        print(f"  API call duration: {api_time:.2f} seconds", flush=True)
        print(f"  Tokens sent: {tokens_sent}", flush=True)
        print(f"  Tokens received: {tokens_received}", flush=True)

        return summary, tokens_sent, tokens_received

    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        if _is_transient_error(e):
            raise RuntimeError(
                f"Gemini API temporarily unavailable after retries: {e}"
            ) from e
        if _is_transient_error(e):
            raise RuntimeError(
                f"Gemini API temporarily unavailable after retries: {e}"
            ) from e
        raise RuntimeError(f"Error calling Gemini API: {e}") from e


def extract_timestamp(timestamp_text: str) -> tuple[TimestampResponse, int, int]:
    """
    Extract the start and end time of the sermon from the timestamp text.

    Args:
        timestamp_text: Text containing timestamped segments in format [start_time -> end_time] text

    Returns:
        TimestampResponse object with start_time and end_time in seconds

    Raises:
        RuntimeError: If API call fails or response cannot be parsed
    """
    model = "gemini-2.5-flash"

    # Prepare prompts
    system_prompt = EXTRACT_TIMESTAMP_PROMPT
    user_prompt = EXTRACT_TIMESTAMP_PROMPT.format(timestamp_text=timestamp_text)

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
        response_json_schema=TimestampResponse.model_json_schema(),
    )

    # Log API call details
    print(
        "Sending timestamp text to Gemini API for timestamp extraction...", flush=True
    )
    print(f"\n{'='*60}", flush=True)
    print(f"API Call Details - Timestamp Extraction:", flush=True)
    print(f"  Model: {model}", flush=True)
    print(f"  System Prompt:", flush=True)
    print(f"  {system_prompt}", flush=True)
    print(
        f"  User Prompt Template (timestamp text length: {len(timestamp_text)} characters):",
        flush=True,
    )
    prompt_parts = EXTRACT_TIMESTAMP_PROMPT.split("{timestamp_text}")
    if len(prompt_parts) > 1:
        print(f"  {prompt_parts[0]}", flush=True)
        print(f"  [Timestamp text - see above for full content]", flush=True)
        print(f"  {prompt_parts[1]}", flush=True)
    else:
        print(f"  {EXTRACT_TIMESTAMP_PROMPT}", flush=True)
    print(f"{'='*60}\n", flush=True)

    try:
        # Generate content with timing
        api_start = time.perf_counter()
        response = _call_gemini_with_retry(
            model=model,
            contents=contents,
            config=generate_content_config,
            action_label="timestamp extraction",
        )
        api_time = time.perf_counter() - api_start

        if not response.text:
            raise RuntimeError("Empty response from Gemini API")

        # Validate response using Pydantic model
        try:
            timestamp_response = TimestampResponse.model_validate_json(response.text)
        except Exception as e:
            raise RuntimeError(
                f"Failed to validate JSON response from Gemini API: {e}\nResponse: {response.text}"
            )

        # Log token usage and timing
        tokens_sent, tokens_received = 0, 0

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_sent = getattr(response.usage_metadata, "prompt_token_count", 0)
            tokens_received = getattr(
                response.usage_metadata, "candidates_token_count", 0
            )
        print("Timestamp extraction complete.", flush=True)
        print(f"  API call duration: {api_time:.2f} seconds", flush=True)
        print(f"  Tokens sent: {tokens_sent}", flush=True)
        print(f"  Tokens received: {tokens_received}", flush=True)
        print(
            f"  Sermon boundaries: {timestamp_response.start_time:.2f}s -> {timestamp_response.end_time:.2f}s, reason: {timestamp_response.reason}",
            flush=True,
        )

        return timestamp_response, tokens_sent, tokens_received

    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"Error calling Gemini API: {e}") from e
