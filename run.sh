#!/bin/bash

# AI Test Generator - Launch Script

echo "🧪 AI-Powered Test Case Generator"
echo "================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Checking dependencies..."
pip install -q -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo "Please create a .env file with your Gemini API key:"
    echo "GEMINI_API_KEY=your_key_here"
    echo ""
fi

# Launch the app
echo ""
echo "🚀 Launching application..."
echo "Opening browser at http://localhost:8501"
echo ""
streamlit run src/app.py
