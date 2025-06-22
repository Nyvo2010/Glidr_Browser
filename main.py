import sys
import platform
import random
import time
from urllib.parse import quote, urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSizePolicy, QScrollArea, QShortcut
)
from PyQt5.QtCore import Qt, QUrl, QTimer, QPropertyAnimation, QPoint, QEasingCurve, QObject, QRect
from PyQt5.QtGui import QFont, QLinearGradient, QPainter, QColor, QBrush, QKeySequence, QCursor
from PyQt5.QtWebEngineWidgets import QWebEngineView

from duckduckgo_search import DDGS

# List of random prompts for the AI input box
AI_INPUT_PROMPTS = [
    "What's on your mind?",
    "Ask me anything!",
    "How can I assist you today?",
    "What would you like to know?",
    "Need help with something? Just ask."
]

# List of random prompts for the title text on startup
STARTUP_TITLE_PROMPTS = [
    "What are you looking for?",
    "Explore the internet.",
    "Find what you are looking for.",
    "What do you want to find?"
]

def get_random_prompt(prompt_list):
    """Return a random prompt from the given list."""
    return random.choice(prompt_list)

def duckduckgo_search(query):
    """
    Retrieve DuckDuckGo search results for a given query using DDGS.

    Args:
        query (str): The search query.

    Returns:
        list: A list of tuples containing the title and URL of search results.
    """
    results = []
    try:
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query)):
                title = r.get("title", "").strip()
                href = r.get("href", "")
                if title and href:
                    results.append((title, href))
                if len(results) >= 9:
                    break
    except Exception as e:
        print("DuckDuckGo search failed:", e)
    return results

def fetch_ai_summary(query):
    """
    Fetch a short AI-generated summary for the query.

    Args:
        query (str): The query to fetch a summary for.

    Returns:
        str: The AI-generated summary or an error message.
    """
    prompt = (
        f"{query} — no markdown, below 50 words, "
        "do not respond to the query, but give a brief info about it"
    )
    url = f"https://text.pollinations.ai/{quote(prompt)}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.text.strip()
    except requests.RequestException:
        return "GlidrAI response failed."
    return "No GlidrAI response."

def is_probable_url(text):
    """
    Check if the text is a probable URL.

    Args:
        text (str): The text to check.

    Returns:
        bool: True if the text is a probable URL, False otherwise.
    """
    if " " in text:
        return False
    if "." in text and not text.startswith("search://") and not text.startswith("startup://"):
        return True
    return False

class GradientOverlay(QWidget):
    """A widget that provides a gradient overlay effect."""
    def __init__(self, color="#121212", height=15, parent=None):
        super().__init__(parent)
        self.color = color
        self.setMinimumHeight(height)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, _event):
        """Custom painting for vertical gradient overlay."""
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        top_color = QColor(self.color)
        top_color.setAlpha(0)
        bottom_color = QColor(self.color)
        bottom_color.setAlpha(255)
        grad.setColorAt(0, top_color)
        grad.setColorAt(1, bottom_color)
        painter.fillRect(self.rect(), QBrush(grad))

    def resizeEvent(self, _event):
        """Repaint gradient on resize."""
        self.update()
        super().resizeEvent(_event)

