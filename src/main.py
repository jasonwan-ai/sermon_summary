#!/usr/bin/env python3
"""
Main entry point for sermon transcription and summarization workflow.

Processes all MKV files in the input/ directory, transcribes them,
and generates summaries using Gemini API.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from time import strftime

from .transcribe import transcribe_file
from .summarize import summarize_sermon
from .typing import SermonSummary


def get_directories() -> tuple[Path, Path, Path]:
    """
    Get and initialize directory paths for the workflow.
    
    Returns:
        Tuple of (input_dir, temp_dir, output_dir) paths
    """
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    input_dir = project_root / "input"
    temp_dir = project_root / "temp"
    output_dir = script_dir / "output"
    
    # Create temp_dir if it doesn't exist
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    return input_dir, temp_dir, output_dir


def get_transcript_path(temp_dir: Path, base_name: str) -> Path:
    """
    Get the expected transcript file path.
    
    We deduplicate by the first two parts of the filename:
    {year_month_day}_{time}_descrp.mkv -> {year_month_day}_{time}_transcript.txt
    
    Args:
        temp_dir: Temporary directory for transcripts
        base_name: Base filename (without extension)
    
    Returns:
        Path to the transcript file
    """
    parts = base_name.split("_")
    if len(parts) >= 2:
        identifier = f"{parts[0]}_{parts[1]}"
    else:
        identifier = base_name  # fallback when pattern is unexpected
    return temp_dir / f"{identifier}_transcript.txt"


def load_transcript(transcript_path: Path) -> str:
    """
    Load transcript from file.
    
    Args:
        transcript_path: Path to the transcript file
    
    Returns:
        Transcript text content
    
    Raises:
        FileNotFoundError: If transcript file doesn't exist
        IOError: If file cannot be read
    """
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript file not found: {transcript_path}")
    
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            return f.read()
    except IOError as e:
        raise IOError(f"Failed to read transcript file {transcript_path}: {e}") from e


def save_transcript(transcript: str, transcript_path: Path) -> None:
    """
    Save transcript to file.
    
    Args:
        transcript: Transcript text to save
        transcript_path: Path where to save the transcript
    
    Raises:
        IOError: If file cannot be written
    """
    try:
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)
    except IOError as e:
        raise IOError(f"Failed to save transcript to {transcript_path}: {e}") from e


def extract_date_from_filename(filename: str) -> str:
    """
    Extract and format date from filename.
    
    Expected format: {YYMMDD}_{time}_{description}.mkv
    Example: 260104_12-27_Afternoon.mkv -> "January 4, 2026"
    
    Args:
        filename: The filename (with or without extension)
    
    Returns:
        Formatted date string (e.g., "January 4, 2026")
    """
    base_name = Path(filename).stem
    parts = base_name.split("_")
    
    if not parts:
        return "Unknown Date"
    
    date_str = parts[0]
    
    # Parse YYMMDD format
    if len(date_str) == 6 and date_str.isdigit():
        try:
            year = 2000 + int(date_str[:2])  # Assume 20XX
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            
            date_obj = datetime(year, month, day)
            return date_obj.strftime("%B %d, %Y")
        except (ValueError, IndexError):
            pass
    
    return "Unknown Date"


def save_summary(summary: SermonSummary, output_dir: Path, base_name: str) -> None:
    """
    Save summary to JSON and markdown files.
    
    Args:
        summary: The SermonSummary object
        output_dir: Directory to save outputs
        base_name: Base filename (without extension)
    
    Raises:
        IOError: If files cannot be written
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Save JSON
        json_path = output_dir / f"{base_name}_summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"✓ Saved JSON summary: {json_path}", flush=True)
        
        # Save Markdown
        md_path = output_dir / f"{base_name}_summary.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Sermon Summary\n\n")
            f.write(f"## Summary\n\n{summary.summary_markdown}\n\n")
            f.write("## Bible Verses\n\n")
            if summary.bible_verses:
                for verse in summary.bible_verses:
                    f.write(f"- {verse}\n")
            else:
                f.write("No verses cited.\n")
        print(f"✓ Saved Markdown summary: {md_path}", flush=True)
    except IOError as e:
        raise IOError(f"Failed to save summary files for {base_name}: {e}") from e


