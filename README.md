# Word Fix: Educational Word Game

Players complete a word with missing letters (A__LE → APPLE) by choosing from options.
Three difficulty levels, topics, per-level leaderboards. No database, no build step.

This README has two parts: **A. Functional setup** (how the game plays and how a teacher runs it)
and **B. Technical setup** (how an engineer installs, configures, tests and deploys it).

---

# A. Functional setup

## A1. How a player plays
1. Open the game.
2. **Choose a nickname** from the 4 names the game suggests (press *Show other names* for more). This is the guest "login". No password, no real name.
3. **Choose a difficulty** (see A2).
4. **Choose a topic** (science, history, ...) or *All topics*.
5. Press **Play**. Each game has 10 words (setting: `rounds`).
6. For each word, look at the blanks and pick the missing letters from the 4 options (click, or press keys 1-4).
7. The game shows right or wrong at once, reveals the word, and updates the score. Press **Next word**.
8. After the last word, the final score is shown and sent to the leaderboard (see A4).

## A2. Difficulty levels (decided by the number of blanks)
| Level | Blanks | Example (APPLE) | Example options |
|---|---|---|---|
| Simple `_` | 1 | A_PLE | `P`, `L`, `T`, `R` |
| Medium `__` | 2 | A__LE | `PP`, `PL`, `BB`, `TR` |
| Hard `___` | 3 | e.g. `EXP___ER` for EXPLORER | three-letter groups |

- The first and last letters always stay visible.
- The hidden letters are always one block (A__LE, never A_P_E).
- Short words may not fit the harder levels (Hard needs 5+ letters). The game counts only words that fit the chosen level and says "N words this game".
- Wrong options are made to look plausible and are never another real word from your list.

## A3. Marking (scoring)
- Right answer: **+3**. Wrong answer: **−4**. No time limit.
- Score can go below zero. A 10-word game ranges from **−40 to +30**.
- Example: 7 right and 3 wrong = 21 − 12 = **+9**.
- Guessing among 4 options loses points on average (1 in 4 right gives −2.25 per word), so the game favours knowing over guessing.
- The same points apply at every level, so the levels have **separate leaderboards**.

## A4. Leaderboard rules
- One row per nickname **per level**, showing that nickname's **best** score. Top 10 shown (setting: `leaderboard.showTop`).
- Tabs switch between Simple, Medium and Hard boards.
- Your own nickname is highlighted.
- **Local test mode:** the score is saved automatically when the game ends.
- **GitHub (online) mode:** the player presses *Send score to leaderboard*, which opens a pre-filled GitHub issue. They press *Submit new issue*, a bot checks the score and adds it, and the board updates after the workflow runs. Accepted issues are closed; rejected scores get a comment and a `score-rejected` label. Players need a free GitHub account.
- Nicknames are guest names only; the game does not collect real names. The public leaderboard stores nickname, best score, number of plays, last topic, date, and processed GitHub issue numbers to prevent duplicate score submissions.

## A5. What a teacher or content owner can do
| Task | How |
|---|---|
| Add or change words | Edit `words.json` (see B4) |
| Add a topic | Add a new key in `words.json`, e.g. `"geography": ["RIVER", ...]` |
| Add a hint to a word | `{ "word": "APPLE", "hint": "A round fruit" }` |
| Add words automatically | GitHub Actions → *Update words* (see B8) |
| Change points, number of words, level names | Edit `config.json` (see B3) |
| Remove an inappropriate or fake entry | `python scripts/admin.py remove NICKNAME` |
| Start a fresh term | `python scripts/admin.py reset` |
| See all entries | `python scripts/admin.py list` |

In GitHub mode, commit the changed `leaderboard.json` after running the admin script.

## A6. Suggested classroom use
1. Pick one topic matching the current lesson and one level (start on Simple).
2. Students play 2-3 rounds (about 3 minutes each) on shared or personal devices.
3. Debrief: which words were hard? Why was the wrong option tempting?
4. Move up a level when most students score above +15.
5. Use the leaderboard for class motivation only, not as a grade.

---

# B. Technical setup

## B1. Requirements
- **Local testing:** Python 3.8+ and any modern browser. No packages to install.
- **Deployment:** a GitHub account and a public repository (GitHub Pages, Actions and Issues enabled).
- **Optional:** an `ANTHROPIC_API_KEY` for AI-generated word lists. Without it the free Datamuse word API is used.

