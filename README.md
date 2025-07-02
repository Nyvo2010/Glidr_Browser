# ✳︎ Glidr Browser

Glidr is a web browser application built with Python and PyQt5. It features a user-friendly interface with an integrated AI chat assistant.

## Prerequisites

Before installing Glidr, make sure you have:
- Python 3.5 or higher installed on your system
- pip (Python package installer)

## Installation Instructions

### Step 1: Download the Project
1. Download and extract the project zip file to your desired location
2. Open a terminal/command prompt and navigate to the project directory:
   ```
   cd path/to/glidr-browser
   ```

### Step 2: Install Dependencies
Install the required packages using the requirements file:
```
pip install -r requirements.txt
```

**Alternative method:** If the above doesn't work, install packages individually:
```
pip install PyQt5 PyQtWebEngine requests beautifulsoup4 duckduckgo-search
```

### Step 3: Run the Application
Start the Glidr browser by running:
```
python glidr.py
```

## Troubleshooting

### Common Issues:
- **PyQt5 installation fails**: Try `pip install --upgrade pip` first, then retry
- **WebEngine not working**: Make sure PyQtWebEngine is properly installed
- **Permission errors**: On Linux/Mac, you might need to use `pip3` instead of `pip`

### System-specific notes:
- **Windows**: Make sure Python is added to your PATH
- **macOS**: You might need to install additional dependencies for PyQt5
- **Linux**: Some distributions require `python3-pip` to be installed separately

## Features

### Keyboard Shortcuts
* `Ctrl + .`: Go forward
* `Ctrl + ,`: Go back
* `Ctrl + R`: Reload the current page
* `Ctrl + W`: Clear history and show the startup widget
* `Ctrl + G`: Toggle the AI chat interface

### AI Chat Interface
Press `Ctrl + G` or one of the `✳︎` buttons to toggle the AI chat interface. Type your query or message and press `Enter` to send. The AI will respond with relevant information or assistance, or open a webpage on request.

### Search Functionality
Enter your search query in the search bar and press `Enter`. Glidr uses DuckDuckGo as its search engine and displays results in the main window.

### Web Navigation
Enter a URL in the search bar to visit a specific website. Use the navigation buttons to move through your browsing history or refresh the current page.

## File Structure
```
glidr-browser/
├── glidr.py          # Main application file
├── requirements.txt  # Required Python packages
└── README.md        # This file
```

## Support
If you encounter any issues during installation or usage, please check the troubleshooting section above.
