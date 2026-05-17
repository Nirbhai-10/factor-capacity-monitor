# Factor Capacity & Crowding Monitor — web

Next.js 15 / React 19 / Tailwind / Recharts / KaTeX dashboard for the Factor
Capacity & Crowding Monitor research project.

## Local development

```bash
# 1. Generate the data bundle (requires Python deps in the parent project)
cd ..
python scripts/build_web_data.py     # writes web/lib/data.json

# 2. Run the dev server
cd web
npm install
npm run dev
# → http://localhost:3001
```

## Deploying to Vercel

The cleanest path is **CLI**. Run from `web/`:

```bash
npm install -g vercel        # or pnpm add -g vercel
vercel login                 # opens your browser to auth
vercel                       # first deploy → preview URL
vercel --prod                # promote to production
```

When prompted:
- *Set up and deploy?* → yes
- *Scope?* → your personal account or team
- *Link to existing project?* → no
- *Project name?* → `fcm-web` (or anything)
- *Code directory?* → `./` (we are already inside `web/`)
- *Override settings?* → no (the bundled `vercel.json` already sets framework=nextjs)

Vercel will detect Next.js, install deps, build, and give you a URL like
`https://fcm-web-<hash>.vercel.app`. Subsequent pushes (if you connect a git
repo) deploy automatically.

### Or: deploy from GitHub via the dashboard

1. Push the repo to GitHub.
2. Go to https://vercel.com/new
3. Import the repo, set **Root Directory** = `web`.
4. Click Deploy.

The static `data.json` is committed to the repo, so the build is fully
reproducible without running Python on Vercel.

## Refreshing the data

Whenever you re-run `python scripts/build_web_data.py` the dashboard updates
automatically (dev server hot-reloads; on Vercel, push to trigger a redeploy).
