"""
ZebEduApplication Launcher
Launches the Flask application inside a desktop window using PyWebView
Auto-populates schools database on first run
"""

import threading
import sys
import io
import os
import time
import socket
import webview
import logging

# Prevent I/O errors when running as windowed executable
if hasattr(sys, "_MEIPASS"):
    # Running as compiled .exe
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")
else:
    # Running as script - keep normal output
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Disable logging output for compiled version
if hasattr(sys, "_MEIPASS"):
    logging.basicConfig(level=logging.CRITICAL)
else:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def is_port_in_use(port: int) -> bool:
    """Check if a given TCP port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def safe_print(message):
    """Safely print messages - works in both script and compiled mode"""
    try:
        print(message)
    except:
        pass


def setup_database():
    """Initialize database and add schools if empty"""
    safe_print("\n" + "=" * 70)
    safe_print("Checking database...")
    safe_print("=" * 70 + "\n")

    from app import app
    from models import db, School

    with app.app_context():
        # Create all tables
        db.create_all()
        safe_print("✓ Database tables created/verified")

        # Check if schools exist
        school_count = School.query.count()

        if school_count == 0:
            safe_print("\n" + "=" * 70)
            safe_print("First time setup: Adding schools to database...")
            safe_print("=" * 70 + "\n")

            try:
                # Import schools data directly
                from add_sample_schools import add_sample_schools

                # Call the function to add schools
                add_sample_schools()

                # Verify schools were added
                new_count = School.query.count()
                safe_print(f"\n✓ Successfully added {new_count} schools to database!")

            except ImportError:
                safe_print("⚠️  Warning: Could not import add_sample_schools module.")
                safe_print("   Schools database may be empty.")
                safe_print("   Please run 'python add_sample_schools.py' manually.\n")
            except Exception as e:
                safe_print(f"⚠️  Error populating schools: {e}")
                safe_print("   You may need to add schools manually.\n")
        else:
            safe_print(f"✓ Database ready - {school_count} schools loaded\n")


def run_flask():
    """Run the Flask server in a background thread."""
    from app import app

    app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)


def main():
    """Main function to launch the ZebEdu desktop app."""
    safe_print("=" * 70)
    safe_print("        ZebEduApplication - School Application System")
    safe_print("=" * 70)

    # Check if the port is already in use
    if is_port_in_use(5001):
        safe_print("\n⚠️  Another instance of ZebEduApplication is already running.")
        safe_print("   Please close it before starting a new one.")
        logging.info("Another instance is already running.")
        # Don't use input() in windowed mode
        if not hasattr(sys, "_MEIPASS"):
            input("\nPress Enter to exit...")
        sys.exit(1)

    # Setup and populate database FIRST
    try:
        setup_database()
    except Exception as e:
        safe_print(f"\n⚠️  Database setup error: {e}")
        safe_print("   The application will still start, but may have issues.")
        safe_print("   Please contact support if problems persist.\n")

    safe_print("\nStarting application server...")
    safe_print("A desktop window will open automatically.")
    safe_print("\nPress CTRL+C in the terminal to stop the server.")
    safe_print("=" * 70 + "\n")

    # Start the Flask server in a background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Give Flask a moment to start
    time.sleep(3)

    # Determine icon path (works both for .py and compiled .exe)
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    icon_path = os.path.join(base_path, "icon.ico")

    # Create a desktop window for your Flask app
    try:
        window = webview.create_window(
            title="ZebEdu Application",
            url="http://127.0.0.1:5001",
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
            safe_print(f"⚠️  Could not set icon: {e}")

        # Start the GUI loop
        safe_print("✓ Application window opened successfully!")
        safe_print("📍 Location detection is ready to use!\n")
        webview.start()

    except Exception as e:
        safe_print(f"\n❌ Error creating window: {e}")
        safe_print("   The Flask server is still running at: http://127.0.0.1:5001")
        safe_print("   You can open this URL in your browser manually.\n")
        if not hasattr(sys, "_MEIPASS"):
            input("Press Enter to exit...")

    safe_print("\n\n" + "=" * 70)
    safe_print("Shutting down application...")
    safe_print("Thank you for using ZebEduApplication!")
    safe_print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
