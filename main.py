import streamlit as st
import sys
import os

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import the main app
from app.main import main

# Run the app
if __name__ == "__main__":
    main()
