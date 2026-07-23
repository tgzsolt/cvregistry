from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

SRC_DIR = Path(__file__).resolve().parent      # .../cvregistry/src
ROOT = SRC_DIR.parent                           # project root
TEMPLATES_DIR = SRC_DIR / "templates"
CVS_DIR = ROOT / "cvs"
ASSETS_DIR = ROOT / "assets"
BUILD_DIR = ROOT / "build"
CACHE_DIR = BUILD_DIR / "cache"
LOGO_PATH = ASSETS_DIR / "alvicom-logo.png"

DEFAULT_MODEL = os.environ.get("CVREGISTRY_MODEL", "claude-opus-4-8")
PROMPT_VERSION = "1"  # bump to invalidate all cached About texts

# Section headings -> canonical key (English + Hungarian).
SECTION_ALIAS = {
    "rólam": "about", "about": "about",
    "készségek": "skills", "skills": "skills",
    "competence": "competence", "kompetencia": "competence",
    "languages": "languages", "nyelvek": "languages",
    "hobbies": "hobbies", "hobbi": "hobbies",
    "achievements": "achievements", "eredmények": "achievements",
    "professional experience": "experience", "szakmai tapasztalat": "experience",
}

LABELS = {
    "en": {"about": "About Me", "competence": "Competence", "skills": "Skills",
           "languages": "Languages", "hobbies": "Hobbies",
           "achievements": "Achievements", "experience": "Professional Experience"},
    "hu": {"about": "Rólam", "competence": "Kompetencia", "skills": "Készségek",
           "languages": "Nyelv", "hobbies": "Hobbi",
           "achievements": "Eredmények", "experience": "Szakmai tapasztalat"},
}

DASH = "—"  # em dash used to separate a bullet's text from its tech tags
PHOTO_EXTS = (".png", ".jpg", ".jpeg")  # accepted photo extensions


def parse_body(body_lines: list[str]) -> dict:
    name = headline = None
    sections: dict[str, list[str]] = {}
    current_section = None
    seen_h2 = False

    for line in body_lines:
        if line.startswith("# "):
            name = line[2:].strip()
            current_section = None
        elif line.startswith("## "):
            title = line[3:].strip()
            if not seen_h2:
                headline, seen_h2, current_section = title, True, None
            else:
                current_section = SECTION_ALIAS.get(title.lower())
                if current_section:
                    sections[current_section] = []
        elif current_section:
            sections[current_section].append(line)

    return {
        "name": name,
        "headline": headline,
        "competence": parse_competence(sections.get("competence", [])),
        "skills": parse_skills(sections.get("skills", [])),
        "languages": parse_languages(sections.get("languages", [])),
        "hobbies": parse_hobbies(sections.get("hobbies", [])),
        "achievements": parse_achievements(sections.get("achievements", [])),
        "experience": parse_experience(sections.get("experience", [])),
        "about": sections.get("about", []),
    }


