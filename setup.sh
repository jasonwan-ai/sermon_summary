#!/bin/bash
# Setup script for sermon transcription and summarization workflow
# Supports both Linux and macOS

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
echo -e "${BLUE}Sermon Summary Setup${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo -e "${GREEN}Detected OS: ${MACHINE}${NC}\n"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for ffmpeg
echo -e "${BLUE}Checking for ffmpeg...${NC}"
if ! command_exists ffmpeg; then
    echo -e "${RED}✗ ffmpeg is not installed${NC}"
    echo -e "${YELLOW}Please install ffmpeg:${NC}"
    if [ "$MACHINE" = "Mac" ]; then
        echo -e "  brew install ffmpeg"
    else
        echo -e "  sudo apt-get install ffmpeg  # Debian/Ubuntu"
        echo -e "  sudo yum install ffmpeg      # RHEL/CentOS"
    fi
    exit 1
fi
echo -e "${GREEN}✓ ffmpeg found${NC}\n"

# Check for uv or install it
echo -e "${BLUE}Checking for uv...${NC}"
if ! command_exists uv; then
    echo -e "${YELLOW}uv not found. Installing uv...${NC}"
    if [ "$MACHINE" = "Mac" ]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add to PATH for current session
        export PATH="$HOME/.cargo/bin:$PATH"
    else
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add to PATH for current session
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    
    # Verify installation
    if ! command_exists uv; then
        echo -e "${RED}✗ Failed to install uv. Please install manually:${NC}"
        echo -e "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    echo -e "${GREEN}✓ uv installed successfully${NC}\n"
else
    echo -e "${GREEN}✓ uv found${NC}\n"
fi

# Pin Python version
echo -e "${BLUE}Pinning Python 3.13...${NC}"
if [ -f ".python-version" ]; then
    PINNED_VERSION=$(cat .python-version)
    echo -e "${GREEN}✓ Using Python version from .python-version: ${PINNED_VERSION}${NC}\n"
    uv python pin "$PINNED_VERSION"
else
    echo -e "${YELLOW}No .python-version file found. Pinning Python 3.13...${NC}"
    uv python pin 3.13
    echo -e "${GREEN}✓ Python 3.13 pinned${NC}\n"
fi

# Create virtual environment
echo -e "${BLUE}Creating virtual environment...${NC}"
if [ -d ".venv" ]; then
    echo -e "${YELLOW}.venv already exists. Removing old virtual environment...${NC}"
    rm -rf .venv
fi

uv venv --python 3.13
echo -e "${GREEN}✓ Virtual environment created${NC}\n"

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}\n"

# Install dependencies
echo -e "${BLUE}Installing dependencies from requirements.txt...${NC}"
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}✗ requirements.txt not found${NC}"
    exit 1
fi

uv pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}\n"

# Create .env file
echo -e "${BLUE}Creating .env file...${NC}"
cp env.example .env
echo -e "${GREEN}✓ .env file created${NC}\n"
echo -e "${GREEN}Please fill in your Gemini API key in the .env file${NC}\n"
echo -e "Get your API key from: https://aistudio.google.com/apikey\n"

# Check for input directory
echo -e "${BLUE}Checking for input directory...${NC}"
if [ ! -d "input" ]; then
    echo -e "${YELLOW}⚠ input directory not found. Creating it...${NC}"
    mkdir -p input
    echo -e "${GREEN}✓ input directory created${NC}\n"
else
    echo -e "${GREEN}✓ input directory found${NC}\n"
fi

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}\n"
echo -e "Next steps:"
echo -e "  1. Place your MKV files in the ${BLUE}input/${NC} directory"
echo -e "  2. Make sure you have a ${BLUE}.env${NC} file with your GEMINI_API_KEY"
echo -e "  3. Run the workflow with: ${BLUE}./run_workflow.sh${NC}\n"