## B2. Files
```
word-game/
├── index.html            page structure
├── style.css             look and feel
├── game.js               all game logic (no libraries)
├── config.json           ALL settings (B3). Read by the game AND by the Python scripts
├── words.json            word bank (B4)
├── leaderboard.json      scores (written by server.py or by the GitHub Action)
├── server.py             local test server and score API
├── scripts/
│   ├── common.py         config loading + score validation rules (shared)
│   ├── process_score.py  used by the GitHub Action to add a score
│   ├── update_words.py   used by the GitHub Action to add words
│   └── admin.py          list / remove / reset leaderboard entries
└── .github/workflows/
    ├── score.yml         "Add score to leaderboard"
    └── update-words.yml  "Update words" (run by hand)
```

## B3. Settings you can change (`config.json`)
JSON has no comments, so every setting is explained here. Bad values stop the Python scripts with a clear message; the browser reports a missing file.

| Setting | Default | Meaning and limits |
|---|---|---|
| `title` | `"Word Fix"` | Game name shown on the page |
| `rounds` | `10` | Words per game, 1-100. Also the maximum the server accepts |
| `pointsRight` | `3` | Points for a right answer. Whole number, must be greater than `pointsWrong` |
| `pointsWrong` | `-4` | Points for a wrong answer (use `0` for no penalty) |
| `optionsPerQuestion` | `4` | Choices shown, 2-6. A 1-blank vowel has only 4 other vowels, so 5 or 6 can occasionally show fewer |
| `wordLength.min / max` | `4 / 14` | Allowed word length. Words outside are skipped with a console warning, and the Action only adds words in range |
| `difficulties` | simple 1, medium 2, hard 3 | Each key is `{ "label": "...", "blanks": N }`. Key: lowercase letters/digits. Add, remove or rename levels freely |
| `defaultDifficulty` | `"simple"` | Must be a key in `difficulties` |
| `leaderboard.showTop` | `10` | Rows shown per level |
| `leaderboard.storeLimitPerLevel` | `100` | Rows kept per level in `leaderboard.json` |
| `nicknames.suggestionsShown` | `4` | How many names are offered |
| `nicknames.adjectives / animals` | 10 each | Name parts. Letters only, 2-10 characters, no spaces. A nickname = adjective + animal + 2 digits |
| `github.owner / repo` | `""` | GitHub mode only. Leave empty on `name.github.io/repo`; fill in if you use a custom domain |

**Adding a level:** add `"expert": { "label": "Expert", "blanks": 4 }`. Words need at least `blanks + 2` letters to be used at that level. Leaderboard tabs and the validation update automatically.

**Rule of thumb:** after changing points or rounds, restart `server.py`. The server and the Action use the same file, so the browser and the validator never disagree.

## B4. Words (`words.json`)
```json
{
  "general": [
    { "word": "APPLE", "hint": "A round fruit, often red or green" },
    "ORANGE", "BANANA"
  ],
  "science": ["PLANET", "GRAVITY"]
}
```
- Each key is a topic. Each item is a plain word or `{ "word", "hint" }` (hint optional).
- The game checks only the format: letters A-Z (case ignored), no spaces or hyphens, and length within `wordLength`. It does **not** check whether a string is a real English word or is correct for its topic.
- Format-invalid words are skipped and listed in the browser console (F12); duplicates are ignored. Review the word list yourself, especially words added automatically.
- Reload the page after editing. 

## B5. Run and test locally (no GitHub needed)
```
python server.py            # http://localhost:8000, this computer only
python server.py --lan      # phones/computers on your Wi-Fi can open the printed address (see B5a)
python server.py --port 9000
```
- Do not double-click `index.html`: browsers block `words.json` and `config.json` on `file://`. The game shows a message if you do.
- `server.py` replaces the GitHub Action while testing: it receives each finished game at `POST /api/score`, validates it and writes `leaderboard.json`.
- **You do not need GitHub Actions to test.** Local testing needs only Python.
- Test online mode without a server: open `http://localhost:8000/?mode=github`. This shows the "Send score" button and builds the issue link (set `github.owner` and `github.repo` in `config.json` to see a real link).
- Test the Action scripts on your computer:
  ```
  # score script (what score.yml runs)
  ISSUE_BODY='{"nick":"BraveFox22","score":9,"rounds":10,"difficulty":"simple"}' python scripts/process_score.py
  # words script (needs internet; add ANTHROPIC_API_KEY to use Claude)
  DOMAIN=science QUERY=chemistry COUNT=5 python scripts/update_words.py
  ```
  On Windows PowerShell set variables first: `$env:ISSUE_BODY='...'; python scripts/process_score.py`.
