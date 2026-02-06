#!/usr/bin/env python3
"""
Main entry point for sermon transcription and summarization workflow.

Processes all MKV and MP4 files in the input/ directory, transcribes them,
and generates summaries using Gemini API.
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

from .transcribe import transcribe_wav_file, run_ffmpeg_crop_wav, run_ffmpeg_extract_wav
from .summarize import summarize_sermon, extract_timestamp
from .io_helpers import (
    get_directories,
    get_tiny_transcript_path,
    get_tiny_timestamp_path,
    get_medium_transcript_path,
    load_transcript,
    load_text,
    save_transcript,
    save_text,
    save_summary,
)
from .formatters import format_duration, extract_date_from_filename


def _is_gemini_unavailable(error: Exception) -> bool:
    msg = str(error).lower()
    return "gemini" in msg and (
        "503" in msg or "unavailable" in msg or "overloaded" in msg
    )


def convert_video(video_file: Path, base_name: str) -> tuple[str, str, float]:
    """
    Extract audio from video file.

    Args:
        video_file: Path to the video file (MKV or MP4)
        base_name: Base filename (without extension)

    Returns:
        Tuple of (wav_path, cropped_wav_path, extract_time)
    """
    print("Step 0: Extracting audio from video file", flush=True)
    input_dir = os.path.dirname(str(video_file))
    wav_path = os.path.join(input_dir, base_name + "_audio.wav")
    cropped_wav_path = os.path.join(input_dir, base_name + "_cropped_audio.wav")

    extract_start = time.perf_counter()
    run_ffmpeg_extract_wav(str(video_file), wav_path)
    extract_time = time.perf_counter() - extract_start
    print(f"Audio extracted. (Time: {extract_time:.2f} seconds)\n", flush=True)

    return wav_path, cropped_wav_path, extract_time


def get_or_load_transcript(
    wav_path: str,
    cropped_wav_path: str,
    temp_dir: Path,
    base_name: str,
) -> tuple[str, dict[str, float], dict[str, float], int, int]:
    """
    Get transcript by loading existing file or performing two-pass transcription.

    Args:
        wav_path: Path to the full audio WAV file
        cropped_wav_path: Path where cropped WAV will be saved
        temp_dir: Temporary directory for transcripts
        base_name: Base filename (without extension)

    Returns:
        Tuple of (transcript, transcription_times, api_times, total_tokens_sent, total_tokens_received)
    """
    transcription_times = {"tiny": 0.0, "medium": 0.0}
    api_times = {"timestamp": 0.0, "summary": 0.0}
    total_tokens_sent = 0
    total_tokens_received = 0

    tiny_transcript_path = get_tiny_transcript_path(temp_dir, base_name)
    tiny_timestamp_path = get_tiny_timestamp_path(temp_dir, base_name)
    medium_transcript_path = get_medium_transcript_path(temp_dir, base_name)

    # Check if medium transcript already exists
    if medium_transcript_path.exists():
        print("Step 1: Loading cached medium transcript", flush=True)
        transcript = load_transcript(medium_transcript_path)
        print(f"✓ Loaded transcript from: {medium_transcript_path}\n", flush=True)
        return (
            transcript,
            transcription_times,
            api_times,
            total_tokens_sent,
            total_tokens_received,
        )

    # Step 1: First pass with tiny model (or load cached)
    if tiny_transcript_path.exists() and tiny_timestamp_path.exists():
        print("Step 1: Loading cached tiny transcript and timestamps", flush=True)
        first_pass_transcript = load_transcript(tiny_transcript_path)
        timestamp_text = load_text(tiny_timestamp_path)
        print(f"✓ Loaded tiny transcript from: {tiny_transcript_path}", flush=True)
        print(f"✓ Loaded tiny timestamps from: {tiny_timestamp_path}\n", flush=True)
    else:
        print("Step 1: First pass transcription (tiny model)", flush=True)
        tiny_start = time.perf_counter()
        first_pass_transcript, timestamp_text = transcribe_wav_file(
            wav_path, model_size="tiny", language="id", clear_model_after=True
        )
        transcription_times["tiny"] = time.perf_counter() - tiny_start
        print(
            f"First pass transcription (tiny model): {transcription_times['tiny']:.2f} seconds\n",
            flush=True,
        )
        save_transcript(first_pass_transcript, tiny_transcript_path)
        save_text(timestamp_text, tiny_timestamp_path)
        print(f"✓ Saved tiny transcript to: {tiny_transcript_path}", flush=True)
        print(f"✓ Saved tiny timestamps to: {tiny_timestamp_path}\n", flush=True)

    # Step 2: Extract sermon timestamps using LLM
    print("Step 2: Extracting sermon boundaries", flush=True)
    timestamp_start = time.perf_counter()
    timestamp_response, ts_tokens_sent, ts_tokens_received = extract_timestamp(
        timestamp_text
    )
    api_times["timestamp"] = time.perf_counter() - timestamp_start
    total_tokens_sent += ts_tokens_sent
    total_tokens_received += ts_tokens_received
    print(
        f"Timestamp extraction API call: {api_times['timestamp']:.2f} seconds\n",
        flush=True,
    )

    # Step 3: Crop WAV file
    print("Step 3: Cropping audio to sermon portion", flush=True)
    crop_start = time.perf_counter()
    run_ffmpeg_crop_wav(
        wav_path,
        cropped_wav_path,
        timestamp_response.start_time,
        timestamp_response.end_time,
    )
    crop_time = time.perf_counter() - crop_start
    print(f"Audio cropping: {crop_time:.2f} seconds\n", flush=True)

    # Step 4: Second pass with medium model on cropped audio
    print("Step 4: Second pass transcription (medium model)", flush=True)
    medium_start = time.perf_counter()
    transcript, _ = transcribe_wav_file(
        cropped_wav_path, model_size="medium", clear_model_after=True
    )
    transcription_times["medium"] = time.perf_counter() - medium_start
    print(
        f"Second pass transcription (medium model): {transcription_times['medium']:.2f} seconds\n",
        flush=True,
    )

    # Save medium transcript to temp directory
    save_transcript(transcript, medium_transcript_path)
    print(f"✓ Saved transcript to: {medium_transcript_path}\n", flush=True)

    return (
        transcript,
        transcription_times,
        api_times,
        total_tokens_sent,
        total_tokens_received,
    )


def summarize_and_save(
    transcript: str,
    date: str,
    output_dir: Path,
    base_name: str,
) -> tuple[dict[str, float], int, int]:
    """
    Summarize transcript and save outputs.

    Args:
        transcript: The transcript text to summarize
        date: The date of the sermon service
        output_dir: Output directory for summaries
        base_name: Base filename (without extension)

    Returns:
        Tuple of (api_times, total_tokens_sent, total_tokens_received)
    """
    api_times = {"summary": 0.0}

    # Step 5: Summarize the final transcript
    print("Step 5: Summarization", flush=True)
    summary_start = time.perf_counter()
    summary, sum_tokens_sent, sum_tokens_received = summarize_sermon(transcript, date)
    api_times["summary"] = time.perf_counter() - summary_start
    print(f"Summarization API call: {api_times['summary']:.2f} seconds\n", flush=True)

    # Step 6: Save outputs
    print("Step 6: Saving outputs", flush=True)
    save_summary(summary, output_dir, base_name, date)

    return api_times, sum_tokens_sent, sum_tokens_received


def process_single_file(
    video_file: Path,
    input_dir: Path,
    temp_dir: Path,
    output_dir: Path,
) -> bool:
    """
    Process a single video file: transcribe (or load existing transcript) and summarize.

    Args:
        video_file: Path to the video file (MKV or MP4) to process
        input_dir: Input directory path
        temp_dir: Temporary directory for transcripts
        output_dir: Output directory for summaries

    Returns:
        True if processing succeeded, False otherwise
    """
    start_time = datetime.now()
    overall_start = time.perf_counter()
    print(
        f'Starting to process file: {start_time.strftime("%Y-%m-%d %H:%M:%S")}',
        flush=True,
    )

    wav_path = None
    cropped_wav_path = None

    try:
        # Extract date from filename
        date = extract_date_from_filename(video_file.name)
        print(f"Extracted date: {date}\n", flush=True)

        base_name = Path(video_file).stem

        wav_path, cropped_wav_path, extract_time = convert_video(video_file, base_name)

        (
            transcript,
            transcription_times,
            api_times,
            total_tokens_sent,
            total_tokens_received,
        ) = get_or_load_transcript(wav_path, cropped_wav_path, temp_dir, base_name)

        summary_api_times, sum_tokens_sent, sum_tokens_received = summarize_and_save(
            transcript, date, output_dir, base_name
        )

        api_times["summary"] = summary_api_times["summary"]
        total_tokens_sent += sum_tokens_sent
        total_tokens_received += sum_tokens_received

        # Calculate and log processing time summary
        end_time = datetime.now()
        overall_time = time.perf_counter() - overall_start
        duration_str = format_duration(start_time, end_time)

        total_transcription_time = (
            transcription_times["tiny"] + transcription_times["medium"]
        )
        total_api_time = api_times.get("timestamp", 0.0) + api_times["summary"]

        print(f"\n{'='*60}", flush=True)
        print(f"✓ Successfully processed: {video_file.name}", flush=True)
        print(f"  Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        print(f"  End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        print(f"  Processing time: {duration_str}", flush=True)
        print(f"\nTotal processing summary:", flush=True)
        print(f"  Video extraction time: {extract_time:.2f} seconds", flush=True)
        print(
            f"  Transcription time: {total_transcription_time:.2f} seconds (tiny: {transcription_times['tiny']:.2f}s, medium: {transcription_times['medium']:.2f}s)",
            flush=True,
        )
        print(
            f"  API call time: {total_api_time:.2f} seconds (timestamp: {api_times.get('timestamp', 0.0):.2f}s, summary: {api_times['summary']:.2f}s)",
            flush=True,
        )
        print(f"  Total tokens sent: {total_tokens_sent}", flush=True)
        print(f"  Total tokens received: {total_tokens_received}", flush=True)
        print(f"  Total processing time: {overall_time:.2f} seconds", flush=True)
        print(f"{'='*60}\n", flush=True)
        return True

    except FileNotFoundError as e:
        end_time = datetime.now()
        duration_str = format_duration(start_time, end_time)
        print(
            f"✗ File not found error processing {video_file.name}: {e}",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"  Processing time before error: {duration_str}",
            file=sys.stderr,
            flush=True,
        )
        return False

    except Exception as e:
        end_time = datetime.now()
        duration_str = format_duration(start_time, end_time)
        if _is_gemini_unavailable(e):
            print(
                f"✗ Gemini service temporarily unavailable while processing {video_file.name}: {e}",
                file=sys.stderr,
                flush=True,
            )
            print(
                "  This is likely transient. Retry this file later once the API recovers.",
                file=sys.stderr,
                flush=True,
            )
        else:
            print(
                f"✗ Unexpected error processing {video_file.name}: {e}",
                file=sys.stderr,
                flush=True,
            )
        print(
            f"  Processing time before error: {duration_str}",
            file=sys.stderr,
            flush=True,
        )
        return False

    finally:
        # Clean up temporary WAV files
        try:
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
            if cropped_wav_path and os.path.exists(cropped_wav_path):
                os.remove(cropped_wav_path)
        except OSError:
            pass


def main() -> int:
    """
    Main workflow function.

    Orchestrates the processing of all video files in the input directory.
    """
    # Get directories
    input_dir, temp_dir, output_dir = get_directories()

    # Validate input directory exists
    if not input_dir.exists():
        print(f"Error: input directory not found: {input_dir}", file=sys.stderr)
        return 1

    video_files = sorted(list(input_dir.glob("*.mkv")) + list(input_dir.glob("*.mp4")))

    if not video_files:
        print(f"No MKV or MP4 files found in {input_dir}", file=sys.stderr)
        return 1

    print(f"Found {len(video_files)} video file(s) to process\n", flush=True)

    success_count, error_count = 0, 0

    for video_file in video_files:
        print(f"\n{'='*60}", flush=True)
        print(f"Processing: {video_file.name}", flush=True)
        print(f"{'='*60}\n", flush=True)

        if process_single_file(video_file, input_dir, temp_dir, output_dir):
            success_count += 1
        else:
            error_count += 1

    print(f"\n{'='*60}", flush=True)
    print(f"Processing complete:", flush=True)
    print(f"  Success: {success_count}", flush=True)
    print(f"  Errors: {error_count}", flush=True)
    print(f"{'='*60}\n", flush=True)

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
