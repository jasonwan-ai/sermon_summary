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

1. **Clone or navigate to this directory**

2. **Pin Python version** (optional, but recommended):
   ```bash
   uv python pin 3.13
   ```

3. **Create a virtual environment with uv**:
   ```bash
   uv venv --python 3.13
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```

5. **Configure API key**:
   Create a `.env` file in the project root with your Gemini API key:
   ```bash
   echo "GEMINI_API_KEY=your_key_here" > .env
   ```
   Or manually create `.env` with:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   Get your API key from: https://aistudio.google.com/apikey

6. **Place your MKV files** in the `input/` directory

## Usage

Run the main script:

```bash
python -m src.main
```

Or if you've set up the package as a module:

```bash
python -m ser_summary.src.main
```

The workflow will:
1. Scan `input/` for all `.mkv` files
2. Transcribe each file using faster-whisper
3. Generate summaries using Gemini API
4. Save outputs to `src/output/` as JSON and Markdown

## File Structure

```
ser_summary/
├── input/                    # Place MKV files here
│   └── *.mkv
├── src/
│   ├── main.py               # Entry point
│   ├── transcribe.py         # Transcription logic
│   ├── summarize.py          # Gemini API integration
│   ├── prompts.py            # Prompt templates
│   ├── typing.py             # Pydantic schemas
│   └── output/               # Generated summaries
│       ├── *_summary.json
│       └── *_summary.md
├── .env                      # Your API keys (not in git)
├── .env.example              # Template
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
- Make sure you've created `.env` file with your API key
- Check that `python-dotenv` is installed

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
