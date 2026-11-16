"""Render the neofetch-style profile card (dark_mode.svg / light_mode.svg).

The left half is an ASCII spiral galaxy generated procedurally; the right half
is profile info plus live GitHub stats. Run by .github/workflows/update.yml
daily. Needs GH_TOKEN (or GITHUB_TOKEN) in the environment for stats; without
one it renders with placeholder stats.
"""

import json
import math
import os
import random
import urllib.request
from html import escape

USER = "Jynx-hub"

# ---- galaxy -----------------------------------------------------------------

ART_W, ART_H = 40, 25
RAMP = " .'`,:;~+*=x%#&@"


def galaxy():
    """Return rows of (char, tier) cells; tier 0=core .. 4=outer/background."""
    rnd = random.Random(426)
    cx, cy = (ART_W - 1) / 2, (ART_H - 1) / 2
    tilt = math.radians(-28)
    arms, twist = 2, 2.6
    rows = []
    for y in range(ART_H):
        row = []
        for x in range(ART_W):
            # characters are ~2x taller than wide; squash y, then tilt + flatten
            dx, dy = (x - cx) / cx, (y - cy) / cy * 1.05
            rx = dx * math.cos(tilt) - dy * math.sin(tilt)
            ry = (dx * math.sin(tilt) + dy * math.cos(tilt)) / 0.62
            r = math.hypot(rx, ry)
            theta = math.atan2(ry, rx)

            core = math.exp(-(r / 0.2) ** 2) * 1.3
            arm_phase = arms * (theta - twist * math.log(r + 0.05))
            arm = (0.5 + 0.5 * math.cos(arm_phase)) ** 2 * math.exp(-r / 0.75)
            disk = 0.22 * math.exp(-r / 0.45)
            d = core + arm * 1.5 + disk + rnd.uniform(-0.1, 0.1)

            if r > 1.08 or d < 0.16:
                # empty space with sparse background stars
                roll = rnd.random()
                ch = "*" if roll < 0.012 else "." if roll < 0.04 else " "
                row.append((ch, 4))
                continue
            ch = RAMP[min(len(RAMP) - 1, max(1, int(d * (len(RAMP) - 1))))]
            tier = 0 if r < 0.14 else 1 if r < 0.3 else 2 if r < 0.55 else 3
            row.append((ch, tier))
        rows.append(row)
    return rows