def parse_competence(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        m = re.match(r"^- \*\*(.+?):\*\*\s*(.*)$", line)
        if m:
            out.append({"category": m.group(1), "items": m.group(2)})
    return out

def parse_skills(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        m = re.match(rf"^- (.+?) {DASH} (.+)$", line)
        if m:
            out.append({"name": m.group(1).strip(), "level": int(m.group(2).strip())})
    return out


def parse_languages(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        m = re.match(rf"^- (.+?) {DASH} (.+)$", line)
        if m:
            out.append({"name": m.group(1).strip(), "level": m.group(2).strip()})
    return out


def parse_hobbies(lines: list[str]) -> list[str]:
    for line in lines:
        if line.strip():
            return [h.strip() for h in line.split("·") if h.strip()]
    return []


def parse_achievements(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        m = re.match(rf"^- \*\*(.+?)\*\*\s*{DASH}\s*(.*)$", line)
        if m:
            parts = [p.strip() for p in m.group(2).split("·")]
            out.append({"type": m.group(1).strip(), "title": parts[0],
                        "meta": " · ".join(parts[1:])})
    return out


def parse_experience(lines: list[str]) -> list[dict]:
    employers: list[dict] = []
    role = None
    for line in lines:
        if line.startswith("### "):
            employers.append({"employer": line[4:].strip(), "roles": []})
            role = None
        elif line.startswith("#### "):
            title, _, period = line[5:].strip().rpartition(" · ")
            role = {"title": title.strip(), "period": period.strip(),
                    "subtitle": "", "items": []}
            if employers:
                employers[-1]["roles"].append(role)
        elif line.strip().startswith("*") and line.strip().endswith("*") and role:
            role["subtitle"] = line.strip().strip("*").strip()
        elif line.startswith("- ") and role is not None:
            body = line[2:].strip()
            if f" {DASH} " in body:
                text, _, tech = body.partition(f" {DASH} ")
                role["items"].append({"text": text.strip(),
                                      "tech": [t.strip() for t in tech.split("·")]})
            else:
                role["items"].append({"text": body, "tech": []})
    return employers

def year_span(experience: list[dict]) -> int:
    years = []
    for emp in experience:
        for role in emp["roles"]:
            years += [int(y) for y in re.findall(r"\d{4}", role["period"])]
    return (max(years) - min(years)) if years else 0

# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def circular_photo(path: Path, size: int = 600) -> str:
    """Crop the largest centred square from an image, mask it to a circle,
    and return a PNG data URI (transparent outside the circle)."""
    import base64
    import io
    from PIL import Image, ImageDraw

    img = Image.open(path).convert("RGBA")
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize(
        (size, size))

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)

    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def file_data_uri(path: Path, mime: str = "image/png") -> str:
    """Embed a file verbatim as a data URI (keeps the PDF self-contained)."""
    import base64
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def find_photo(md_dir: Path) -> Path | None:
    """Locate the photo next to the CV. `spec` may include an extension or not;
    either way we accept selfie.png / selfie.jpg / selfie.jpeg (any case)."""
    p = Path("selfie")
    search_dir = (md_dir / p.parent).resolve()
    # An explicit, existing path wins.
    exact = (md_dir / "selfie").resolve()
    if p.suffix and exact.exists():
        return exact
    # Otherwise try the stem with each accepted extension.
    for ext in PHOTO_EXTS:
        cand = search_dir / f"{p.stem}{ext}"
        if cand.exists():
            return cand
    return None


def render_pdf(md_path: Path) -> Path:
    text = md_path.read_text(encoding="utf-8")
    body_lines = text.splitlines()
    cv = parse_body(body_lines)

    skills = cv["skills"]
    about = cv["about"]
    language = md_path.stem

    photo = None
    photo_path = find_photo(md_path.parent)
    if photo_path:
        try:
            photo = circular_photo(photo_path)
        except Exception as exc:  # noqa: BLE001
            print(f"  Photo processing failed ({exc!s}) — skipping")
    else:
        print("  Photo not found: selfie.{png,jpg,jpeg} (skipping)")

    context = {
        "language": language,
        "name": cv["name"],
        "monogram": "".join(w[0] for w in (cv["name"] or "").split()).upper(),
        "headline": cv["headline"],
        "photo": photo,
        "brand_logo": file_data_uri(LOGO_PATH) if LOGO_PATH.exists() else None,
        "about": about,
        "competence": cv["competence"],
        "skills": skills,
        "languages": cv["languages"],
        "hobbies": cv["hobbies"],
        "achievements": cv["achievements"],
        "experience": cv["experience"],
        "labels": LABELS.get(language),
    }

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)),
                      autoescape=select_autoescape(["html"]))
    template = env.get_template("modern-sidebar.html")
    html = template.render(**context)
    OUT_DIR = BUILD_DIR / f"{md_path.parent.stem}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = OUT_DIR / f"{md_path.stem}.pdf"
    HTML(string=html, base_url=str(ROOT)).write_pdf(str(out_path))
    skill_str = ", ".join(f"{s['name']}({s['level']})" for s in skills)
    print(f"  Skills: {skill_str}")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate CV PDFs from markdown.")
    ap.add_argument("paths", nargs="*", help="CV markdown files (default: cvs/*.md)")
    args = ap.parse_args()

    paths = [Path(p) for p in args.paths] or sorted(CVS_DIR.rglob("*.md"))
    if not paths:
        print("No CV markdown files found.", file=sys.stderr)
        return 1

    for md_path in paths:
        print(f"{md_path}")
        out = render_pdf(md_path)
        print(f"  -> {out.relative_to(ROOT)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
