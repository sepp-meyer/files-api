# run.py
import os
from fileserver.app import create_app

app = create_app()

if __name__ == "__main__":
    debug = bool(int(os.getenv("FLASK_DEBUG", "1")))
    # Reloader AUS, damit er nicht wegen Dateiänderungen mitten im Test neu startet
    app.run(debug=debug, use_reloader=False)
