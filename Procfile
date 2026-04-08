# Render/Heroku-style process file (Render reads the "web" line).
# Pre-deploy migrations: set in Render dashboard → Settings → Pre-Deploy Command:
#   flask --app run.py db upgrade
# `python -m gunicorn` uses the same interpreter as pip (avoids PATH issues).
web: python -m gunicorn --bind 0.0.0.0:$PORT run:app
