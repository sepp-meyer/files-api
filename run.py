# app.py (im Projekt-Root)
import os
from fileserver.app import create_app

app = create_app()

if __name__ == "__main__":
    debug = bool(int(os.getenv("FLASK_DEBUG", "1")))
    app.run(debug=debug)