class TabOverlay(QFrame):
    """A widget that provides an overlay for tabs."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: #1a1a1a; border: 1px solid #444444;")
        self.setFixedWidth(300)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.hide()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.tab_list = QWidget()
        self.tab_list_layout = QVBoxLayout(self.tab_list)
        self.tab_list_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_list_layout.setSpacing(0)

        self.layout.addWidget(self.tab_list)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

    def add_tab(self, title):
        """Add a tab to the overlay."""
        tab = QLabel(title)
        tab.setFont(QFont("San Francisco", 17))
        tab.setStyleSheet("color: white; background: transparent; border: none; padding: 10px;")
        tab.setCursor(Qt.PointingHandCursor)
        tab.setFixedHeight(40)

        def apply_dim(dimming):
            color = "#aaa" if dimming else "white"
            tab.setStyleSheet(f"color: {color}; background: transparent; border: none; padding: 10px;")

        tab.enterEvent = lambda e: apply_dim(True)
        tab.leaveEvent = lambda e: apply_dim(False)

        self.tab_list_layout.addWidget(tab)

    def show_animated(self):
        """Show the overlay with animation."""
        start_geom = QRect(-self.width(), self.y(), self.width(), self.height())
        end_geom = QRect(0, self.y(), self.width(), self.height())
        self.setGeometry(start_geom)
        self.show()
        self.animation.setStartValue(start_geom)
        self.animation.setEndValue(end_geom)
        self.animation.start()

    def hide_animated(self):
        """Hide the overlay with animation."""
        start_geom = QRect(0, self.y(), self.width(), self.height())
        end_geom = QRect(-self.width(), self.y(), self.width(), self.height())
        self.animation.setStartValue(start_geom)
        self.animation.setEndValue(end_geom)
        self.animation.start()

class ChatBubble(QFrame):
    """A widget that represents a chat bubble."""
    def __init__(self, text, is_ai):
        super().__init__()
        self.is_ai = is_ai
        self.setMaximumWidth(600)
        self.setStyleSheet(self._bubble_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setFont(QFont("San Francisco", 18))
        self.label.setStyleSheet(
            "color: white; background: transparent; border: none; margin: 0px; padding: 0px;"
        )
        layout.addWidget(self.label)

    def _bubble_style(self):
        """Returns appropriate style string for user/AI bubble."""
        if self.is_ai:
            return (
                "background-color: transparent;"
                "border: none;"
                "margin: 0px;"
                "padding: 0px;"
            )
        else:
            return (
                "background-color: rgba(30,30,30,0.85);"
                "border: 1px solid #444444;"
                "border-radius: 10px;"
                "margin: 0px;"
                "padding: 16px;"
            )

class LoadingOverlay(QWidget):
    """A widget that provides a loading overlay effect."""
    def __init__(self, parent=None, text="✳︎ Glidr is working...", opacity=180):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.bg_opacity = opacity
        self.setStyleSheet(f"background: rgba(18, 18, 18, {self.bg_opacity});")
        self.label = QLabel(text, self)
        self.label.setStyleSheet(
            "color: white; font-size: 18px; font-family: 'San Francisco', sans-serif;"
        )
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.label, alignment=Qt.AlignCenter)
        layout.addStretch()

    def set_opacity(self, opacity):
        """Set the opacity of the overlay."""
        self.bg_opacity = opacity
        self.setStyleSheet(f"background: rgba(18, 18, 18, {self.bg_opacity});")

    def set_text(self, text):
        """Set the text of the overlay."""
        self.label.setText(text)

    def resizeEvent(self, _event):
        """Resize the label to fit the overlay."""
        self.label.setFixedWidth(self.width())
        super().resizeEvent(_event)

class AnimatedResultWidget(QWidget):
    """A widget that provides an animation effect for results."""
    def __init__(self, child_widget, parent=None):
        super().__init__(parent)
        self.child_widget = child_widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(child_widget)
        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.anim = None

    def animate_rise_from_bottom(self, parent_window, delay_ms=0, duration_ms=250):
        """Animate widget rising from bottom of parent window."""
        self.show()
        QApplication.processEvents()
        start_y = parent_window.height()
        final_x = self.x()
        final_y = self.y()
        self.move(final_x, start_y)
        self.anim = QPropertyAnimation(self, b"pos", self)
        self.anim.setStartValue(QPoint(final_x, start_y))
        self.anim.setEndValue(QPoint(final_x, final_y))
        self.anim.setDuration(duration_ms)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        if delay_ms:
            QTimer.singleShot(delay_ms, self.anim.start)
        else:
            self.anim.start()

class SmoothScroller(QObject):
    """A class that provides smooth scrolling functionality."""
    def __init__(self, scrollbar, parent=None):
        super().__init__(parent)
        self.scrollbar = scrollbar
        self.anim = QPropertyAnimation(self.scrollbar, b"value")
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.setDuration(200)

    def scroll_to(self, target):
        """Smoothly scroll to the target value."""
        self.anim.stop()
        self.anim.setStartValue(self.scrollbar.value())
        self.anim.setEndValue(target)
        self.anim.start()

class GlidrAIChatWidget(QWidget):
    """A widget that provides an AI chat interface."""
    def __init__(self, parent=None, last_query=None, ai_special_string="__GLIDR_NAVIGATE__", via_ai_box=False):
        super().__init__(parent)
        self.setStyleSheet("background: #121212;")
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.parent_glidr = parent
        self.last_query = last_query
        self.ai_special_string = ai_special_string
        self.via_ai_box = via_ai_box

        # Conversation memory stores system, user, and assistant messages.
        self.memory = [{
            "role": "system",
            "content": (
                "You are GlidrAI, a web browser AI assistant. Help users browse and answer questions. "
                "No markdown formatting. "
                "For navigation requests, respond ONLY with: "
                f"{self.ai_special_string}(URL) "
                f"Example: {self.ai_special_string}(https://www.google.com)"
            )
        }]

        if self.last_query:
            self.memory.append({
                "role": "user",
                "content": f"Context: My previous search query was '{self.last_query}'. This may be relevant to my current request."
            })

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.content_container = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 10, 0, 50)
        self.content_layout.setSpacing(0)

        self.init_chat_area()
        self.init_input_area()
        self.content_layout.setStretch(0, 1)
        self.content_layout.setStretch(1, 0)

        self.main_layout.addWidget(self.content_container, alignment=Qt.AlignHCenter)
        self.main_layout.setStretch(0, 1)
        self.target_content_width = 0

        self.gradient_overlay = GradientOverlay(color="#121212", height=15, parent=self)
        self.gradient_overlay.hide()
        self.bottom_overlay = GradientOverlay(color="#121212", height=15, parent=self)
        self.bottom_overlay.hide()

        self.working_bubble = None

        self.scroller = SmoothScroller(self.scroll_area.verticalScrollBar())

    def init_chat_area(self):
        """Initializes chat area UI components."""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("border: none; QScrollBar { width: 0px; height: 0px; }")
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(30)
        # Header
        if self.last_query and self.via_ai_box:
            header_text = f'Chat with ✳︎ GlidrAI about "{self.last_query}"'
        else:
            header_text = "Chat with ✳︎ GlidrAI"
        self.header_label = QLabel(header_text)
        self.header_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.header_label.setFont(QFont("San Francisco", 25, QFont.Bold))
        self.header_label.setStyleSheet(
            "color: white; background: transparent; padding: 0; "
            "margin-top: 215px; margin-bottom: 2px; border: none;"
        )
        self.chat_layout.addWidget(self.header_label, 0, Qt.AlignHCenter)

        self.subtitle_label = QLabel('Just start typing...\n"Bring me to the F1 website"\n"Write a text about pandas"\n"Explain AI to me"')
        self.subtitle_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.subtitle_label.setFont(QFont("San Francisco", 15))
        self.subtitle_label.setStyleSheet(
            "color: #aaa; background: transparent; border: none; margin-top: 0px; margin-bottom: 40px;"
        )
        self.chat_layout.addWidget(self.subtitle_label, 0, Qt.AlignHCenter)
        self.chat_layout.addStretch(1)
        self.bottom_spacer = QWidget()
        self.bottom_spacer.setFixedHeight(10)
        self.chat_layout.addWidget(self.bottom_spacer)
        self.scroll_area.setWidget(self.chat_container)
        self.content_layout.addWidget(self.scroll_area)

    def init_input_area(self):
        """Initializes user input area UI."""
        self.input_container = QFrame()
        self.input_container.setFixedHeight(100)
        self.input_container.setStyleSheet(
            "background-color: #1a1a1a;"
            "border-radius: 10px;"
            "border: 1px solid #444444;"
        )
        input_layout = QHBoxLayout(self.input_container)
        input_layout.setContentsMargins(15, 15, 15, 15)
        input_layout.setSpacing(12)

        input_and_spacer = QVBoxLayout()
        input_and_spacer.setContentsMargins(0, 0, 0, 0)
        input_and_spacer.setSpacing(0)

        # Use a random prompt for the AI input box
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(get_random_prompt(AI_INPUT_PROMPTS))
        self.input_field.setFont(QFont("San Francisco", 18))
        self.input_field.setStyleSheet(
            "background: transparent;"
            "border: none;"
            "color: white;"
        )
        self.input_field.returnPressed.connect(self.send_message)
        self.input_field.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        input_and_spacer.addWidget(self.input_field)
        input_and_spacer.addStretch()

        input_layout.addLayout(input_and_spacer)

        self.send_btn = QPushButton("↑")
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setToolTip("Send")
        self.send_btn.setStyleSheet(
            "QPushButton {"
            "    background-color: #1A1A1A;"
            "    border: 1px solid #444444;"
            "    border-radius: 10px;"
            "    color: white;"
            "    font-size: 20px;"
            "}"
            "QPushButton:hover {"
            "    background-color: #333333;"
            "}"
        )
        self.send_btn.clicked.connect(self.send_message)

        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        btn_layout.addWidget(self.send_btn, 0, Qt.AlignRight)

        input_layout.addLayout(btn_layout)
        self.content_layout.addWidget(self.input_container)

    def resizeEvent(self, event):
        """Handles resizing and overlays for chat widget."""
        super().resizeEvent(event)
        if self.parent():
            top_bar_height = getattr(self.parent(), "top_bar", None)
            top = top_bar_height.height() if top_bar_height else 72
            self.setGeometry(0, top, self.parent().width(), self.parent().height() - top)
            if hasattr(self, "input_container") and hasattr(self, "gradient_overlay"):
                input_geom = self.input_container.geometry()
                gx = self.content_container.x() + input_geom.x()
                gy = self.content_container.y() + input_geom.y() - self.gradient_overlay.height()
                gw = self.content_container.width()
                self.gradient_overlay.setGeometry(
                    gx,
                    gy,
                    gw,
                    self.gradient_overlay.height()
                )
                self.gradient_overlay.show()
                self.gradient_overlay.raise_()
            if hasattr(self, "input_container") and hasattr(self, "bottom_overlay"):
                input_geom = self.input_container.geometry()
                gx = self.content_container.x() + input_geom.x()
                gy = self.content_container.y() + input_geom.y() + input_geom.height()
                gw = self.content_container.width()
                self.bottom_overlay.setGeometry(
                    gx,
                    gy,
                    gw,
                    self.bottom_overlay.height()
                )
                self.bottom_overlay.show()
                self.bottom_overlay.raise_()

    def show_working_bubble(self):
        """Show a working bubble in the chat."""
        self.remove_working_bubble()
        self.working_bubble = ChatBubble("✳︎ GlidrAI is working...", True)
        wrapper = QHBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(0)
        wrapper.addWidget(self.working_bubble, 0, Qt.AlignLeft)
        wrapper.addStretch(1)
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, wrapper)
        QTimer.singleShot(50, self.scroll_to_bottom_direct)

    def remove_working_bubble(self):
        """Remove the working bubble from the chat."""
        if self.working_bubble:
            self.working_bubble.setParent(None)
            self.working_bubble = None

    def add_bubble(self, text, is_ai):
        """Add a chat bubble to the chat."""
        bubble = ChatBubble(text, is_ai)
        wrapper = QHBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(0)
        if is_ai:
            wrapper.addWidget(bubble, 0, Qt.AlignLeft)
            wrapper.addStretch(1)
        else:
            wrapper.addStretch(1)
            wrapper.addWidget(bubble, 0, Qt.AlignRight)
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, wrapper)
        QTimer.singleShot(50, self.scroll_to_bottom_direct)

    def scroll_to_bottom_direct(self):
        """Scroll to the bottom of the chat directly."""
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())

    def scroll_to_bottom_smooth(self):
        """Scroll to the bottom of the chat smoothly."""
        bar = self.scroll_area.verticalScrollBar()
        self.scroller.scroll_to(bar.maximum())

    def send_message(self):
        """Send a message from the user."""
        user_text = self.input_field.text().strip()
        if not user_text:
            return
        self.input_field.clear()
        self.add_bubble(user_text, False)
        self.memory.append({"role": "user", "content": user_text})
        self.show_working_bubble()
        QTimer.singleShot(100, self.get_ai_response)

    def get_ai_response(self):
        """Handles response from the AI, navigation or display."""
        self.remove_working_bubble()
        prompt_text = self.build_prompt()
        response = self.fetch_ai_response(prompt_text)
        response = response.strip()
        nav_url = self.detect_ai_navigation(response)
        if nav_url and self.parent_glidr:
            self.memory.append({"role": "assistant", "content": response})
            self.parent_glidr.search_input.setText(nav_url)
            self.parent_glidr.toggle_ai_interface()
            self.parent_glidr._navigate_to(nav_url)
            return
        self.memory.append({"role": "assistant", "content": response})
        self.show_ai_response_animated(response)

    def detect_ai_navigation(self, response):
        """
        Detects the navigation string and returns a URL if present.

        Args:
            response (str): The response from the AI.

        Returns:
            str: The URL if navigation is detected, None otherwise.
        """
        prefix = f"{self.ai_special_string}("
        suffix = ")"
        if response.startswith(prefix) and response.endswith(suffix):
            url = response[len(prefix):-1].strip()
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            return url
        return None

    def build_prompt(self):
        """Formats conversation memory for AI prompt."""
        conversation_text = ""
        for entry in self.memory:
            role = entry["role"]
            content = entry["content"]
            if role == "system":
                conversation_text += f"[System]: {content}\n"
            elif role == "user":
                conversation_text += f"[User]: {content}\n"
            elif role == "assistant":
                conversation_text += f"{content}\n"
        return conversation_text

    def fetch_ai_response(self, prompt):
        url = f"https://text.pollinations.ai/{requests.utils.quote(prompt)}"
        try:
            r = requests.get(url, timeout=15)
            print("Response content:", r.text)
            if r.status_code == 200:
                return r.text.strip()
        except requests.RequestException:
            return "GlidrAI response failed."
        return "No GlidrAI response."

    def show_ai_response_animated(self, full_text):
        """Show the AI response with an animation."""
        bubble = ChatBubble(full_text, True)
        wrapper = QHBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(0)
        wrapper.addWidget(bubble, 0, Qt.AlignLeft)
        wrapper.addStretch(1)
        container = QWidget()
        container.setLayout(wrapper)
        animated = AnimatedResultWidget(container)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, animated)
        animated.animate_rise_from_bottom(self)
        QTimer.singleShot(300, self.scroll_to_bottom_smooth)

    def update_content_width(self, width, top_margin=10, bottom_margin=10):
        """Update the content width of the chat."""
        self.content_container.setFixedWidth(width)
        self.target_content_width = width
        self.content_layout.setContentsMargins(0, top_margin, 0, bottom_margin)
        self.resizeEvent(None)

    def focus_input(self):
        """Focus the input field."""
        self.input_field.setFocus()

class StartupSearchWidget(QWidget):
    """A widget that provides a search interface on startup."""
    def __init__(self, parent, search_placeholder="Search"):
        super().__init__(parent)
        self.parent_glidr = parent
        self.setStyleSheet("background: #121212;")
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addStretch(2)

        # Use a random prompt for the title text on startup
        self.header_label = QLabel(get_random_prompt(STARTUP_TITLE_PROMPTS))
        self.header_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.header_label.setFont(QFont("San Francisco", 25, QFont.Bold))
        self.header_label.setStyleSheet(
            "color: white; background: transparent; padding: 0; margin-bottom: 35px; border: none;"
        )
        self.main_layout.addWidget(self.header_label, 0, Qt.AlignHCenter)

        self.subtitle_label = QLabel("Just start typing...")
        self.subtitle_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.subtitle_label.setFont(QFont("San Francisco", 15))
        self.subtitle_label.setStyleSheet(
            "color: #aaa; background: transparent; border: none; margin-bottom: 35px;"
        )
        self.main_layout.addWidget(self.subtitle_label, 0, Qt.AlignHCenter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(search_placeholder)
        self.search_input.setFixedHeight(43)
        self.search_input.setFont(QFont("San Francisco", 17))
        self.search_input.setStyleSheet(
            "background-color: #1a1a1a;"
            "border-radius: 10px;"
            "border: 1px solid #444444;"
            "padding: 0 14px;"
            "color: white;"
            "font-size: 17px;"
            "font-family: 'San Francisco', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;"
        )
        self.search_input.returnPressed.connect(self.on_search)
        self.main_layout.addWidget(self.search_input, 0, Qt.AlignHCenter)
        self.main_layout.addStretch(3)
        QTimer.singleShot(100, self.select_search_text)

    def select_search_text(self):
        """Select the search text."""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def resizeEvent(self, _event):
        """Ensures search input width matches the center container."""
        if hasattr(self.parent_glidr, "center_container"):
            width = self.parent_glidr.center_container.width()
            self.search_input.setFixedWidth(width)
            self.header_label.setFixedWidth(width)
        super().resizeEvent(_event)

    def showEvent(self, _event):
        """Show the search widget."""
        super().showEvent(_event)
        QTimer.singleShot(50, self.select_search_text)

    def on_search(self):
        """Handle the search action."""
        text = self.search_input.text().strip()
        if not text:
            return
        if hasattr(self.parent_glidr, "startup_search_trigger"):
            self.parent_glidr.startup_search_trigger(text)
            self.hide()
            self.deleteLater()
            self.parent_glidr.startup_widget = None

class Glidr(QWidget):
    """The main application widget."""
    def __init__(self):
        super().__init__()
        self.history = []
        self.current_index = -1
        self.last_query = ""
        self.ai_box = None
        self.ignore_url_add = False
        self.ai_mode = False
        self.glidrai_chat_widget = None
        self.last_query_for_ai = None
        self.startup_widget = None
        self.ai_close_btn = None
        self.loading_overlay = None
        self.has_searched = False
        self.tab_overlay = None

        self.init_ui()
        self.setup_shortcuts()
        self.resize(1000, 700)
        self.setMinimumSize(800, 400)
        self.web_view.urlChanged.connect(self.on_url_changed)
        QTimer.singleShot(0, self.show_startup_widget)

    def setup_shortcuts(self):
        """Set up keyboard shortcuts for navigation and actions."""
        mod = "Meta" if platform.system() == "Darwin" else "Ctrl"

        self.shortcut_forward = QShortcut(QKeySequence(f"{mod}+."), self)
        self.shortcut_forward.activated.connect(self.go_forward)

        self.shortcut_back = QShortcut(QKeySequence(f"{mod}+,"), self)
        self.shortcut_back.activated.connect(self.go_back)

        self.shortcut_reload = QShortcut(QKeySequence(f"{mod}+R"), self)
        self.shortcut_reload.activated.connect(self.reload_page)

        self.shortcut_startup = QShortcut(QKeySequence(f"{mod}+W"), self)
        self.shortcut_startup.activated.connect(self.clear_history)

        self.shortcut_ai = QShortcut(QKeySequence(f"{mod}+G"), self)
        self.shortcut_ai.activated.connect(self.toggle_ai_interface)

    def show_loading_overlay(self, text="✳︎ Glidr is working...", full_opacity=False):
        """Show a loading overlay during search or navigation."""
        opacity = 255 if full_opacity else 180
        if self.loading_overlay is None:
            self.loading_overlay = LoadingOverlay(self, text=text, opacity=opacity)
        else:
            self.loading_overlay.set_text(text)
            self.loading_overlay.set_opacity(opacity)
        self.loading_overlay.setGeometry(
            0, self.top_bar.height(),
            self.width(), self.height() - self.top_bar.height()
        )
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        QApplication.processEvents()

    def hide_loading_overlay(self):
        """Hide the loading overlay."""
        if self.loading_overlay is not None:
            self.loading_overlay.hide()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Glidr")
        self.setStyleSheet("background-color: #121212; color: white;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.init_top_bar()
        self.init_chat_area()
        self.init_web_view()

    def init_top_bar(self):
        """Setup top bar UI with search, navigation, and AI button."""
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(72)
        self.top_bar.setStyleSheet(
            "background-color: #171717;"
            "border-bottom: 1px solid #444444;"
        )
        self.top_layout = QHBoxLayout(self.top_bar)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(0)
        self.logo = QLabel("✳︎ Glidr")
        self.logo.setFont(QFont("San Francisco", 25, QFont.Bold))
        self.logo.setStyleSheet("background: transparent; padding: 0; margin: 0; border: none;")
        self.top_layout.addWidget(self.logo, 0, Qt.AlignVCenter | Qt.AlignLeft)
        self.top_layout.addStretch(1)
        self.center_container = QWidget(self.top_bar)
        self.center_layout = QHBoxLayout(self.center_container)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search")
        self.search_input.setFixedHeight(43)
        self.search_input.setStyleSheet(self.input_style())
        self.search_input.setFont(QFont("San Francisco", 17))
        self.search_input.returnPressed.connect(self.top_bar_search_trigger)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.reload_btn = QPushButton("↺")
        self.reload_btn.setFixedSize(43, 43)
        self.reload_btn.setStyleSheet(self.button_style(enabled=False))
        self.reload_btn.setCursor(Qt.PointingHandCursor)
        self.reload_btn.clicked.connect(self.reload_page)
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedSize(43, 43)
        self.back_btn.setStyleSheet(self.button_style(enabled=False))
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.go_back)
        self.forward_btn = QPushButton("→")
        self.forward_btn.setFixedSize(43, 43)
        self.forward_btn.setStyleSheet(self.button_style(enabled=False))
        self.forward_btn.setCursor(Qt.PointingHandCursor)
        self.forward_btn.clicked.connect(self.go_forward)
        self.center_layout.addWidget(self.search_input)
        self.center_layout.addWidget(self.reload_btn)
        self.center_layout.addWidget(self.back_btn)
        self.center_layout.addWidget(self.forward_btn)
        self.center_container.setFixedHeight(72)
        self.center_container.raise_()
        self.ai_button_top_right = QPushButton("✳︎")
        self.ai_button_top_right.setFixedSize(43, 43)
        self.ai_button_top_right.setStyleSheet(self.button_style())
        self.ai_button_top_right.setCursor(Qt.PointingHandCursor)
        self.ai_button_top_right.clicked.connect(self.toggle_ai_interface)
        button_container = QWidget()
        button_container.setStyleSheet("background: transparent; border: none;")
        button_container.setAttribute(Qt.WA_TranslucentBackground)
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(15, 15, 15, 15)
        button_layout.setSpacing(0)
        button_layout.addWidget(self.ai_button_top_right, alignment=Qt.AlignTop | Qt.AlignRight)
        self.top_layout.addWidget(button_container, 0, Qt.AlignTop | Qt.AlignRight)
        self.main_layout.addWidget(self.top_bar)

    def init_chat_area(self):
        """Initialize the chat area."""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.outer = QWidget()
        self.outer_layout = QHBoxLayout(self.outer)
        self.outer_layout.setSpacing(0)
        self.outer_layout.setContentsMargins(0, 12, 0, 36)
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(24)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.addWidget(self.results_container)
        self.scroll_area.setWidget(self.outer)
        self.main_layout.addWidget(self.scroll_area)

    def init_web_view(self):
        """Initialize the web view."""
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.web_view.hide()
        self.main_layout.addWidget(self.web_view)

    def input_style(self):
        """Return the style sheet for input fields."""
        return (
            "background-color: #1a1a1a;"
            "border-radius: 10px;"
            "border: 1px solid #444444;"
            "padding: 0 14px;"
            "color: white;"
            "font-size: 17px;"
            "font-family: 'San Francisco', -apple-system;"
        )

    def button_style(self, enabled=True):
        """Return the style sheet for buttons."""
        opacity = "1.0" if enabled else "0.5"
        return (
            "QPushButton {"
            "background-color: #1a1a1a;"
            f"color: rgba(255, 255, 255, {opacity});"
            "border: 1px solid #444444;"
            "border-radius: 10px;"
            "font-family: 'San Francisco', -apple-system;"
            "font-size: 19px;"
            "font-weight: bold;"
            "}"
            "QPushButton:disabled {"
            "background-color: #1a1a1a;"
            "color: rgba(255,255,255,0.5);"
            "border: 1px solid #444444;"
            "}"
            "QPushButton:hover:!disabled {"
            "background-color: #333;"
            "}"
        )

    def show_ai_close_button(self):
        """Display the close ("×") button for the AI chat interface."""
        if self.ai_close_btn:
            self.ai_close_btn.show()
            QTimer.singleShot(0, self.update_ai_close_button_geometry)
            return
        self.ai_close_btn = QPushButton("×", self)
        self.ai_close_btn.setFixedSize(43, 43)
        self.ai_close_btn.setStyleSheet(self.button_style())
        self.ai_close_btn.setFont(QFont("San Francisco", 25, QFont.Bold))
        self.ai_close_btn.setCursor(Qt.PointingHandCursor)
        self.ai_close_btn.clicked.connect(self.toggle_ai_interface)
        self.ai_close_btn.setToolTip("Close AI chat")
        self.ai_close_btn.show()
        QTimer.singleShot(0, self.update_ai_close_button_geometry)

    def hide_ai_close_button(self):
        """Hide the close button for the AI chat interface."""
        if self.ai_close_btn:
            self.ai_close_btn.hide()

    def showEvent(self, event):
        """Show the AI close button if it is visible."""
        super().showEvent(event)
        if self.ai_close_btn and self.ai_close_btn.isVisible():
            self.update_ai_close_button_geometry()

    def update_ai_close_button_geometry(self):
        """Update the geometry of the AI close button."""
        if self.ai_close_btn and self.ai_close_btn.isVisible():
            btn_x = self.width() - self.ai_close_btn.width() - 15
            btn_y = self.top_bar.height() + 15
            self.ai_close_btn.move(btn_x, btn_y)
            self.ai_close_btn.raise_()

    def focus_best_search_bar(self):
        """Set focus to the best search bar (startup or top bar)."""
        if getattr(self, "startup_widget", None) and self.startup_widget.isVisible():
            self.startup_widget.search_input.setFocus()
            self.startup_widget.search_input.selectAll()
        else:
            self.search_input.setFocus()
            self.search_input.selectAll()

    def toggle_ai_interface(self, via_ai_box=False):
        """Show or hide the AI chat interface."""
        self.ai_mode = not self.ai_mode
        if self.ai_mode:
            if via_ai_box:
                last_query = self.last_query_for_ai
            else:
                last_query = None
            self.glidrai_chat_widget = GlidrAIChatWidget(self, last_query=last_query, via_ai_box=via_ai_box)
            self.glidrai_chat_widget.setParent(self)
            self.glidrai_chat_widget.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
            self.update_glidrai_chat_geometry()
            QTimer.singleShot(0, self.update_glidrai_chat_geometry)
            self.glidrai_chat_widget.show()
            self.glidrai_chat_widget.update_content_width(self.center_container.width(), top_margin=10, bottom_margin=10)
            QTimer.singleShot(0, self.glidrai_chat_widget.focus_input)
            self.show_ai_close_button()
        else:
            if self.glidrai_chat_widget:
                self.glidrai_chat_widget.hide()
                self.glidrai_chat_widget.deleteLater()
                self.glidrai_chat_widget = None
            self.hide_ai_close_button()
            if (not self.has_searched) or (self.current_index >= 0 and self.history and self.history[self.current_index] == "startup://"):
                QTimer.singleShot(150, self.focus_best_search_bar)

    def update_glidrai_chat_geometry(self):
        """Ensure AI chat widget geometry matches current window."""
        if self.glidrai_chat_widget:
            top_bar_height = self.top_bar.height()
            if top_bar_height == 0:
                top_bar_height = 72
            self.glidrai_chat_widget.setGeometry(
                0,
                top_bar_height,
                self.width(),
                self.height() - top_bar_height
            )
            self.glidrai_chat_widget.raise_()
            self.glidrai_chat_widget.update_content_width(self.center_container.width(), top_margin=10, bottom_margin=10)

    def show_startup_widget(self):
        """Display the startup widget and update history."""
        self.history = self.history[: self.current_index + 1]
        if not self.history or self.history[-1] != "startup://":
            self.history.append("startup://")
            self.current_index = len(self.history) - 1
        self.update_nav_buttons()
        self.search_input.setText("")
        if hasattr(self, "startup_widget") and self.startup_widget:
            self.startup_widget.hide()
            self.startup_widget.deleteLater()
        self.web_view.hide()
        self.scroll_area.show()
        self.clear_results()
        self.startup_widget = StartupSearchWidget(self)
        self.startup_widget.setParent(self)
        self.startup_widget.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.startup_widget.setGeometry(0, self.top_bar.height(), self.width(), self.height() - self.top_bar.height())
        self.startup_widget.show()
        self.startup_widget.raise_()
        QTimer.singleShot(150, self.focus_best_search_bar)

    def clear_ai_box(self):
        """Clear the AI box."""
        if self.ai_box is not None:
            try:
                self.results_layout.removeWidget(self.ai_box)
            except Exception:
                pass
            self.ai_box.deleteLater()
            self.ai_box = None

    def clear_results(self):
        """Remove all result widgets from the results container."""
        self.clear_ai_box()
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def update_ai_box_width(self):
        """Adjust AI box width when resizing."""
        if not self.ai_box:
            return
        left, _, right, _ = self.outer_layout.getContentsMargins()
        max_width = self.scroll_area.width() - left - right
        self.ai_box.setMaximumWidth(max_width)

    def unified_search_trigger(self, text, full_overlay=False):
        """Unified entry point for search from either startup or top bar."""
        if self.startup_widget:
            self.startup_widget.hide()
            self.startup_widget.deleteLater()
            self.startup_widget = None
        self.search_input.setText(text)
        self.web_view.hide()
        self.scroll_area.show()
        self.clear_results()

        self.has_searched = True
        if self.glidrai_chat_widget:
            self.toggle_ai_interface()
        # Improved URL detection logic.
        if is_probable_url(text):
            if not text.startswith("http://") and not text.startswith("https://"):
                text = "https://" + text
            self._navigate_to(text)
            return

        entry = f"search://{text}"
        self.history = self.history[: self.current_index + 1]
        if not self.history or self.history[-1] != entry:
            self.history.append(entry)
            self.current_index = len(self.history) - 1
            self.last_query_for_ai = text

        self.show_loading_overlay(full_opacity=full_overlay)
        QTimer.singleShot(100, lambda: self._load_search_results(text))
        self.update_nav_buttons()

    def top_bar_search_trigger(self):
        """Handle search from the top bar."""
        text = self.search_input.text().strip()
        if not text:
            return
        self.unified_search_trigger(text, full_overlay=False)

    def startup_search_trigger(self, text):
        """Handle search from the startup widget."""
        if not text:
            return
        self.unified_search_trigger(text, full_overlay=True)

    def perform_search(self):
        """Perform a search."""
        self.top_bar_search_trigger()

    def load_search_page(self, query, full_overlay=False):
        """Load a search page."""
        self.unified_search_trigger(query, full_overlay=full_overlay)

    def _load_search_results(self, query):
        """Fetches and displays AI and search results."""
        self.has_searched = True
        ai_result = fetch_ai_summary(query)
        results = duckduckgo_search(query)
        self.hide_loading_overlay()
        widgets = []
        ai_widget = self._make_ai_box_widget(ai_result)
        animated_ai = AnimatedResultWidget(ai_widget)
        self.results_layout.addWidget(animated_ai)
        self.ai_box = animated_ai
        widgets.append(animated_ai)

        for title, url in results:
            result_widget = self._make_result_widget(title, url)
            animated_result = AnimatedResultWidget(result_widget)
            self.results_layout.addWidget(animated_result)
            widgets.append(animated_result)
        self.update_ai_box_width()

        delay_step = 100
        for idx, widget in enumerate(widgets):
            widget.animate_rise_from_bottom(self, delay_ms=idx * delay_step)
        self.update_nav_buttons()

    def _make_ai_box_widget(self, text):
        """Creates the AI result widget."""
        box = QFrame()
        box.setStyleSheet(
            "background-color: #1a1a1a;"
            "border: 1px solid #444444;"
            "border-radius: 10px;"
        )
        layout = QVBoxLayout(box)
        layout.setContentsMargins(24, 24, 24, 24)
        title_layout = QHBoxLayout()
        title_label = QLabel("AI Result")
        title_label.setFont(QFont("San Francisco", 22, QFont.Bold))
        title_label.setStyleSheet("color: white; background: transparent; border: none;")
        title_layout.addWidget(title_label)
        self.ai_button_inside_ai_box = QPushButton("✳︎")
        self.ai_button_inside_ai_box.setFixedSize(43, 43)
        self.ai_button_inside_ai_box.setStyleSheet(self.button_style())
        self.ai_button_inside_ai_box.setCursor(Qt.PointingHandCursor)
        self.ai_button_inside_ai_box.clicked.connect(lambda: self.toggle_ai_interface(via_ai_box=True))
        title_layout.addStretch()
        title_layout.addWidget(self.ai_button_inside_ai_box)
        layout.addLayout(title_layout)
        content = QLabel(text)
        content.setWordWrap(True)
        content.setFont(QFont("San Francisco", 17))
        content.setStyleSheet("color: white; background: transparent; border: none;")
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(content)
        return box

    def _make_result_widget(self, title_text, url):
        """Creates a clickable search result widget."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)
        font_family = "San Francisco"
        font_size = 17
        title = QLabel(title_text)
        title.setWordWrap(True)
        title.setFont(QFont(font_family, font_size, QFont.Bold))
        title.setStyleSheet("color: white;")
        title.setCursor(Qt.PointingHandCursor)
        url_label = QLabel(url)
        url_label.setWordWrap(True)
        url_label.setFont(QFont(font_family, font_size))
        url_label.setStyleSheet("color: #ccc;")
        url_label.setCursor(Qt.PointingHandCursor)
        container_layout.addWidget(title)
        container_layout.addWidget(url_label)

        def apply_dim(dimming: bool):
            color_title = "#aaa" if dimming else "white"
            color_url = "#888" if dimming else "#ccc"
            title.setStyleSheet(f"color: {color_title};")
            url_label.setStyleSheet(f"color: {color_url};")

        title.enterEvent = lambda e: apply_dim(True)
        title.leaveEvent = lambda e: apply_dim(False)
        url_label.enterEvent = lambda e: apply_dim(True)
        url_label.leaveEvent = lambda e: apply_dim(False)

        def open_link_event(event):
            self._navigate_to(url)
        title.mousePressEvent = open_link_event
        url_label.mousePressEvent = open_link_event
        return container

    def _navigate_to(self, url):
        """Hide overlays/widgets and navigate to a URL in the web view."""
        if hasattr(self, "glidrai_chat_widget") and self.glidrai_chat_widget:
            self.glidrai_chat_widget.hide()
        if hasattr(self, "startup_widget") and self.startup_widget:
            self.startup_widget.hide()
        if hasattr(self, "loading_overlay") and self.loading_overlay:
            self.loading_overlay.hide()
        if hasattr(self, "scroll_area") and self.scroll_area:
            self.scroll_area.hide()
        # Show the web view and load the page.
        self.web_view.show()
        self.web_view.raise_()
        self.web_view.load(QUrl(url))
        self.search_input.setText(url)
        self.history = self.history[: self.current_index + 1]
        if not self.history or self.history[-1] != url:
            self.history.append(url)
            self.current_index = len(self.history) - 1
        self.ignore_url_add = True
        self.update_nav_buttons()
        self.search_input.clearFocus()

    def on_url_changed(self, qurl):
        """Update history when the web view's URL changes."""
        if self.ignore_url_add:
            self.ignore_url_add = False
            return
        new_url = qurl.toString()
        if self.current_index >= 0 and self.history[self.current_index] == new_url:
            self.search_input.setText(new_url)
            return
        self.history = self.history[: self.current_index + 1]
        if not self.history or self.history[-1] != new_url:
            self.history.append(new_url)
            self.current_index = len(self.history) - 1
            self.search_input.setText(new_url)
        self.update_nav_buttons()

    def go_back(self):
        """Navigate back in the browsing/search history."""
        if self.current_index > 1 and self.history[self.current_index].startswith("search://") and self.history[1] == "startup://":
            self.current_index = 1
            entry = self.history[self.current_index]
            self.ignore_url_add = True
            self.search_input.setText("")
            self.show_startup_widget()
            QTimer.singleShot(150, self.focus_best_search_bar)
            self.update_nav_buttons()
            return
        if self.current_index <= 0:
            return
        self.current_index -= 1
        entry = self.history[self.current_index]
        self.ignore_url_add = True
        if entry == "startup://":
            self.search_input.setText("")
            if hasattr(self, "startup_widget") and self.startup_widget:
                self.startup_widget.search_input.setText("")
            self.show_startup_widget()
            QTimer.singleShot(150, self.focus_best_search_bar)
        elif entry.startswith("search://"):
            query = entry[len("search://"):]
            self.unified_search_trigger(query, full_overlay=False)
            self.search_input.setText(query)
        else:
            self.web_view.load(QUrl(entry))
            self.web_view.show()
            self.scroll_area.hide()
            self.search_input.setText(entry)
        self.update_nav_buttons()

    def go_forward(self):
        """Navigate forward in the browsing/search history."""
        if self.current_index >= len(self.history) - 1:
            return
        self.current_index += 1
        entry = self.history[self.current_index]
        self.ignore_url_add = True
        if entry == "startup://":
            self.search_input.setText("")
            if hasattr(self, "startup_widget") and self.startup_widget:
                self.startup_widget.search_input.setText("")
            self.show_startup_widget()
            QTimer.singleShot(150, self.focus_best_search_bar)
        elif entry.startswith("search://"):
            query = entry[len("search://"):]
            self.unified_search_trigger(query, full_overlay=False)
            self.search_input.setText(query)
        else:
            self.web_view.load(QUrl(entry))
            self.web_view.show()
            self.scroll_area.hide()
            self.search_input.setText(entry)
        self.update_nav_buttons()

    def reload_page(self):
        """Reload the current web page if the web view is visible."""
        if self.web_view.isVisible():
            self.web_view.reload()

    def update_nav_buttons(self):
        """Update the enabled/disabled state and style of navigation buttons."""
        back_enabled = self.current_index > 0
        forward_enabled = self.current_index < len(self.history) - 1
        reload_enabled = self.web_view.isVisible()
        self.back_btn.setEnabled(back_enabled)
        self.forward_btn.setEnabled(forward_enabled)
        self.reload_btn.setEnabled(reload_enabled)
        self.back_btn.setStyleSheet(self.button_style(back_enabled))
        self.forward_btn.setStyleSheet(self.button_style(forward_enabled))
        self.reload_btn.setStyleSheet(self.button_style(reload_enabled))

    def resizeEvent(self, event):
        """Handles resizing of all major UI components to maintain layout."""
        super().resizeEvent(event)
        margin_lr = min(360, max(24, (self.width() - 480) // 2))
        self.outer_layout.setContentsMargins(margin_lr, 12, margin_lr, 36)
        max_width = self.width() - margin_lr * 2
        self.results_container.setMaximumWidth(max_width)
        self.center_container.setFixedWidth(max_width)
        top_bar_width = self.top_bar.width()
        center_x = (top_bar_width - max_width) // 2
        center_y = (self.top_bar.height() - self.center_container.height()) // 2
        self.center_container.move(center_x, center_y)
        self.center_container.raise_()
        self.update_ai_box_width()
        self.logo.setContentsMargins(24, 0, 0, 0)
        self.update_glidrai_chat_geometry()
        if self.glidrai_chat_widget:
            self.glidrai_chat_widget.update_content_width(self.center_container.width(), top_margin=10, bottom_margin=10)
        if hasattr(self, "startup_widget") and self.startup_widget and self.startup_widget.isVisible():
            self.startup_widget.setGeometry(
                0,
                self.top_bar.height(),
                self.width(),
                self.height() - self.top_bar.height()
            )
        if self.ai_close_btn and self.ai_close_btn.isVisible():
            self.update_ai_close_button_geometry()
        if self.loading_overlay and self.loading_overlay.isVisible():
            self.loading_overlay.setGeometry(
                0, self.top_bar.height(),
                self.width(), self.height() - self.top_bar.height()
            )

    def clear_history(self):
        """Clear all navigation/search history and reset UI."""
        self.history = []
        self.current_index = -1
        self.show_startup_widget()

    def enterEvent(self, event):
        """Handle mouse enter events for the main window."""
        super().enterEvent(event)
        if not self.tab_overlay:
            self.tab_overlay = TabOverlay(self)
            self.tab_overlay.setGeometry(0, self.height() - 300, 300, 300)
            self.update_tab_overlay()

    def leaveEvent(self, event):
        """Handle mouse leave events for the main window."""
        super().leaveEvent(event)
        if self.tab_overlay and not self.tab_overlay.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.tab_overlay.hide_animated()

    def mouseMoveEvent(self, event):
        """Handle mouse move events for the main window."""
        super().mouseMoveEvent(event)
        if event.x() < 20 and not self.tab_overlay.isVisible():
            self.tab_overlay.show_animated()
        elif event.x() > 300 and self.tab_overlay.isVisible() and not self.tab_overlay.rect().contains(event.pos()):
            self.tab_overlay.hide_animated()

    def update_tab_overlay(self):
        """Update the tab overlay with current tabs."""
        if self.tab_overlay:
            # Clear existing tabs
            while self.tab_overlay.tab_list_layout.count():
                item = self.tab_overlay.tab_list_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add current tabs
            for index, entry in enumerate(self.history):
                if entry != "startup://":
                    self.tab_overlay.add_tab(f"Tab {index + 1}: {entry}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QScrollBar:vertical {
            width: 6px;
            background: rgba(0,0,0,0);
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: rgba(51,51,51,128);
            min-height: 40px;
            border-radius: 3px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar:horizontal {
            height: 6px;
            background: rgba(0,0,0,0);
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: rgba(51,51,51,128);
            min-width: 40px;
            border-radius: 3px;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        """)
    glidr = Glidr()
    glidr.show()
    sys.exit(app.exec_())


#  ██████╗ ██╗     ██╗██████╗ ██████╗ 
# ██╔════╝ ██║     ██║██╔══██╗██╔══██╗
# ██║  ███╗██║     ██║██║  ██║██████╔╝
# ██║   ██║██║     ██║██║  ██║██╔══██╗
# ╚██████╔╝███████╗██║██████╔╝██║  ██║
#  ╚═════╝ ╚══════╝╚═╝╚═════╝ ╚═╝  ╚═╝