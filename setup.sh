#!/bin/bash

# Real-Time Trading Analytics Platform
# Automated Setup Script

echo "================================================"
echo "  Real-Time Trading Analytics Platform Setup"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo -e "${GREEN}✓ Python $python_version detected${NC}"
else
    echo -e "${RED}✗ Python 3.8 or higher required. Current: $python_version${NC}"
    exit 1
fi

# Create project structure
echo -e "\n${YELLOW}Creating project structure...${NC}"
mkdir -p backend
mkdir -p templates
mkdir -p data
mkdir -p exports
mkdir -p logs

echo -e "${GREEN}✓ Directories created${NC}"

# Create __init__.py for backend package
echo -e "\n${YELLOW}Initializing backend package...${NC}"
cat > backend/__init__.py << 'EOF'
"""
Backend package for Real-Time Trading Analytics Platform
"""

__version__ = '1.0.0'

from .data_ingestion import DataIngestionService
from .storage import DatabaseManager
from .analytics_engine import AnalyticsEngine
from .alert_manager import AlertManager

__all__ = [
    'DataIngestionService',
    'DatabaseManager',
    'AnalyticsEngine',
    'AlertManager'
]
EOF

echo -e "${GREEN}✓ Backend package initialized${NC}"

# Install dependencies
echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
echo -e "${YELLOW}This may take a few minutes...${NC}"

pip3 install -q Flask==3.0.0 \
    flask-cors==4.0.0 \
    flask-socketio==5.3.5 \
    websockets==12.0 \
    pandas==2.1.4 \
    numpy==1.26.2 \
    scipy==1.11.4 \
    scikit-learn==1.3.2 \
    statsmodels==0.14.1 \
    plotly==5.18.0 \
    python-socketio==5.10.0 \
    eventlet==0.33.3

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dependencies installed successfully${NC}"
else
    echo -e "${RED}✗ Error installing dependencies${NC}"
    exit 1
fi

# Check if all required files exist
echo -e "\n${YELLOW}Checking required files...${NC}"

required_files=(
    "app.py"
    "backend/data_ingestion.py"
    "backend/storage.py"
    "backend/analytics_engine.py"
    "backend/alert_manager.py"
    "templates/index.html"
    "requirements.txt"
    "README.md"
)

missing_files=0
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗ Missing file: $file${NC}"
        missing_files=$((missing_files + 1))
    else
        echo -e "${GREEN}✓ Found: $file${NC}"
    fi
done

if [ $missing_files -gt 0 ]; then
    echo -e "\n${RED}Setup incomplete. Please ensure all files are in place.${NC}"
    exit 1
fi

# Create .gitignore
echo -e "\n${YELLOW}Creating .gitignore...${NC}"
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# Exports
exports/*.csv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local
EOF

echo -e "${GREEN}✓ .gitignore created${NC}"

# Test import
echo -e "\n${YELLOW}Testing imports...${NC}"
python3 << 'EOF'
try:
    import flask
    import flask_socketio
    import websockets
    import pandas
    import numpy
    import scipy
    import sklearn
    import statsmodels
    import plotly
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Import test passed${NC}"
else
    echo -e "${RED}✗ Import test failed${NC}"
    exit 1
fi

echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo -e "\n${YELLOW}To start the application:${NC}"
echo -e "  ${GREEN}python3 app.py${NC}"
echo -e "\n${YELLOW}Then open your browser to:${NC}"
echo -e "  ${GREEN}http://localhost:5000${NC}"
echo -e "\n${YELLOW}For more information, see:${NC}"
echo -e "  ${GREEN}README.md${NC}"
echo -e "  ${GREEN}ARCHITECTURE.md${NC}"
echo ""