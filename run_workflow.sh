#!/bin/bash
# Run the sermon transcription and summarization workflow

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

# Generate log filename with current datetime
LOG_FILENAME="logs/$(date +%Y%m%d_%H%M%S).log"
LOG_FILE="$SCRIPT_DIR/$LOG_FILENAME"

# Function to log and display messages
log_and_echo() {
    echo -e "$@" | tee -a "$LOG_FILE"
}

log_and_echo "${BLUE}========================================${NC}"
log_and_echo "${BLUE}Running Sermon Summary Workflow${NC}"
log_and_echo "${BLUE}========================================${NC}"
log_and_echo "${BLUE}Log file: ${LOG_FILENAME}${NC}\n"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo -e "${YELLOW}Please run setup first:${NC}"
    echo -e "  ./setup.sh\n"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ Warning: .env file not found${NC}"
    echo -e "${YELLOW}Make sure you have created .env with your GEMINI_API_KEY${NC}\n"
fi

# Check if input directory exists and has files
if [ ! -d "input" ]; then
    echo -e "${RED}✗ input directory not found${NC}"
    echo -e "${YELLOW}Please create the input directory and add your MKV files${NC}\n"
    exit 1
fi

MKV_COUNT=$(find input -name "*.mkv" -type f | wc -l | tr -d ' ')
if [ "$MKV_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠ No MKV files found in input/ directory${NC}"
    echo -e "${YELLOW}Please add your MKV files to the input/ directory${NC}\n"
    exit 1
fi

log_and_echo "${GREEN}Found ${MKV_COUNT} MKV file(s) to process${NC}\n"

# Activate virtual environment
log_and_echo "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate

# Run the workflow and capture all output to log file
log_and_echo "${BLUE}Starting workflow...${NC}\n"

# Execute workflow and tee output to both terminal and log file
# Capture both stdout and stderr, with stderr redirected to stdout
set +e  # Temporarily disable exit on error to capture exit code
uv run python -m src.main 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}  # Capture exit code of uv run command
set -e  # Re-enable exit on error

# Check exit status and output final message
if [ $EXIT_CODE -eq 0 ]; then
    log_and_echo "\n${GREEN}========================================${NC}"
    log_and_echo "${GREEN}Workflow completed successfully!${NC}"
    log_and_echo "${GREEN}========================================${NC}\n"
    log_and_echo "Check the ${BLUE}output/${NC} directory for your summaries."
    log_and_echo "Log file saved to: ${BLUE}${LOG_FILENAME}${NC}\n"
else
    log_and_echo "\n${RED}========================================${NC}"
    log_and_echo "${RED}Workflow failed${NC}"
    log_and_echo "${RED}========================================${NC}\n"
    log_and_echo "Log file saved to: ${BLUE}${LOG_FILENAME}${NC}\n"
    exit $EXIT_CODE
fi
