# YouTube Smart Pause

A browser extension that helps fact-check arguments of a YouTube video content.

## Features

- Elegant sidebar interface that appears when you press 'E' while watching a video
- Real-time video information display including current timestamp and progress
- Analyze video content at the current timestamp with AI-powered insights
- Markdown rendering support for analysis results
- Smooth animations and modern glass-morphism design

## Installation

1. Clone this repository
2. Open Chrome/Firefox and go to extensions page
3. Enable "Developer Mode"
4. Click "Load unpacked extension" and select the `browser_extension` folder

## Config
To start the extention, you should create a ```.env``` file:
```
PERPLEXITY_API_KEY=<Your Perplexity API Key>
OPENROUTER_API_KEY=<Your OpenRouter API Key>
OPENROUTER_MODEL_NAM=<OpenRouter Model Name>
```

## Usage

1. Navigate to any YouTube video
2. Press 'E' to open/close the sidebar
3. Click "Analyze Current Position" to get AI analysis of the current video segment
4. The analysis will appear in the results section below

## Technical Details

The extension consists of:
- `content.js`: Main extension logic and sidebar functionality
- `sidebar.css`: Styling with modern glass-morphism design
- `manifest.json`: Extension configuration
- Backend server (required) for AI analysis

## Requirements

- Modern web browser (Chrome/Firefox)
- Backend server running on localhost:8000
- marked.js library for Markdown rendering

## Development

The extension uses:
- Custom CSS with backdrop-filter for glass effect
- Stream-based response handling for real-time analysis updates
- Event listeners for video state management
- MutationObserver for handling dynamic YouTube content

## License

MIT License
