# Sermon Transcription and Summarization

An automated workflow to transcribe video recordings of church services and generate structured sermon summaries using faster-whisper and Google's Gemini API.

## Features

- **Automatic Transcription**: Uses faster-whisper to transcribe MKV video files
- **AI Summarization**: Generates structured summaries with Bible verses using Gemini API
- **Batch Processing**: Processes all MKV files in the `input/` directory automatically
- **Structured Output**: Saves summaries as both JSON and Markdown formats
- **Date Extraction**: Automatically extracts sermon dates from filenames

## Prerequisites

- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
  - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or see [uv installation](https://github.com/astral-sh/uv#installation))
- Python 3.13 (managed by uv)
- ffmpeg (system dependency for audio extraction)
- Gemini API key ([Get one here](https://aistudio.google.com/apikey))

## Setup

The easiest way to set up the project is using the automated setup script:

1. **Run the setup script**:
   ```bash
   ./setup.sh
   ```

   This script will:
   - Check for and install `uv` if needed
   - Verify `ffmpeg` is installed
   - Pin Python 3.13
   - Create a virtual environment
   - Install all dependencies
   - Create the `input/` directory if it doesn't exist
   - Create `.env` file 

2. **Configure API key**:
   Fill in your Gemini API key in the .env file created by the script

   ```
   GEMINI_API_KEY=your_key_here
   ```
   Get your API key from: https://aistudio.google.com/apikey

3. **Place your MKV files** in the `input/` directory

### Manual Setup (Alternative)

If you prefer to set up manually:

1. **Pin Python version**:
   ```bash
   uv python pin 3.13
   ```

2. **Create a virtual environment**:
   ```bash
   uv venv --python 3.13
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```

4. **Create `.env` file** in the project root (see step 2 above)

## Usage

### Recommended: Use the workflow script

Run the automated workflow script:

```bash
./run_workflow.sh
```

This script will:
- Check that the virtual environment exists
- Verify `.env` file is present
- Check for MKV files in `input/` directory
- Activate the virtual environment
- Run the transcription and summarization workflow

### Manual execution

Alternatively, you can run the workflow manually:

```bash
source .venv/bin/activate  # Activate virtual environment
python -m src.main
```

### What the workflow does

The workflow will:
1. Scan `input/` for all `.mkv` files
2. Transcribe each file using faster-whisper (saves transcripts to `temp/` for reuse)
3. Generate summaries using Gemini API
4. Save outputs to `src/output/` as JSON and Markdown files

## File Structure

```
ser_summary/
├── input/                    # Place MKV files here
│   └── *.mkv
├── temp/                     # Temporary transcript files (auto-created)
│   └── *_transcript.txt
├── src/
│   ├── main.py               # Entry point
│   ├── transcribe.py         # Transcription logic
│   ├── summarize.py          # Gemini API integration
│   ├── prompts.py            # Prompt templates
│   ├── typing.py             # Pydantic schemas
│   └── output/               # Generated summaries (auto-created)
│       ├── *_summary.json
│       └── *_summary.md
├── .env                      # Your API keys (not in git)
├── .venv/                    # Virtual environment (auto-created by setup.sh)
├── setup.sh                  # Automated setup script
├── run_workflow.sh           # Workflow execution script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Filename Format

The script extracts dates from filenames using this pattern:
- Format: `{YYMMDD}_{time}_{description}.mkv`
- Example: `260104_12-27_Afternoon.mkv` → Date: "January 4, 2026"

## Output Format

Each processed file generates two outputs:

1. **JSON** (`*_summary.json`): Structured data with `summary` and `bible_verses` fields
2. **Markdown** (`*_summary.md`): Human-readable format

## Configuration

### Whisper Model

Default model is `medium`. To change, edit `src/transcribe.py`:
```python
transcribe_file(path, model_size="large")  # or "base", "small", "medium", "large"
```
** dont chage model size**

### Prompts

Customize prompts in `src/prompts.py`:
- `SYSTEM_PROMPT`: System instructions for Gemini (use `.format(date=date)`)
- `USER_PROMPT`: User prompt with transcript (use `.format(transcript=transcript)`)

## Troubleshooting

### "GEMINI_API_KEY environment variable is not set"
- Make sure you've created `.env` file in the **project root** (not in `src/`)
- Verify the file contains: `GEMINI_API_KEY=your_key_here`
- Check that `python-dotenv` is installed (should be in requirements.txt)

### "File not found" errors
- Ensure MKV files are in the `input/` directory
- Check file permissions

### Transcription errors
- Verify ffmpeg is installed: `ffmpeg -version`
- Check that the MKV file is not corrupted

### API errors
- Verify your Gemini API key is valid
- Check your API quota/limits
- Ensure you have internet connectivity

## License

IREC Melbourne 2026
