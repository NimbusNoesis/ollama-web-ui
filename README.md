# Ollama UI

A comprehensive UI for Ollama, providing model management, chat capabilities, and model comparison features.

## Features

### 🤖 Model Management

- Browse and manage installed models
- View detailed model information including parameters and templates
- Search and download models from Ollama library
- Real-time download progress tracking
- Delete unused models

### 💬 Chat Interface

- Interactive chat with any installed model
- Adjustable parameters (temperature, system prompts)
- Save and load conversations
- Persistent chat history
- Multi-session support

### 🔄 Model Comparison

- Compare responses from multiple models simultaneously
- Side-by-side output comparison
- Customizable model selection
- Unified prompt interface

## Requirements

- Python 3.8+
- Ollama (running locally)
- Required Python packages:
  - streamlit
  - pandas
  - ollama
  - requests
  - markdown
  - pygments

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

ollama-ui/
├── app/
│ ├── api/ # Ollama API integration
│ ├── components/ # Reusable UI components
│ ├── data/ # Chat history storage
│ ├── pages/ # Application pages
│ ├── utils/ # Utility functions
│ └── main.py # App initialization
├── requirements.txt
└── main.py # Entry point

## Usage

### Model Management

- Navigate to the Models page to view installed models
- Use the search function to find and download new models
- View detailed model information and parameters
- Remove unused models

### Chat Interface

- Select a model to chat with
- Adjust temperature and system prompts
- Save conversations for later reference
- Load previous chat sessions

### Model Comparison

- Select multiple models to compare
- Enter a single prompt to test across models
- View responses side by side
- Compare model performance and outputs

## Contributing

1. Fork the repository
1. Create a feature branch (git checkout -b feature/enhancement)
1. Commit changes (git commit -am 'Add new feature')
1. Push to branch (git push origin feature/enhancement)
1. Create Pull Request

## License

This project is licensed under the Apache 2 License - see the LICENSE file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Ollama](https://ollama.com/)
