# Ollama Model Manager

A Streamlit-based web application for managing your Ollama models. This dashboard provides an intuitive interface to browse, search, download, and manage local AI models through Ollama.

## Features

- **Model Management**: View, download, and delete Ollama models
- **Model Details**: Examine model information, including parameters, templates, and system prompts
- **Model Search**: Search for available models by keywords or categories
- **Real-time Downloads**: Track download progress with visual indicators

## Requirements

- Python 3.8 or higher
- Streamlit
- Pandas
- Ollama (running locally)
- Additional Python libraries: time, re, logging

## Installation

1. Make sure Ollama is installed and running (visit <https://ollama.com/> for installation instructions)
2. Clone this repository
3. Install the required Python packages:

   ```bash
   pip install streamlit pandas ollama
   ```

## Usage

1. Start the Ollama service on your machine
2. Run the application:

   ```bash
   streamlit run main.py
   ```

3. Open your browser and navigate to the URL displayed in the terminal (typically <http://localhost:8501>)

## Application Sections

### Models List

The main dashboard shows all installed models with their size and last modified date. You can:

- View details of any model
- Delete models (with confirmation)

### Model Details

Shows detailed information about selected models, including:

- Basic information (family, parameter size, quantization level)
- System prompt
- Template format
- Model parameters
- License information

### Search

Find new models to download:

- Search by keywords
- Filter by category (Code, Vision, Small, Medium, Large)
- Pull (download) models directly from the search interface

## Notes

- The application requires Ollama to be running locally
- Model search results are from a preset catalog and may not include all available models
- The application will display appropriate error messages if Ollama is not accessible

## License

[Your license information here]

## Acknowledgements

Built with Streamlit and the Ollama API.
