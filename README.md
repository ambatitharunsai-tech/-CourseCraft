# CourseCraft — AI Learning Path Generator

CourseCraft is a Flask web application that creates structured learning curricula for a skill or career goal. It uses Groq chat completions for AI generation, SQLAlchemy for accounts and saved history, and a responsive vanilla HTML/CSS/JavaScript interface.

**Live app:** https://coursecraft-e1jx.onrender.com  
**Repository:** https://github.com/ambatitharunsai-tech/-CourseCraft

## Features

- **Curriculum generation:** uses the skill/topic, target duration, and experience level to create a phased learning path.
- **Account access:** email/password registration and login; Google sign-in is optional and requires a configured Google OAuth client ID.
- **Saved history:** signed-in users can browse, search, sort, open, and delete previous curricula, or clear their history.
- **Sharing:** generated curricula have shareable links.
- **Exports:** download curricula as PDF or Markdown.
- **Learning progress:** mark topics complete; progress is stored in the browser for that skill.
- **Learning resources:** links to relevant web and YouTube searches for topics.
- **Personalization:** dark/light mode, spell-check assistance where dictionary assets are available, and a profile panel.
- **Database health check:** `GET /health` tests the database connection and returns a non-sensitive status.

CourseCraft currently requires sign-in to generate and save curricula. Guest quota text in older versions of this README was outdated.

## Architecture

- **Backend:** Python, Flask, Flask-SQLAlchemy, SQLAlchemy
- **Database:** SQLite for local development; PostgreSQL when `DATABASE_URL` is configured
- **AI:** Groq Chat Completions API; default model `qwen/qwen3.8-27b`, overridable with `GROQ_MODEL`
- **Frontend:** Jinja templates, HTML, CSS, vanilla JavaScript
- **Deployment:** Render web service running `gunicorn app:app`

The application creates the `user` and `search_history` tables with SQLAlchemy on startup. Use a persistent PostgreSQL database for production; a local SQLite file on an ephemeral hosting filesystem is not a reliable production store.

## Local development

Requirements: Python 3.10 or newer, a Groq API key, and (optionally) a Google OAuth client ID.

1. Clone the repository:

   ```bash
   git clone https://github.com/ambatitharunsai-tech/-CourseCraft.git
   cd -CourseCraft
   ```

2. Create a virtual environment and install packages:

   ```bash
   python -m venv .venv
   source .venv/bin/activate       # macOS/Linux
   # .venv\Scripts\activate      # Windows
   pip install -r requirements.txt
   ```

3. Create your local environment file:

   ```bash
   cp .env.example .env
   ```

   Set `GROQ_API_KEY` and a long random `SECRET_KEY`. Set `GOOGLE_CLIENT_ID` only if you have configured Google Identity Services in Google Cloud Console. Never commit real credentials.

4. Start the app:

   ```bash
   python app.py
   ```

5. Open http://127.0.0.1:5050.

When `DATABASE_URL` is omitted, local development uses SQLite. Set it to a PostgreSQL connection string to exercise the persistent database path locally.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes for deployment | Stable, random Flask session-signing key. Do not use the development fallback in production. |
| `GROQ_API_KEY` | Yes for generation | Server-side Groq API key. Never put this in frontend JavaScript. |
| `GROQ_MODEL` | No | Groq model ID. Defaults to `qwen/qwen3.8-27b`. |
| `DATABASE_URL` | Yes for persistent production storage | PostgreSQL connection string. Omit locally to use SQLite. |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID used to render the Google sign-in button and verify ID tokens. |
| `LOG_LEVEL` | No | Python logging level; defaults to `INFO`. |

See [`.env.example`](.env.example) for a safe template. Values in that file are placeholders only.

## Connect a Supabase PostgreSQL database

1. Create a **separate Supabase project for CourseCraft** (do not reuse another app's student or business tables).
2. In Supabase, open **Connect** and select the PostgreSQL connection string. For Render, prefer the IPv4-compatible **Supavisor session pooler** connection string if your project's direct endpoint is not reachable over IPv4. Use the pooler's session mode for a long-running Flask/Gunicorn service. Add `sslmode=require` when provided by the Supabase connection string.
3. In Render, open the CourseCraft web service settings and add the complete connection string as the secret environment variable `DATABASE_URL`. Keep it server-side; never put it in templates or static JavaScript.
4. Add `SECRET_KEY` and `GROQ_API_KEY` in Render environment settings if not already configured. Set `GOOGLE_CLIENT_ID` if Google login is wanted.
5. Redeploy the service, then open `/health`. A successful connection returns `{"status":"ok","database":"connected"}`.
6. In Supabase Table Editor, verify the `user` and `search_history` tables exist. Registration and curriculum history should persist across application redeploys.

**Existing data:** switching from SQLite to PostgreSQL creates the schema but does not automatically copy local or existing SQLite records. Export/import any data you need before switching production databases.

References: [Supabase PostgreSQL connection options](https://supabase.com/docs/guides/database/connecting-to-postgres) and [SQLAlchemy with Supabase](https://supabase.com/docs/guides/troubleshooting/using-sqlalchemy-with-supabase-FUqebT).

## Render deployment

The existing Render service uses:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`
- **Branch:** `main`
- **Auto deploy:** enabled

After a GitHub commit reaches `main`, Render should start a deployment automatically. Confirm the deployment is live, check the logs, and test `/health`, login/registration, curriculum generation, and history operations. Do not treat the service's “Live” status by itself as proof that the AI provider or database is configured.

## Troubleshooting

- **Generation returns 503:** `GROQ_API_KEY` is missing from the backend environment.
- **Generation returns 502:** the AI provider timed out, rate-limited the request, rejected the model/request, or returned unusable content. Check the Render logs for a safe diagnostic message and verify `GROQ_MODEL`.
- **Generation returns 500 while saving:** check `DATABASE_URL`, the database's availability, and permissions. `/health` verifies connectivity.
- **Login session does not persist:** ensure `SECRET_KEY` is set to a stable random value and do not change it between deploys.
- **Google sign-in is not shown:** set `GOOGLE_CLIENT_ID` in Render and configure the corresponding authorized JavaScript origin in Google Cloud Console. Email/password login remains available without Google sign-in.

## Security notes

- Keep API keys, database passwords, and the Flask session secret in environment variables or the hosting secret manager.
- Google ID tokens are verified against the configured client ID; the former developer bypass is removed.
- User passwords are stored as Werkzeug password hashes, not plaintext.
- Keep user history endpoints behind login and verify ownership before deleting records.
- For production, configure a unique random `SECRET_KEY`, use HTTPS, and keep dependencies updated.

## License

See [LICENSE](LICENSE).
