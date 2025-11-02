"""
ZebEduApplication Launcher
Launches the Flask application inside a desktop window using PyWebView
"""

import threading
import sys
import io
import os
import time
import socket
import webview
from app import app
import logging

# Ensure UTF-8 output for terminals that don't support emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Setup logging for optional logging to file or terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def is_port_in_use(port: int) -> bool:
    """Check if a given TCP port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('0.0.0.0', port)) == 0


def run_flask():
    """Run the Flask server in a background thread."""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


def safe_print(*args, **kwargs):
    """Print safely, ignoring errors if stdout is closed."""
    try:
        print(*args, **kwargs)
    except (ValueError, IOError):
        pass


def main():
    """Main function to launch the ZebEdu desktop app."""
    safe_print("=" * 70)
    safe_print("ZebEduApplication - School Application System")
    safe_print("=" * 70)
    safe_print("\nStarting application server...")
    safe_print("A desktop window will open automatically.")
    safe_print("\nPress CTRL+C in the terminal to stop the server.")
    safe_print("=" * 70 + "\n")

    # Check if another instance is running
    if is_port_in_use(5000):
        safe_print("\n⚠️  Another instance of ZebEduApplication is already running.")
        safe_print("   Please close it before starting a new one.")
        logging.warning("Another instance is already running.")
        sys.exit(1)

    # Start Flask server in a background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Give Flask time to start
    time.sleep(2)

    # Determine icon path (works for .py and PyInstaller .exe)
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_path, "icon.ico")

    # Create a desktop window for the Flask app
    window = webview.create_window(
        title="ZebEdu Application",
        url="http://0.0.0.0:5000",
        width=1200,
        height=800,
        resizable=True,
        confirm_close=True,
    )

    # Set icon if possible
    try:
        if os.path.exists(icon_path):
            window.icon = icon_path
    except Exception as e:
        safe_print(f"!! Could not set icon: {e}")
        logging.warning(f"Could not set icon: {e}")

    # Start the GUI loop
    webview.start()

    # Shutdown messages
    safe_print("\n\nShutting down application...")
    safe_print("Thank you for using ZebEduApplication!")
    logging.info("Application shutdown successfully.")


if __name__ == '__main__':
    main()
