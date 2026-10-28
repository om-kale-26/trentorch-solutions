#!/usr/bin/env python3
"""
Regenerates progress.json, README.md, coverage.svg and docs/index.html
for the TrenTorch Data Science track. Runs on every push (see the workflow).

Each top-level folder (e.g. db-sql-select-all) counts as one solved problem.
Category comes from the folder-name prefix (CATEGORIES below) or from an
optional meta.json inside the folder:
    {"category": "SQL & Databases", "difficulty": "easy", "title": "SELECT All Rows"}
"""
import json
import math
import os
import re
import subprocess
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = os.environ.get("GITHUB_REPOSITORY", "om-kale-26/trentorch-solutions")
OWNER, NAME = REPO.split("/")
TRACK = "Data Science"
TRACK_URL = "https://trentorch.com/questions/part-data-science"
PAGES_URL = f"https://{OWNER}.github.io/{NAME}/"

# (display name, total questions on TrenTorch, folder-name prefixes)
# Totals come from trentorch.com/questions/part-data-science.
# Prefixes are matched against the folder name ("db-sql-select-all" -> "db-sql").
# Only "db-sql" is confirmed; fix the others when you see your real folder names.
CATEGORIES = [
    ("Exploratory Data Analysis (EDA)", 17, ["eda"]),
    ("Data Visualization", 22, ["viz", "dv", "visualization"]),
    ("Data Preparation", 13, ["prep", "dp", "data-prep"]),
    ("Data Storage & Retrieval", 12, ["storage", "retrieval", "dsr"]),
    ("SQL & Databases", 51, ["db-sql", "sql"]),
    ("Data Structures & Algorithms", 20, ["dsa", "algo", "ds-algo"]),
]
OTHER = "Other"
IGNORE = {"docs", "scripts", "node_modules"}
PREFIXES = sorted(
    ((p, name) for name, _t, ps in CATEGORIES for p in ps),
    key=lambda x: -len(x[0]),
)


def git(*args):
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        return out or None
    except Exception:
        return None


def classify(slug):
    for prefix, name in PREFIXES:
        if slug == prefix or slug.startswith(prefix + "-"):
            return name, prefix
    return None, None


def read_md(folder):
    text = ""
    for f in sorted(folder.glob("*.md")):
        try:
            text += f.read_text("utf-8", errors="ignore") + "\n"
        except Exception:
            pass
    return text


def find_difficulty(folder, md):
    """Look for easy/medium/hard in every small text file in the folder."""
    texts = [md]
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in {".json", ".txt", ".yml", ".yaml", ".sql", ".py"}:
            try:
                texts.append(f.read_text("utf-8", errors="ignore")[:5000])
            except Exception:
                pass
    # 1) explicit "difficulty: easy" / "difficulty": "easy" / table cell
    for t in texts:
        m = re.search(r"difficulty\W{0,8}(easy|medium|hard)", t, re.I)
        if m:
            return m.group(1).lower()
    # 2) a lone badge/label such as "Easy" or "**Medium**" near the top of a .md
    for line in md.splitlines()[:15]:
        m = re.fullmatch(r"\W*(easy|medium|hard)\W*", line.strip(), re.I)
        if m:
            return m.group(1).lower()
    return ""


