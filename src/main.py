#!/usr/bin/env python3
"""
Main entry point for sermon transcription and summarization workflow.

Processes all MKV files in the input/ directory, transcribes them,
and generates summaries using Gemini API.
"""

import sys
from pathlib import Path
from datetime import datetime

from .transcribe import transcribe_file
from .summarize import summarize_sermon
from .io_helpers import (
    get_directories,
    get_transcript_path,
    load_transcript,
    save_transcript,
    save_summary,
)
from .formatters import format_duration, extract_date_from_filename

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
    print(f'Starting to process file: {start_time.strftime("%Y-%m-%d %H:%M:%S")}', flush=True)
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

            print(f"✓ Loaded existing transcript (length: {len(transcript)} characters)\n", flush=True)
        else:
            print("No existing transcript found, transcribing...", flush=True)
            transcript, _ = transcribe_file(str(mkv_file))
            print(f"Transcription complete. ",flush=True)
            
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
        
        # Calculate and log processing time
        end_time = datetime.now()
        duration_str = format_duration(start_time, end_time)
        
        print(f"\n✓ Successfully processed: {mkv_file.name}", flush=True)
        print(f"  Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        print(f"  End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        print(f"  Processing time: {duration_str}\n", flush=True)
        return True
    
    except FileNotFoundError as e:
        end_time = datetime.now()
        duration_str = format_duration(start_time, end_time)
        print(f"✗ File not found error processing {mkv_file.name}: {e}", file=sys.stderr, flush=True)
        print(f"  Processing time before error: {duration_str}", file=sys.stderr, flush=True)
        return False
  
    except Exception as e:
        end_time = datetime.now()
        duration_str = format_duration(start_time, end_time)
        print(f"✗ Unexpected error processing {mkv_file.name}: {e}", file=sys.stderr, flush=True)
        print(f"  Processing time before error: {duration_str}", file=sys.stderr, flush=True)
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
    
    mkv_files = list(input_dir.glob("*.mkv"))
    
    if not mkv_files:
        print(f"No MKV files found in {input_dir}", file=sys.stderr)
        return 1
    
    print(f"Found {len(mkv_files)} MKV file(s) to process\n", flush=True)
    
    success_count,error_count = 0,0
    
    for mkv_file in mkv_files:
        print(f"\n{'='*60}", flush=True)
        print(f"Processing: {mkv_file.name}", flush=True)
        print(f"{'='*60}\n", flush=True)
        
        if process_single_file(mkv_file, input_dir, temp_dir, output_dir):
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
