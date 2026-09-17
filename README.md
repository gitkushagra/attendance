# HoursTrack — Flask

A dark-mode weekly working-hours manager built with Flask + SQLite.

## Features
- Username/password accounts with hashed passwords
- Daily start and exit logging
- 9-hour normal working-day target
- Shortfall carry-forward to the next working day
- Overtime reduces the next working-day target
- Friday target reflects the accumulated balance
- 45-hour weekly target
- WFH is marked as a working day for daily calculations, but reduces the weekly target by 9 hours; holiday / leave also reduce weekly target by 9 hours
- Non-working day can be marked as working without changing the weekly requirement
- Circular weekly progress indicator
- Responsive dark UI

## Run on Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py app.py
```

Open http://127.0.0.1:5000

## Run on macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Production notes
- Change `SECRET_KEY` in `app.py`.
- Use a production WSGI server rather than Flask's development server.
- For a multi-user internet deployment, use HTTPS and a managed database.

- Week selection uses Month / Week-of-month dropdowns.
- WFH automatically logs 10:00 AM–7:00 PM, counts as a working day, and reduces the weekly requirement by 9 hours.
- Times are displayed in 12-hour AM/PM format.
