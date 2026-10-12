# New Dawn City College Online CBT Portal — Starter

A custom website starter for New Dawn City College, Gusau, Zamfara State. Includes admin/student login, student accounts for JSS 1–3 and SS 1–3, exam creation, multiple-choice and True/False questions, automatic scoring, one attempt per student/exam, and an admin results dashboard.

## Run locally for a test
1. Install Python 3.10+.
2. Extract the ZIP and open a terminal in this folder.
3. Run `python -m venv .venv` and activate it.
4. Run `pip install -r requirements.txt`.
5. Set a private session secret, e.g. `SECRET_KEY` environment variable.
6. Run `python app.py`.
7. Open `http://127.0.0.1:5000` in a browser.

## Demo credentials — change before use
- Admin: `admin` / `ChangeMe123!`
- Sample student: `NDCC001` / `482915`

## Important before real exams
This is a starter, not an audited production system. The timer is currently advisory and does not force-submit; no CSV/Excel/PDF export, bulk import, password reset, question randomization, or exam scheduling window is included yet. Before public deployment, change demo passwords, set a long private `SECRET_KEY`, use HTTPS, run behind a production WSGI server (for example Gunicorn), configure persistent database storage, back up the database, and test with dummy accounts. Never use Flask's development server for public deployment.

## Hosting
To let students access the portal online, deploy it to a Python-compatible host that supports persistent storage. Configure the host to run `gunicorn app:app` (install Gunicorn on the host), set `SECRET_KEY`, and set `DATABASE_PATH` to a persistent disk path. Your host will provide a public URL; a custom domain can be added later.
