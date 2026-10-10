"""
Build README.md: ASCII portrait on the left, terminal-style stats panel on the right.

* Live stats come from the GitHub API (set GITHUB_TOKEN for commits / PRs / sparkline).
* If the API is unreachable, the numbers in config.json -> fallback_stats are used.
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

try:
    import requests
except ImportError:                      # lets the script still run offline
    requests = None

ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(ROOT, "config.json")))
USER = CFG["username"]
TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT")
HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


# ------------------------------------------------------------------ data
def api(path):
    r = requests.get(f"https://api.github.com{path}", headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def graphql(query):
    r = requests.post("https://api.github.com/graphql", json={"query": query},
                      headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def humanize(created_at):
    start = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    y = now.year - start.year
    m = now.month - start.month
    d = now.day - start.day
    if d < 0:
        m -= 1
        d += 30
    if m < 0:
        y -= 1
        m += 12
    parts = []
    if y: parts.append(f"{y} year{'s' * (y != 1)}")
    if m: parts.append(f"{m} month{'s' * (m != 1)}")
    parts.append(f"{d} day{'s' * (d != 1)}")
    return ", ".join(parts)


def fetch_live():
    s = dict(CFG["fallback_stats"])
    langs = {}
    spark = []
    if requests is None:
        return s, langs, spark, False
    try:
        u = api(f"/users/{USER}")
        repos, page = [], 1
        while True:
            chunk = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
            repos += chunk
            if len(chunk) < 100:
                break
            page += 1
        s["repos"] = u["public_repos"]
        s["followers"] = u["followers"]
        s["stars"] = sum(r["stargazers_count"] for r in repos)
        s["forks"] = sum(r["forks_count"] for r in repos)
        s["uptime"] = humanize(u["created_at"])
        own = [r for r in repos if not r["fork"]]
        if own:
            top = max(own, key=lambda r: (r["stargazers_count"], r["pushed_at"]))
            s["top_repo"] = f"{top['name']} ({top['stargazers_count']} *)"
        cnt = Counter(r["language"] for r in own if r["language"])
        tot = sum(cnt.values()) or 1
        langs = {k: round(100 * v / tot) for k, v in cnt.items()}
    except Exception as e:
        print("REST fetch failed, using fallback:", e, file=sys.stderr)
        return s, langs, spark, False

    if TOKEN:
        try:
            g = graphql(f'''{{ user(login:"{USER}") {{
              repositoriesContributedTo(first:1, contributionTypes:[COMMIT,PULL_REQUEST,ISSUE]) {{ totalCount }}
              pullRequests {{ totalCount }}
              issues {{ totalCount }}
              contributionsCollection {{
                totalCommitContributions
                totalPullRequestReviewContributions
                contributionCalendar {{ totalContributions weeks {{ contributionDays {{ contributionCount date }} }} }}
              }} }} }}''')["user"]
            cc = g["contributionsCollection"]
            s["commits"] = cc["totalCommitContributions"]
            s["reviews"] = cc["totalPullRequestReviewContributions"]
            s["prs"] = g["pullRequests"]["totalCount"]
            s["issues"] = g["issues"]["totalCount"]
            s["contributed"] = g["repositoriesContributedTo"]["totalCount"]
            s["last12"] = cc["contributionCalendar"]["totalContributions"]
            weeks = cc["contributionCalendar"]["weeks"]
            for i in range(0, len(weeks), 4):               # ~13 buckets of 4 weeks
                spark.append(sum(d["contributionCount"] for w in weeks[i:i + 4]
                                 for d in w["contributionDays"]))
        except Exception as e:
            print("GraphQL failed, keeping REST/fallback numbers:", e, file=sys.stderr)
    return s, langs, spark, True


# ------------------------------------------------------------------ layout
def dotted(label, value, width):
    value = str(value)
    dots = max(2, width - len(label) - len(value) - 3)
    return f". {label}: " + "." * dots + f" {value}"


def section(title, width):
    return f"- {title} " + "-" * (width - len(title) - 3)


def sparkline(values):
    if not values:
        return ""
    bars = "▁▂▃▄▅▆▇█"
    hi = max(values) or 1
    return "".join(bars[min(7, int(v / hi * 7))] if v else "▁" for v in values)


def build_panel(s, langs, spark):
    w = CFG["panel_width"]
    names = []
    for name in CFG["languages"]:
        names.append(f"{name} {langs[name]}%" if name in langs else name)
    lang_text = ", ".join(names)

    lines = [f"{USER}@github", "-" * w]
    if s.get("uptime"):
        lines.append(dotted("Uptime", s["uptime"], w))
    lines.append(dotted("Languages", lang_text, w))
    lines += ["", section("Contact", w),
              dotted("Email", CFG["email"], w),
              dotted("GitHub", CFG["github_url"], w),
              "", section("GitHub Stats", w),
              pair(("Repos", s["repos"]), ("Stars", s["stars"])),
              pair(("Forks", s["forks"]), ("Followers", s["followers"])),
              pair(("Commits", s["commits"]), ("Contributed", s["contributed"])),
              pair(("PRs", s["prs"]), ("Issues", s["issues"]))]
    if s.get("top_repo"):
        lines.append(dotted("Top repo", s["top_repo"], w))
    if "last12" in s or spark:
        lines += ["", section("Last 12 Months", w),
                  pair(("Contributions", s.get("last12", sum(spark))), ("Reviews", s["reviews"]))]
        if spark:
            lines.append(". " + sparkline(spark))
    return lines


def pair(a, b, w=24):
    """Two stats side by side:  . Repos: ..... 14  |  Stars: ..... 4"""
    return dotted(*a, w) + "  |  " + dotted(*b, w)[2:]


def side_by_side(art, panel, gap=4):
    art = art.strip("\n").splitlines()
    aw = max(len(l) for l in art)
    n = max(len(art), len(panel))
    top = max(0, (len(art) - len(panel)) // 2)          # vertically centre the panel
    out = []
    for i in range(n):
        a = art[i] if i < len(art) else ""
        j = i - top
        p = panel[j] if 0 <= j < len(panel) else ""
        out.append((a.ljust(aw) + " " * gap + p).rstrip())
    return "\n".join(out)


TEMPLATE = """```text
{block}
```

## Hi there 👋

I'm **{name}** - I build things with **Java**, **Jupyter Notebooks**, **HTML** and **SQL**.

- 📫 Reach me at **{email}**
- 🔭 Always learning, always building

<sub>Auto-updated daily by GitHub Actions · last refresh: {stamp}</sub>
"""


def main():
    art = open(os.path.join(ROOT, "assets", "ascii.txt")).read()
    s, langs, spark, live = fetch_live()
    block = side_by_side(art, build_panel(s, langs, spark))
    readme = TEMPLATE.format(block=block, name=CFG["display_name"], email=CFG["email"],
                             stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    open(os.path.join(ROOT, "README.md"), "w").write(readme)
    print(f"README.md written ({'live' if live else 'fallback'} stats)")


if __name__ == "__main__":
    main()