- Reset test data afterwards: `python scripts/admin.py reset`.
- Optional: the open-source tool `act` can run the `.github/workflows` files locally in Docker. It is not required and was not used in testing.

## B5a. Test from a phone or another computer (same Wi-Fi)
1. On the computer run `python server.py --lan`. It prints the address to use, for example `http://192.168.1.23:8000`.
2. On the phone, join the **same Wi-Fi** as the computer. Turn **mobile data and any VPN off**. Type the printed address in the browser, starting with `http://` (not `https://`).
3. The moment the phone reaches the computer, the terminal prints a line starting `Connected:`. Scores played on phones are saved to the computer's `leaderboard.json`, so several phones can share one leaderboard. This is a good classroom multiplayer test.

**Quick self-test:** 

| Symptom | Likely cause | Fix |
|---|---|---|
| Phone times out and the terminal never prints `Connected:` | **Computer firewall** | **Windows:** when the "Windows Security Alert" for Python appears, tick **Private** (and **Public** if your Wi-Fi is marked public), then Allow. If you closed it: Start menu → "Allow an app through Windows Firewall" → Change settings → find *python* → tick Private and Public. **Mac:** System Settings → Network → Firewall → allow incoming connections for Python, or switch the firewall off for the test. **Linux:** `sudo ufw allow 8000/tcp` |
| Same as above, and the firewall is fine | **Wi-Fi blocks device-to-device traffic** ("client isolation"). Common on guest Wi-Fi, schools, offices, cafes | Use the main (non-guest) network, ask the network owner to switch isolation off, or use the hotspot method below |
| Phone shows an error such as "cannot connect securely" | Typed `https://` or left out `http://` | Type `http://` and the address exactly |
| Computer cannot open the printed address either | **Wrong address.** A computer can have several network adapters (VirtualBox, WSL, VPN). The first printed address is usually the Wi-Fi one | Try the others. Your Wi-Fi address starts with the same first three numbers as the phone's. Windows: `ipconfig`, look under Wi-Fi, "IPv4 Address". Mac: `ipconfig getifaddr en0`. Linux: `hostname -I` |
| `Cannot start on port 8000` | Another copy is already running | Close it, or use `python server.py --lan --port 8001` |

**Hotspot method (works when the Wi-Fi blocks devices):** switch on the phone's personal hotspot, connect the computer to it, run `python server.py --lan` and use the printed address on the phone. This usually works, but not on every phone or carrier.

Free tunnelling tools can also give a temporary internet address for `localhost:8000`. They were not tested with this project and they make your test server public, which has no login, so use them only briefly.

Stop the server (Ctrl+C) when you finish. `--lan` lets everyone on that network reach it.

## B6. Modes at a glance
| | Local mode | GitHub (online) mode |
|---|---|---|
| Needs | Python | GitHub Pages, Actions, Issues |
| Detected when | `/api/ping` answers | no server answers (or `?mode=github`) |
| Score saved by | `server.py` | `score.yml` Action |
| Player action | none | press *Send score*, then *Submit new issue* |
| Leaderboard delay | instant | about a minute |
| Players | anyone who can reach your computer | anyone on the internet |

## B7. Deploy to GitHub
1. Create a **public** repository and upload all files, keeping the `.github` folder.
2. *Settings → Pages →* Deploy from a branch → `main`, folder `/ (root)`.
3. *Settings → Actions → General → Workflow permissions →* **Read and write permissions**.
4. *Settings → General → Features →* Issues enabled.
5. Open `https://YOUR-NAME.github.io/REPO-NAME/` after the first Pages build (a few minutes).
6. Play one game and send the score. In the *Actions* tab, "Add score to leaderboard" should run and the issue should close.
7. Before launch, clear test scores: `python scripts/admin.py reset`, commit and push.

How scores flow: browser → pre-filled issue titled `SCORE|nick|score` → `score.yml` scans and validates all open score issues → accepted scores are committed together to `leaderboard.json` → accepted issues are closed → Pages republishes. Each issue number is recorded to prevent duplicate scoring if a workflow retries. Rejected scores receive a comment and `score-rejected` label. The workflow also scans for unprocessed scores every five minutes, recovering score issues if GitHub replaces a pending workflow run. If a score does not show, check the *Actions* tab and its run-log artifact.

## B8. Update words with GitHub Actions
*Actions → Update words → Run workflow*, then fill in:
- **domain**: topic key in `words.json` (new names create new topics), e.g. `science` or `Nepal history` (spaces become underscores, so it is saved as `nepal_history`)
- **query**: what to find words about, e.g. `chemistry` or `grade 6 water cycle`
- **count**: how many to add (max 100)

