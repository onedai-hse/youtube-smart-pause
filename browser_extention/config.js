// YouTube Smart Pause Extension - Configuration
// This file contains all configurable settings for the extension

window.YOUTUBE_ASSISTANT_CONFIG = {
  // Backend API URL - Change this to your backend server address
  // Examples:
  // - Local development: 'http://localhost:8000'
  // - Production server: 'https://your-domain.com'
  // - Different port: 'http://localhost:3000'
  BACKEND_URL: 'http://localhost:8000',
  
  // Other configurable settings
  UPDATE_INTERVAL: 2000, // How often to update video info (milliseconds)
  PREVIEW_THROTTLE: 5000, // How often to update extractable phrase preview (milliseconds)
  DEFAULT_CONTEXT_SECONDS: 30, // Default context window for analysis
  MAX_TITLE_LENGTH: 50 // Maximum title length to display
};

// Export for use in content script
window.YOUTUBE_ASSISTANT_BACKEND_URL = window.YOUTUBE_ASSISTANT_CONFIG.BACKEND_URL; 