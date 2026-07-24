"""Compatibility launcher for the HTML/Three.js GUI.

The project GUI is implemented as a web interface served by app.py.
Running `python gui.py` is kept as a convenient alias for `python app.py`.
"""

from app import main


if __name__ == "__main__":
    main()