Words are converted to capitals, checked for letters only, de-duplicated, length-filtered by `wordLength`, and committed to `words.json`.
- **No key set:** the free Datamuse API is used (quick, but results are loose matches, so review them). The run log prints which provider was selected.
- **With `ANTHROPIC_API_KEY`** (repo *Settings → Secrets and variables → Actions*): Claude writes school-appropriate words. Change the model with the `MODEL` line in `update-words.yml` (default `claude-sonnet-5-5`).
- Always skim new words before students use them.

## B8a. Run logs
- When running `python server.py`, terminal output is also appended to `run.log` in the project folder. Git ignores this file, so it will not be committed.
- Each **Add score to leaderboard** and **Update words** GitHub Actions run writes its `run.log` outside the repository checkout and uploads it as an artifact. This keeps the log from interfering with Git commits or pushes. Open the workflow run in **Actions** and download the artifact from its **Artifacts** section.
- The artifact captures the Python script and related save/close command output. GitHub's setup and checkout messages remain available in the workflow's regular run log.

## B9. Login: what is included and what is not
| Option | Status | Notes |
|---|---|---|
| **Guest nickname** | Included | Program-suggested names, remembered in the browser (`localStorage`). Works in both modes |
| **GitHub account identity** | Included in GitHub mode | The player must be signed in to GitHub to submit the issue. The game does not read or store the GitHub name |
| **Google / Facebook / GitHub sign-in inside the game** | **Not included** | See below |

Why not social login: OAuth needs a secret kept on a server and a place to store accounts. GitHub Pages is static, so a hosted service is required (for example Firebase Authentication or Supabase Auth, both with a database for scores). It was not built because it adds a database and an account system, it cannot be tested with only Python, and many social platforms require users to be 13 or older, which matters for school pupils. If you add it later, keep the guest nickname as the default, store only nickname and score, and replace the two score paths: `finish()` in `game.js` (submit) and `loadBoard()` (read). The scoring rules in `scripts/common.py` should be re-implemented on the server side of whatever service you choose.

## B10. Security and data
- The server and the Action accept only: nickname `A-Za-z0-9` (3-24), a known difficulty, whole numbers, and a score that is arithmetically possible for `rounds`, `pointsRight` and `pointsWrong`. Everything else is rejected.
- This stops typos and crude tampering. It **cannot** stop someone sending a perfect score from a made-up honest-looking game. Treat the leaderboard as motivation, not assessment.
- `leaderboard.json` is public in a public repo. It contains leaderboard nicknames/scores and processed public issue numbers used to prevent duplicate submissions.
- `server.py` serves every file in the folder and has no login. Use it for testing or on a trusted classroom network only, never on the open internet.
- Leaderboard text is written to the page with `textContent`, so a tampered JSON cannot inject HTML.

## B11. Troubleshooting
| Symptom | Fix |
|---|---|
| "Could not load the game files" | You opened `index.html` directly. Run `python server.py` |
| Play button greyed out | Pick a nickname, or the topic has no words long enough for this level |
| "config.json problem: ..." in the terminal | Fix the named setting (B3) |
| A word never appears | It is outside `wordLength`, contains non-letters, or is too short for the level. Check the browser console (F12) |
| Phone cannot open the game | See **B5a** (firewall, Wi-Fi isolation, wrong address) |
| Local score not saved | Check the terminal running `server.py`; the on-screen message gives the reason |
| GitHub: score not on the board | *Actions* tab: did "Add score to leaderboard" run? Is *Read and write permissions* on? Is the issue title still `SCORE|...`? |
| GitHub: Update words fails | Check the `ANTHROPIC_API_KEY` secret name, or run without it to use Datamuse |
| Board looks old after an update | Wait a minute for Pages to rebuild, then hard refresh (Ctrl+F5) |

## B12. Tested
LAN address detection, serving the game through a non-loopback address, saving a score sent like a phone would, the `Connected:` message and the default (this computer only) mode were tested on one machine. 

The two GitHub workflow files were checked for valid YAML but were **not run on real GitHub**, and the live Datamuse and Claude calls were not run. Do step B7.6 once after deploying to confirm.


## Common questions
### how the nickname is generated?
Nicknames are generated entirely in the browser.

The code randomly combines:
One adjective from config.json
One animal name
A random number from 10 to 99
The formula is: Adjective + Animal + Number
Example: CleverYak12
