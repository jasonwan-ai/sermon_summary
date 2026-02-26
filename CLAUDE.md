# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based automated sermon transcription and summarization pipeline. Processes church service videos (MKV/MP4), transcribes audio using OpenAI's Whisper via `faster-whisper`, and generates structured summaries using Google's Gemini API. Target content: Reformed Christian sermons from IREC Melbourne in Indonesian/English.

## Commands

### Setup
```bash
./setup.sh          # Automated: installs uv, creates .venv, installs deps, creates .env
```

Manual:
```bash
uv python pin 3.13
uv venv --python 3.13
source .venv/bin/activate
uv pip install -r requirements.txt
cp env.example .env
```

### Run
```bash
./run_workflow.sh               # Recommended: validates env, runs, logs to logs/
source .venv/bin/activate && python -m src.main  # Manual
```

### Development Scripts
```bash
python script/check_devices.py        # Check GPU/MPS/CPU availability
python script/check_compute_types.py  # Check compute type support for Whisper
```

No linting or test suite is configured. Testing is done via live execution with real video files.

## Architecture

### Pipeline Flow

```
Video (MKV/MP4)
  → [ffmpeg] extract WAV (16kHz mono)
  → [Whisper tiny] first-pass transcript  → cached in temp/tiny/
  → [Gemini API] extract sermon timestamps (skip announcements/songs)
  → [ffmpeg] crop WAV to sermon boundaries
  → [Whisper medium] second-pass transcript  → cached in temp/medium/
  → [Gemini API] generate summary (title, markdown, Bible verses)
  → output/YYYYMMDD_HHMM/{filename}_summary.{json,md}
```

### Module Responsibilities

- **`src/main.py`** — Orchestrates the full pipeline. `process_single_file()` is the core function; `get_or_load_transcript()` handles caching logic; `summarize_and_save()` writes final output.
- **`src/transcribe.py`** — Whisper integration. Caches loaded models in-memory. `transcribe_wav_file()` is the core function. Device: `auto` (MPS/CUDA/CPU), compute type: `int8`.
- **`src/summarize.py`** — Gemini API calls. `summarize_sermon()` generates structured output; `extract_timestamp()` finds sermon boundaries. `_call_gemini_with_retry()` handles exponential backoff + key rotation.
- **`src/io_helpers.py`** — File I/O, path construction, and `APIKeyRotator` (primary + 3 fallback Gemini keys). Note: `input_dir` is hardcoded to `/mnt/H21/sermon` (a custom mount point), not the repo's `input/` directory.
- **`src/prompts.py`** — LLM prompt templates for summarization and timestamp extraction.
- **`src/typing.py`** — Pydantic models: `SermonSummary` (title, summary_markdown, bible_verses), `BibleVerse`, `TimestampResponse`.
- **`src/formatters.py`** — `extract_date_from_filename()` parses filename format `YYMMDD_HH-MM_Description.mkv` into human-readable dates.

### Input Filename Format

Files must follow: `YYMMDD_HH-MM_Description.mkv` (or `.mp4`)
Example: `260104_12-27_Afternoon.mkv` → parsed as "January 4, 2026"

### Key Configuration

**`.env`** (not in git):
```
GEMINI_API_KEY=<primary>
GEMINI_API_KEY_FALLBACK_1=<key1>
GEMINI_API_KEY_FALLBACK_2=<key2>
GEMINI_API_KEY_FALLBACK_3=<key3>
```

**Gemini model**: `gemini-2.5-flash`
**Whisper models**: `tiny` (first pass), `medium` (final pass)
**Language**: `id` (Indonesian) for Whisper transcription

### Error Handling

- Transient Gemini errors (503, overloaded): exponential backoff
- Rate limit errors: automatic rotation through fallback API keys via `APIKeyRotator`
- Transcripts cached to `temp/` to avoid re-running expensive Whisper inference