# ---- stats ------------------------------------------------------------------

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, first: 100, privacy: PUBLIC) {
      totalCount
      nodes { stargazerCount }
    }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST], first: 1) { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
    }
  }
}
"""


def fetch_stats():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        return {"repos": "?", "contributed": "?", "stars": "?", "followers": "?",
                "commits": "?", "joined": "?"}
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-card"},
    )
    u = json.load(urllib.request.urlopen(req))["data"]["user"]
    cc = u["contributionsCollection"]
    return {
        "repos": u["repositories"]["totalCount"],
        "contributed": u["repositoriesContributedTo"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "joined": u["createdAt"][:4],
    }


# ---- info panel -------------------------------------------------------------

INFO_W = 58  # characters per info line


def fmt(n):
    return f"{n:,}" if isinstance(n, int) else str(n)


def info_lines(s):
    """Each line is a list of (text, class) segments, INFO_W chars wide."""

    def header(title):
        t = f"{title} "
        return [(t, "key-h"), ("—" * (INFO_W - len(t)), "dim")]

    def kv(key, value):
        parts = key.split(".")
        segs = [(". ", "dim")]
        for i, p in enumerate(parts):
            if i:
                segs.append((".", "dim"))
            segs.append((p, "key"))
        segs.append((":", "dim"))
        used = 2 + len(key) + 1 + 1 + len(value)
        segs.append((" " + "." * max(1, INFO_W - used - 1) + " ", "dim"))
        segs.append((value, "val"))
        return segs

    def pair(k1, v1, k2, v2, split=30):
        left = kv(k1, v1)
        # shrink the left line to `split` chars by trimming its dot leader
        dots = left[-2][0]
        left[-2] = (" " + "." * (len(dots) - (INFO_W - split) - 2) + " ", "dim")
        right_used = 3 + len(k2) + 1 + 1 + len(v2)
        return left + [(" | ", "dim"), (k2, "key"), (":", "dim"),
                       (" " + "." * max(1, INFO_W - split - right_used - 1) + " ", "dim"),
                       (v2, "val")]

    blank = [(".", "dim")]
    return [
        [("steven", "key-h"), ("@", "dim"), ("ortega ", "key-h"), ("—" * (INFO_W - 14), "dim")],
        kv("OS", "macOS, Linux, AWS"),
        kv("School", "Data Science @ UT Austin '29"),
        kv("Employer", "Patel Gaines"),
        kv("Current Role", "Full-Stack Developer"),
        kv("IDE", "VS Code, Claude Code"),
        blank,
        kv("Languages.Programming", "TypeScript, Python, SQL, Java"),
        kv("Languages.Stack", "Next.js, React, Node, Supabase"),
        kv("Languages.ML", "PyTorch, scikit-learn"),
        blank,
        kv("Shipped.Founder", "Krowe (100+ users)"),
        kv("Shipped.Awards", "1st @ CQ Hacks 2026"),
        blank,
        header("- Contact"),
        kv("Email", "steven.ortega426@gmail.com"),
        kv("LinkedIn", "stevenortega3"),
        kv("Portfolio", "stevenortega.dev"),
        blank,
        header("- GitHub Stats"),
        pair("Repos", fmt(s["repos"]), "Stars", fmt(s["stars"])),
        pair("Commits", fmt(s["commits"]), "Followers", fmt(s["followers"])),
        pair("Contributed", fmt(s["contributed"]), "Joined", s["joined"]),
    ]


# ---- svg --------------------------------------------------------------------

THEMES = {
    "dark": {
        "bg": "#161b22", "dim": "#616e7f", "key": "#ffa657", "key-h": "#c9d1d9",
        "val": "#a5d6ff",
        "tiers": ["#fff4d6", "#ffb3e6", "#c58cff", "#7a8cff", "#8b949e"],
    },
    "light": {
        "bg": "#f6f8fa", "dim": "#c2cfde", "key": "#953800", "key-h": "#24292f",
        "val": "#0a3069",
        "tiers": ["#bf8700", "#bf3989", "#8250df", "#0550ae", "#8c959f"],
    },
}

FONT = 16
CHAR_W = 9.63  # ConsolasFallback/monospace advance at 16px
LINE_H = 20
PAD_X, PAD_Y = 15, 30
GAP = 3  # chars between art and info


def render(theme, art, info):
    t = THEMES[theme]
    info_x = PAD_X + (ART_W + GAP) * CHAR_W
    width = round(info_x + INFO_W * CHAR_W + PAD_X)
    rows = max(len(art), len(info))
    height = PAD_Y + rows * LINE_H

    css = "".join(
        f".{c}{{fill:{t[c]}}}" for c in ("dim", "key", "key-h", "val")
    ) + "".join(f".g{i}{{fill:{c}}}" for i, c in enumerate(t["tiers"]))

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" '
        f'width="{width}px" height="{height}px" font-size="{FONT}px">',
        f"<style>@font-face{{src:local('Consolas'),local('Consolas Bold');font-family:'ConsolasFallback';"
        f"font-display:swap;-webkit-size-adjust:109%;size-adjust:109%;}}{css}text,tspan{{white-space:pre;}}</style>",
        f'<rect width="{width}px" height="{height}px" fill="{t["bg"]}" rx="15"/>',
        f'<text x="{PAD_X}" y="{PAD_Y}">',
    ]
    for i, row in enumerate(art):
        runs, cur, buf = [], None, ""
        for ch, tier in row:
            if tier != cur and buf:
                runs.append((buf, cur))
                buf = ""
            cur = tier
            buf += ch
        runs.append((buf, cur))
        dy = "" if i == 0 else f' dy="{LINE_H}"'
        out.append(f'<tspan x="{PAD_X}"{dy}>' + "".join(
            f'<tspan class="g{tr}">{escape(txt)}</tspan>' for txt, tr in runs
        ) + "</tspan>")
    out.append("</text>")

    out.append(f'<text x="{info_x:.1f}" y="{PAD_Y}">')
    for i, segs in enumerate(info):
        dy = "" if i == 0 else f' dy="{LINE_H}"'
        out.append(f'<tspan x="{info_x:.1f}"{dy}>' + "".join(
            f'<tspan class="{cls}">{escape(txt)}</tspan>' for txt, cls in segs
        ) + "</tspan>")
    out.append("</text></svg>")
    return "\n".join(out)


def main():
    art = galaxy()
    info = info_lines(fetch_stats())
    for theme in THEMES:
        with open(f"{theme}_mode.svg", "w") as f:
            f.write(render(theme, art, info))


if __name__ == "__main__":
    main()