def scan():
    items = {}
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in IGNORE:
            continue
        slug = d.name
        meta = {}
        mp = d / "meta.json"
        if mp.exists():
            try:
                meta = json.loads(mp.read_text("utf-8"))
            except Exception:
                print(f"warning: could not parse {mp}")

        category, prefix = classify(slug)
        category = meta.get("category", category)
        if category not in [c[0] for c in CATEGORIES]:
            print(f"warning: no category for folder '{slug}' -> '{OTHER}'. "
                  f"Add a prefix in CATEGORIES or a meta.json.")
            category = OTHER

        md = read_md(d)
        title = meta.get("title")
        if not title:
            m = re.search(r"^#\s+(.+)$", md, re.M)
            if m:
                title = m.group(1).strip()
        if not title:
            rest = slug[len(prefix) + 1:] if prefix else slug
            title = rest.replace("-", " ").strip().title() or slug

        diff = meta.get("difficulty") or find_difficulty(d, md)

        exts = {f.suffix.lower() for f in d.iterdir() if f.is_file()}
        language = "sql" if ".sql" in exts else "python" if ".py" in exts else ""

        first = meta.get("solved_at") or git(
            "log", "--diff-filter=A", "--reverse", "--format=%aI", "--", slug
        )
        first = (first or "").splitlines()[0] if first else None
        last = git("log", "-1", "--format=%aI", "--", slug)
        if not first:  # not committed yet (local run)
            first = last = datetime.now(timezone.utc).isoformat()

        items[slug] = {
            "title": title,
            "difficulty": diff,
            "category": category,
            "path": slug,
            "url": f"https://github.com/{REPO}/tree/main/{slug}",
            "language": language,
            "first_solved_at": first,
            "last_pushed_at": last or first,
        }
    return items


def build_categories(items):
    cats = []
    for name, total, _p in CATEGORIES:
        solved = sum(1 for i in items.values() if i["category"] == name)
        cats.append({"name": name, "total": total, "solved": min(solved, total)})
    extra = sum(1 for i in items.values() if i["category"] == OTHER)
    if extra:
        cats.append({"name": OTHER, "total": extra, "solved": extra})
    return cats


def coverage_svg(cats):
    W, PAD, STEP, SQ, PER_ROW = 880, 20, 14, 10, 60
    y, parts = 24, []
    for c in cats:
        parts.append(f'<text x="{PAD}" y="{y}" class="l">{escape(c["name"])}</text>')
        parts.append(f'<text x="{W - PAD}" y="{y}" class="l" text-anchor="end">'
                     f'{c["solved"]}/{c["total"]}</text>')
        y += 8
        for i in range(c["total"]):
            r, col = divmod(i, PER_ROW)
            cls = "s" if i < c["solved"] else "e"
            parts.append(f'<rect x="{PAD + col * STEP}" y="{y + r * STEP}" '
                         f'width="{SQ}" height="{SQ}" rx="2" class="{cls}"/>')
        y += math.ceil(c["total"] / PER_ROW) * STEP + 24
    H = y - 4
    style = ("<style>.l{font:12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
             "fill:#6e7781}.s{fill:#1a7f37}.e{fill:#57606a;opacity:.75}</style>")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" role="img" aria-label="Data Science coverage">'
            f'{style}{"".join(parts)}</svg>\n')


def readme(items, cats):
    solved = len(items)
    total = sum(c["total"] for c in cats if c["name"] != OTHER)
    done_cats = sum(1 for c in cats if c["solved"] > 0)
    lines = [
        "# TrenTorch Solutions",
        "",
        f"My data science practice from [TrenTorch]({TRACK_URL}). "
        "Every solution here was written by hand.",
        "",
        f"**{solved}** solved of {total} · {done_cats} of {len(CATEGORIES)} topics started",
        "",
        "[![Coverage](coverage.svg)](coverage.svg)",
        "",
        f"[**Browse the interactive portfolio**]({PAGES_URL}) to replay this filling in over time.",
        "",
    ]
    by_date = lambda i: i["first_solved_at"]
    for c in cats:
        mine = sorted((i for i in items.values() if i["category"] == c["name"]), key=by_date)
        if not mine:
            continue
        lines += [f"## {c['name']}", "",
                  "| Problem | Difficulty | Solved | |", "|---|---|---|---|"]
        for i in mine:
            lines.append(f"| {i['title']} | {i['difficulty'] or '-'} | "
                         f"{i['first_solved_at'][:10]} | [solution]({i['url']}) |")
        lines.append("")
    lines += ["---", "",
              "*This file is regenerated by a GitHub Action on every push.*", ""]
    return "\n".join(lines)


