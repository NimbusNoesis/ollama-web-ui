import streamlit as st
import sys
import importlib.util
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the main app
from app.main import main

# Run the app
if __name__ == "__main__":
    main()
