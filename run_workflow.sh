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

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Running Sermon Summary Workflow${NC}"
echo -e "${BLUE}========================================${NC}\n"

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

echo -e "${GREEN}Found ${MKV_COUNT} MKV file(s) to process${NC}\n"

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate

# Run the workflow
echo -e "${BLUE}Starting workflow...${NC}\n"
uv run python -m src.main

# Check exit status
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}Workflow completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}\n"
    echo -e "Check the ${BLUE}src/output/${NC} directory for your summaries.\n"
else
    echo -e "\n${RED}========================================${NC}"
    echo -e "${RED}Workflow failed${NC}"
    echo -e "${RED}========================================${NC}\n"
    exit 1
fi
