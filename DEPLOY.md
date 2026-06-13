# Publishing the live app

The app (`07_final_assets/app.py`) is light and self-contained: it reads only the small
aggregate CSVs + chart PNGs in `01_analytics_outputs/`, pulls in **no** raw source data, and
needs **no** secrets. So it's safe and easy to host.

> **Confidentiality:** the `.gitignore` excludes `00_source_materials/` (raw reviews + due-diligence),
> any `*.env`/API-key files, the large intermediate artifacts, and the planning/meta docs — so the repo
> holds only code + aggregate outputs, no confidential source. Streamlit's free tier needs a **public**
> repo, which is fine here because nothing sensitive is committed. (Want it private? Use a paid Streamlit
> tier or Hugging Face Spaces.)

---

## Option A — Streamlit Community Cloud  (recommended: free, durable, purpose-built)

Gives you a permanent `https://<name>.streamlit.app` URL you can send before the interview.

1. **One-time:** make sure `requirements.txt` and `.gitignore` are present (they are).
2. **Put it on GitHub.** From the project root:
   ```bash
   git init
   git add .
   git commit -m "360training reputation-intelligence app"
   gh repo create 360training-reputation-app --public --source=. --push   # needs the gh CLI + GitHub login
   ```
   (Or create the repo in the GitHub web UI and `git remote add origin … && git push -u origin main`.)
3. **Deploy:** go to <https://share.streamlit.io> → sign in with GitHub → **New app** →
   - Repository: your `360training-app`
   - Branch: `main`
   - **Main file path: `07_final_assets/app.py`**
   - **Advanced settings → Python version: 3.12** (the app uses numpy 2.x / pandas 3.x)
   - **Deploy**.
4. In ~2–3 minutes you get the public URL. Share it.

**Good to know:** on the free tier the app *sleeps* after a stretch of no traffic and wakes in a
few seconds on the next visit — fine for sharing a link. RAM is ~1 GB; this app uses a fraction.

---

## Option B — Hugging Face Spaces  (also free + durable)

Create a **Streamlit** Space at <https://huggingface.co/spaces>, then push these files to it. Set the
Space's app file to `07_final_assets/app.py` (or move `app.py` to the root of the Space). Same
`requirements.txt`. A Space can be public or private; the running app is reachable either way.

---

## Option C — Instant temporary link (for a quick look, not durable)

Tunnels the **locally-running** app to a public URL. The link only works while your Mac is awake
and the command is running — good for a live demo, **not** for "send it and walk away."

```bash
# terminal 1 — run the app
./.venv/bin/streamlit run 07_final_assets/app.py

# terminal 2 — expose it
brew install cloudflared
cloudflared tunnel --url http://localhost:8501
# → prints a https://<random>.trycloudflare.com URL
```

(ngrok works the same way: `ngrok http 8501`.)

---

## What gets deployed (the whole footprint)
- `07_final_assets/app.py` — entry point
- `cc2_app_data.py`, `cc2_common.py`, `cc2_d_revenue.py`, `cc2_h_kpi.py` — modules the app imports
- `.streamlit/config.toml` — the theme
- `01_analytics_outputs/` — the 12 aggregate CSVs + `CC2_chart_pack/` PNGs
- `requirements.txt`

Everything else (raw data, due-diligence, other pipeline stages, the PDF/deck, `.venv`) is excluded
by `.gitignore` and not needed to serve the app.