def process_single_file(
    mkv_file: Path,
    input_dir: Path,
    temp_dir: Path,
    output_dir: Path,
) -> bool:
    """
    Process a single MKV file: transcribe (or load existing transcript) and summarize.
    
    Args:
        mkv_file: Path to the MKV file to process
        input_dir: Input directory path
        temp_dir: Temporary directory for transcripts
        output_dir: Output directory for summaries
    
    Returns:
        True if processing succeeded, False otherwise
    """
    start_time = datetime.now()
    print('Starting to process file: time now'+strftime(start_time))
    try:
        # Extract date from filename
        date = extract_date_from_filename(mkv_file.name)
        print(f"Extracted date: {date}\n", flush=True)
        
        # Get base name for file operations
        base_name = Path(mkv_file).stem
        transcript_path = get_transcript_path(temp_dir, base_name)
        
        # Step 1: Transcription (or load existing)
        print("Step 1: Transcription", flush=True)
        if transcript_path.exists():
            print(f"Found existing transcript at {transcript_path}, loading...", flush=True)
            transcript = load_transcript(transcript_path)
            language = "unknown"  # Language info not stored in transcript file
            print(f"✓ Loaded existing transcript (length: {len(transcript)} characters)\n", flush=True)
        else:
            print("No existing transcript found, transcribing...", flush=True)
            transcript, language = transcribe_file(str(mkv_file))
            print(f"Transcription complete. Language: {language}", flush=True)
            
            # Save transcript to temp directory
            save_transcript(transcript, transcript_path)
            print(f"✓ Saved transcript to: {transcript_path}\n", flush=True)
        
        # Step 2: Summarization
        print("Step 2: Summarization", flush=True)
        summary = summarize_sermon(transcript, date)
        print("Summarization complete.\n", flush=True)
        
        # Step 3: Save outputs
        print("Step 3: Saving outputs", flush=True)
        save_summary(summary, output_dir, base_name)
        
        print(f"\n✓ Successfully processed: {mkv_file.name}\n", flush=True)
        return True
    
    except FileNotFoundError as e:
        print(f"✗ File not found error processing {mkv_file.name}: {e}", file=sys.stderr, flush=True)
        return False
    except ValueError as e:
        print(f"✗ Configuration error processing {mkv_file.name}: {e}", file=sys.stderr, flush=True)
        return False
    except RuntimeError as e:
        print(f"✗ Runtime error processing {mkv_file.name}: {e}", file=sys.stderr, flush=True)
        return False
    except IOError as e:
        print(f"✗ I/O error processing {mkv_file.name}: {e}", file=sys.stderr, flush=True)
        return False
    except Exception as e:
        print(f"✗ Unexpected error processing {mkv_file.name}: {e}", file=sys.stderr, flush=True)
        return False


def main() -> int:
    """
    Main workflow function.
    
    Orchestrates the processing of all MKV files in the input directory.
    """
    # Get directories
    input_dir, temp_dir, output_dir = get_directories()
    
    # Validate input directory exists
    if not input_dir.exists():
        print(f"Error: input directory not found: {input_dir}", file=sys.stderr)
        return 1
    
    # Find all MKV files
    mkv_files = list(input_dir.glob("*.mkv"))
    
    if not mkv_files:
        print(f"No MKV files found in {input_dir}", file=sys.stderr)
        return 1
    
    print(f"Found {len(mkv_files)} MKV file(s) to process\n", flush=True)
    
    success_count = 0
    error_count = 0
    
    # Process each file
    for mkv_file in mkv_files:
        print(f"\n{'='*60}", flush=True)
        print(f"Processing: {mkv_file.name}", flush=True)
        print(f"{'='*60}\n", flush=True)
        
        if process_single_file(mkv_file, input_dir, temp_dir, output_dir):
            success_count += 1
        else:
            error_count += 1
    
    # Print summary
    print(f"\n{'='*60}", flush=True)
    print(f"Processing complete:", flush=True)
    print(f"  Success: {success_count}", flush=True)
    print(f"  Errors: {error_count}", flush=True)
    print(f"{'='*60}\n", flush=True)
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
