# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Two-pass transcription workflow: first pass with tiny model to identify sermon boundaries, second pass with medium model on cropped audio
- LLM-based timestamp extraction to automatically detect sermon start and end times
- Audio cropping functionality to process only the sermon portion
- Comprehensive timing metrics for transcription, API calls, and overall processing
- Token usage tracking for API calls (sent and received tokens)
- Model caching to avoid reloading Whisper models
- Enhanced error handling with proper cleanup of temporary WAV files
- Detailed processing summary with breakdown of time spent in each stage

### Changed
- Optimized transcription workflow to reduce processing time by cropping audio before final transcription
- Improved model loading with explicit device selection (MPS for Apple Silicon)
- Enhanced main workflow with better separation of concerns and modular functions
- Updated prompts to support timestamp extraction functionality
- Refactored I/O helpers for better organization
- Updated type definitions to support new timestamp extraction features

### Removed
- `src/extractor.py` - functionality consolidated into main workflow

### Fixed
- Improved cleanup of temporary audio files in error scenarios
- Better handling of existing transcripts to avoid redundant processing

## [0.1.0] - 2026-01-19

### Added
- Initial sermon transcription and summarization pipeline
- Automatic transcription using faster-whisper
- AI summarization with Gemini API
- Batch processing of MKV files
- Structured output in JSON and Markdown formats
- Date extraction from filenames
- Helper script to identify compute type
- Logging functionality
- Automated setup script
- Workflow execution script
- Example .env file and comprehensive README
