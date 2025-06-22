# ✳︎ Glidr Browser

Glidr is a web browser application built with Python and PyQt5. It features a user-friendly interface with an integrated AI chat assistant.

## Installation

To run Glidr, you need to have Python installed. Install the required packages using pip:

```bash
pip install PyQt5 PyQtWebEngine requests beautifulsoup4 duckduckgo-search
```

## Usage

Start the Glidr browser by running:

```bash
python glidr.py
```

### Keyboard Shortcuts

- `Ctrl + .`: Go forward
- `Ctrl + ,`: Go back
- `Ctrl + R`: Reload the current page
- `Ctrl + W`: Clear history and show the startup widget
- `Ctrl + G`: Toggle the AI chat interface

### AI Chat Interface

Press `Ctrl + G` or one of the `✳︎` buttons to toggle the AI chat interface. Type your query or message and press `Enter` to send. The AI will respond with relevant information or assistance, or open a webpage on request.

### Search Functionality

Enter your search query in the search bar and press `Enter`. Glidr uses DuckDuckGo as its search engine and displays results in the main window.

### Web Navigation

Enter a URL in the search bar to visit a specific website. Use the navigation buttons to move through your browsing history or refresh the current page.
