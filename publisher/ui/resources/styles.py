"""
Style sheets for Pipeline Publisher UI.

Contains Qt style definitions for consistent theming across all UI components.
"""

# Main window global stylesheet
MAIN_WINDOW_STYLE = """
QMainWindow {
    background-color: #1e1e1e;
}

QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
}

QLabel#header_label {
    font-size: 18pt;
    font-weight: bold;
    color: #0078d4;
    padding: 8px;
    background-color: #2b2b2b;
    border-radius: 4px;
}

QLabel#footer_label {
    font-size: 13pt;
    color: #666666;
    padding: 8px;
}

QPushButton {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 14pt;
    min-height: 32px;
}

QPushButton:hover {
    background-color: #1084d8;
}

QPushButton:pressed {
    background-color: #005a9e;
}

QPushButton:disabled {
    background-color: #444444;
    color: #888888;
}

/* Test control buttons - gray style */
QPushButton#test_button {
    background-color: #4a4a4a;
    color: #ffffff;
    border: 1px solid #555555;
}

QPushButton#test_button:hover {
    background-color: #5a5a5a;
    border-color: #666666;
}

QPushButton#test_button:pressed {
    background-color: #3a3a3a;
    border-color: #444444;
}

QLabel#status_display {
    background-color: #3a3a3a;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 6px;
    font-size: 14pt;
    color: #cccccc;
}

QTextEdit#log_display {
    background-color: #2b2b2b;
    border: 1px solid #444444;
    border-radius: 4px;
    color: #cccccc;
    font-family: 'Courier New', monospace;
    font-size: 14pt;
    padding: 8px;
}

QFrame#controls_frame {
    background-color: #2b2b2b;
    border: 1px solid #444444;
    border-radius: 6px;
    padding: 12px;
}
"""


# Publish bar highlight border
PUBLISH_BAR_STYLE = """
QFrame#controls_frame {
    background-color: #2b2b2b;
    border: 2px solid #0078d4;
    border-radius: 6px;
    padding: 4px;
}
"""


# Status display dynamic colors (applied programmatically)
STATUS_COLORS = {
    'success': '#4caf50',
    'error': '#f44336',
    'warning': '#ff9800',
    'info': '#2196f3',
    'default': '#666666',
}

# Log message colors
LOG_COLORS = {
    'info': '#2196f3',
    'success': '#4caf50',
    'warning': '#ff9800',
    'error': '#f44336',
}


def get_status_style(status_type: str = 'default') -> str:
    """Get status display stylesheet for given status type.

    Args:
        status_type: 'success', 'error', 'warning', 'info', or 'default'

    Returns:
        QLabel stylesheet string with appropriate border color
    """
    color = STATUS_COLORS.get(status_type, STATUS_COLORS['default'])
    return f"""
        QLabel#status_display {{
            background-color: #3a3a3a;
            border: 1px solid {color};
            border-radius: 4px;
            padding: 6px;
            font-size: 14pt;
            color: {color};
            font-weight: normal;
        }}
    """


def get_colored_message(message: str, log_type: str = 'info') -> str:
    """Wrap message in HTML span with appropriate color.

    Args:
        message: The message text
        log_type: 'info', 'success', 'warning', or 'error'

    Returns:
        HTML-formatted colored message string
    """
    color = LOG_COLORS.get(log_type, LOG_COLORS['info'])
    return f'<span style="color: {color}">{message}</span>'
