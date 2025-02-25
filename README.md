# Ollama UI

A comprehensive UI for Ollama, providing model management, chat capabilities, and model comparison features.

## Features

### Model Management

- **Browse Models**: View all installed models with size and modification date
- **Model Details**: Examine detailed information about models, including parameters, templates, and system prompts
- **Search Models**: Find and install models from the Ollama library
- **Download Progress**: Track model download progress with visual indicators

### Chat Interface

- **Full Chat Capabilities**: Chat with any installed Ollama model
- **Conversation Management**: Save, load, and delete conversations
- **Custom Settings**: Adjust temperature and system prompts for each chat
- **Persistent Storage**: All chats are saved as JSON files for easy access

### Model Comparison

- **Compare Multiple Models**: Run the same prompt against multiple models side by side
- **Visual Comparison**: Easily compare responses from different models
- **Customizable**: Select any combination of installed models to compare

## Requirements

- Python 3.8 or higher
- Streamlit
- Pandas
- Ollama (running locally)
- Additional Python libraries: requests, json, datetime, markdown

## Installation

1. Make sure Ollama is installed and running (visit <https://ollama.com/> for installation instructions)
2. Clone this repository
3. Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Usage

1. Start the Ollama service on your machine
2. Run the application:

```bash
streamlit run main.py
```

3. Open your browser and navigate to the URL displayed in the terminal (typically <http://localhost:8501>)

## Application Structure

The application is structured in a modular way for better maintainability:

- `app/api`: API interaction with Ollama
- `app/components`: Reusable UI components
- `app/pages`: Different pages of the application
- `app/utils`: Utility functions and classes
- `app/data`: Data storage (chats)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Ollama](https://ollama.com/)
