# Setup guide - ASCII GitHub profile

## 1. Create the special profile repo
GitHub shows a repo's `README.md` on your profile **only if the repo name equals your username**.

1. Go to https://github.com/new
2. Repository name: **Harshini-Nandi**  (must match exactly), set to **Public**
3. Do *not* add a README/license (this project has its own)

## 2. Push this project
```bash
cd Harshini-Nandi
git init
git add .
git commit -m "feat: ASCII profile README"
git branch -M main
git remote add origin https://github.com/Harshini-Nandi/Harshini-Nandi.git
git push -u origin main
```

## 3. Turn on the schedule
* Repo -> **Settings -> Actions -> General -> Workflow permissions -> Read and write permissions** -> Save
* Repo -> **Actions** tab -> *Update profile README* -> **Run workflow** (first run)
* After that it refreshes automatically every 6 hours (edit the `cron` line in
  `.github/workflows/update-readme.yml` to change it).

Optional: to include **private** contributions, create a token at
https://github.com/settings/tokens (classic, scope `read:user`) and save it as a repo secret named `GH_PAT`.

## 4. Tweak the portrait (run locally)
```bash
pip install -r requirements.txt
python generate_ascii.py --width 80            # bigger
python generate_ascii.py --contrast 1.6        # punchier
python generate_ascii.py --invert              # flip light/dark
python generate_ascii.py --keep-bg             # don't cut out the background
python generate_ascii.py --crop 0.05 0 0.75 0.6   # L T R B as fractions of the photo
python update_readme.py                        # rebuild README.md
```
Replace `assets/me.jpeg` with any photo; edit the `OUTLINE` points in `generate_ascii.py`
(or use `--keep-bg`) so the cut-out fits the new picture.

## 5. Change your info
Everything personal lives in `config.json` (email, languages, fallback stats).
Live numbers from the GitHub API override the fallback numbers automatically.

## Project layout
```
Harshini-Nandi/
├── README.md                      <- generated profile (what visitors see)
├── SETUP.md                       <- this guide
├── config.json                    <- your details
├── generate_ascii.py              <- photo -> assets/ascii.txt
├── update_readme.py               <- ascii + live stats -> README.md
├── requirements.txt
├── assets/
│   ├── me.jpeg                    <- source photo
│   └── ascii.txt                  <- generated portrait
└── .github/workflows/update-readme.yml   <- scheduler
```
