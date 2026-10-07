NEXTME V7.3 - DEPLOYMENT READY

Required environment variables:
1. OPENAI_API_KEY = your OpenAI API secret key
2. NEXTME_SECRET_KEY = a long random secret string
3. NEXTME_DATA_DIR = optional persistent data directory

Start command:
gunicorn app:app

For Render/Railway-type hosting:
- Build command: pip install -r requirements.txt
- Start command: gunicorn app:app
- Add OPENAI_API_KEY and NEXTME_SECRET_KEY as secret environment variables.
- Do NOT put API keys in HTML/JavaScript.
- Persistent disk/storage is required if using the included SQLite database in production.

Important:
SQLite is fine for local testing and a small beta, but for a larger public launch
use a managed database such as PostgreSQL so account/history data survives scaling
and multiple server instances.

Before public launch:
- Replace local-screen password reset code with email delivery.
- Add rate limiting.
- Add privacy policy and terms.
- Add production domain and HTTPS.
