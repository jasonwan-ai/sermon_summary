#!/usr/bin/env python3
"""
Helper functions for file I/O and path operations.
"""

import json
from pathlib import Path
from datetime import datetime
from .typing import SermonSummary


def get_directories() -> tuple[Path, Path, Path]:
    """
    Get and initialize directory paths for the workflow.
    
    Returns:
        Tuple of (input_dir, temp_dir, output_dir) paths
    """
    datetime_str = datetime.now().strftime("%Y%m%d_%H%M") # 260114_0947 (date time to indicate trial runs)

    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    input_dir = project_root /  "input"
    temp_dir = project_root / "temp" / datetime_str
    output_dir = project_root / "output" /datetime_str
    
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


def save_summary(summary: SermonSummary, output_dir: Path, base_name: str,date: str) -> None:
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
            f.write(f"# Sermon Summary -- {date}\n\n")
            f.write(f"## Summary\n\n{summary.summary_markdown}\n\n")
            f.write("## Bible Verses\n\n")
            if summary.bible_verses:
                for verse in summary.bible_verses:
                    f.write(f"- **{verse.verse}** \n\t - {verse.reference}\n")
            else:
                f.write("No verses cited.\n")
        print(f"✓ Saved Markdown summary: {md_path}", flush=True)
    except IOError as e:
        raise IOError(f"Failed to save summary files for {base_name}: {e}") from e