PORTFOLIO = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Data Science portfolio</title>
<style>
:root{--bg:#fff;--fg:#1f2328;--mut:#656d76;--emp:#d0d7de;--ok:#2da44e;--new:#bf8700}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mut:#8b949e;--emp:#30363d}}
body{margin:0;padding:2rem 1rem;background:var(--bg);color:var(--fg);
font:14px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
main{max-width:900px;margin:auto}
h1{font-size:1.4rem;margin:0 0 .25rem}.mut{color:var(--mut)}
.row{display:flex;justify-content:space-between;margin-top:1.2rem}
.grid{display:flex;flex-wrap:wrap;gap:4px;margin-top:.4rem}
.sq{width:10px;height:10px;border-radius:2px;background:var(--emp)}
.sq.ok{background:var(--ok)}.sq.new{background:var(--new)}
.ctl{display:flex;gap:1rem;align-items:center;margin:1.5rem 0}
.ctl input{flex:1}button{font:inherit;padding:.3rem .9rem;cursor:pointer}
</style></head><body><main>
<h1>Data Science portfolio</h1>
<div class="mut" id="sub"></div>
<div class="ctl"><button id="play">Play</button>
<input id="seek" type="range" min="0" value="0"><span id="when"></span></div>
<div id="cats"></div>
<p class="mut" id="latest"></p>
</main>
<script>
const DATA = __DATA__;
const items = DATA.items.slice().sort((a, b) => a.date.localeCompare(b.date));
const seek = document.getElementById("seek"), when = document.getElementById("when");
seek.max = items.length; seek.value = items.length;
document.getElementById("sub").textContent =
  items.length + " solved · track: " + DATA.track;
function render() {
  const n = +seek.value, shown = items.slice(0, n);
  const root = document.getElementById("cats"); root.textContent = "";
  for (const c of DATA.categories) {
    const mine = shown.filter(i => i.category === c.name);
    const row = document.createElement("div"); row.className = "row";
    row.innerHTML = "<span></span><span class='mut'></span>";
    row.children[0].textContent = c.name;
    row.children[1].textContent = mine.length + "/" + c.total;
    const grid = document.createElement("div"); grid.className = "grid";
    const last = shown[n - 1];
    for (let k = 0; k < c.total; k++) {
      const sq = document.createElement("div"); sq.className = "sq";
      if (k < mine.length) {
        sq.classList.add("ok");
        if (last && mine[k] === last) sq.classList.add("new");
      }
      grid.appendChild(sq);
    }
    root.append(row, grid);
  }
  const last = shown[n - 1];
  when.textContent = last ? last.date.slice(0, 10) : "start";
  document.getElementById("latest").textContent =
    last ? "Latest: " + last.title : "";
}
seek.oninput = render;
let timer = null; const btn = document.getElementById("play");
btn.onclick = () => {
  if (timer) { clearInterval(timer); timer = null; btn.textContent = "Play"; return; }
  if (+seek.value >= items.length) seek.value = 0;
  btn.textContent = "Pause";
  timer = setInterval(() => {
    seek.value = +seek.value + 1; render();
    if (+seek.value >= items.length) { clearInterval(timer); timer = null; btn.textContent = "Play"; }
  }, 450);
};
render();
</script></body></html>
"""


def portfolio(items, cats):
    data = {
        "track": TRACK,
        "categories": cats,
        "items": [{"title": i["title"], "category": i["category"],
                   "date": i["first_solved_at"]} for i in items.values()],
    }
    blob = json.dumps(data).replace("</", "<\\/")
    return PORTFOLIO.replace("__DATA__", blob)


def main():
    items = scan()
    cats = build_categories(items)
    stamp = max((i["last_pushed_at"] for i in items.values()), default="")
    (ROOT / "progress.json").write_text(
        json.dumps({"generated_at": stamp, "track": TRACK, "items": items}, indent=2) + "\n",
        "utf-8")
    (ROOT / "coverage.svg").write_text(coverage_svg(cats), "utf-8")
    (ROOT / "README.md").write_text(readme(items, cats), "utf-8")
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(portfolio(items, cats), "utf-8")
    print(f"Done: {len(items)} solved.")


if __name__ == "__main__":
    main()
