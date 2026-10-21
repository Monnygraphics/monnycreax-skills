#!/usr/bin/env python3
"""
make_book.py - one command: manuscript in, ONE print-ready PDF out.

    python make_book.py MANUSCRIPT.docx|.pdf|.txt|.md --trim a5 --title "Title" --author "Name" [options]

The user's folder receives only the deliverable: <out>/<Title>.pdf (plus Word / EPUB only when
--extras asks for them). Everything else (the book project, builds, proofs, print check, cover
numbers, order sheet) lives in the hidden work folder, bookcore.work_root(<slug>), and its key
facts are printed here for Claude to relay.

Options
    --trim a5            any trim build_book knows (a5, 6x9, 5.5x8.5, ...)
    --subtitle, --publisher, --year, --isbn, --location, --contact
    --paper 80gsm        print-shop paper for the spine estimate (70gsm 80gsm 90gsm 100gsm)
    --platform printshop printshop | kdp | ingram (spine maths and bleed rules)
    --out DIR            folder that receives the PDF (default: a folder named after the title, next to the manuscript)
    --extras word,epub   also deliver these (default: none)
    --force              rebuild the project from the manuscript, discarding edits made in it

What it does, in order
  1. imports the manuscript into a book project (only once; later runs rebuild from the project,
     so edits made there are kept unless --force)
  2. builds the typeset interior PDF (+ Word + EPUB)
  3. runs the print check and renders proof pages
  4. writes the cover numbers (spine, full wrap) and PRINT-SHOP-ORDER.md for the printer
It formats only. It never rewrites the author's words: editing is Stages 2-4 of the skill.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bookcore as bc  # noqa: E402


def run(args, capture=False):
    sys.stdout.flush()
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=capture, text=True, encoding="utf-8", errors="replace")
    if capture:
        return r.returncode, r.stdout + r.stderr
    if r.returncode not in (0, 1):
        sys.exit(f"step failed: {' '.join(map(str, args))}")
    return r.returncode, ""


def set_meta(book_yml: Path, values: dict, trim: str):
    import yaml
    data = yaml.safe_load(book_yml.read_text(encoding="utf-8")) or {}
    meta = data.setdefault("meta", {})
    for k, v in values.items():
        if v:
            meta[k] = v
    data.setdefault("layout", {})["trim"] = trim
    book_yml.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manuscript")
    ap.add_argument("--trim", default="a5")
    ap.add_argument("--title")
    ap.add_argument("--subtitle")
    ap.add_argument("--author")
    ap.add_argument("--publisher")
    ap.add_argument("--year")
    ap.add_argument("--isbn")
    ap.add_argument("--location")
    ap.add_argument("--contact")
    ap.add_argument("--paper", default="80gsm")
    ap.add_argument("--platform", default="printshop", choices=["printshop", "kdp", "ingram"])
    ap.add_argument("--out")
    ap.add_argument("--extras", default="", help="word,epub: also deliver these next to the PDF")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    src = Path(a.manuscript).resolve()
    if not src.exists():
        sys.exit(f"not found: {src}")
    project = bc.work_root(bc.slugify(a.title or src.stem))
    trim = a.trim.lower().replace(" ", "")
    if src.is_dir() and (src / "book.yml").exists():
        project = src   # an existing project (e.g. built by structure_plan.py): just build it

    if project == src:
        print(f"1/4 import  skipped: building the project {project}")
    elif not (project / "book.yml").exists() or a.force:
        print(f"1/4 import  {src.name} -> {project}", flush=True)
        importer = "import_pdf.py" if src.suffix.lower() == ".pdf" else "import_docx.py"
        run([HERE / importer, src, project, *(["--force"] if project.exists() else []),
             *(["--title", a.title] if a.title else []), *(["--author", a.author] if a.author else [])])
    else:
        print(f"1/4 import  skipped: {project} exists (edits there are kept; --force re-imports)")
    set_meta(project / "book.yml", {"title": a.title, "subtitle": a.subtitle, "author": a.author,
                                    "publisher": a.publisher, "year": a.year, "isbn_print": a.isbn,
                                    "location": a.location, "contact": a.contact}, trim)

    _, _, secs = bc.load_project(project)
    body = [s for s in secs if s.matter == "body"]
    words = sum(bc.word_count(bc.md_plain(s.body_md)) for s in secs)
    if len(body) <= 1 and words > 3000:
        print(f"\n! No chapter structure found ({words:,} words in {len(body)} body section). This looks like a draft or a\n"
              f"  transcript. Plan the structure first:\n"
              f"    python {HERE / 'structure_plan.py'} dump \"{src}\"\n"
              f"  then fill plan.json, run 'structure_plan.py build', and run this script on the project folder.\n"
              f"  Building anyway so you can see it, but it is not ready for print.\n")
    extras = {e.strip().lower() for e in a.extras.split(",") if e.strip()}
    formats = ["pdf"] + (["docx"] if extras & {"word", "docx"} else []) + (["epub"] if "epub" in extras else [])
    print(f"2/4 build   {','.join(formats)} at {trim}")
    run([HERE / "build_book.py", project, "--formats", ",".join(formats)])
    build = project / "build"
    meta, layout, sections = bc.load_project(project)
    pdf = build / f"{bc.slugify(meta['title'])}-interior-{trim}.pdf"

    pack = build / "print-shop"
    pack.mkdir(exist_ok=True)
    check = ""
    if pdf.exists():
        print("3/4 check   print rules + proof pages")
        code, check = run([HERE / "check_print.py", pdf, "--trim", trim, "--png-dir", pack / "proofs",
                           "--platform", a.platform], capture=True)
        (pack / "print-check.md").write_text(check, encoding="utf-8")
        print("4/4 cover   spine and wrap size")
        _, cover = run([HERE / "cover_calc.py", "--pdf", pdf, "--trim", trim, "--paper", a.paper,
                        "--platform", a.platform], capture=True)
        (pack / "cover-spec.md").write_text(cover, encoding="utf-8")
        import fitz
        pages = len(fitz.open(str(pdf)))
        w_mm, h_mm = (round(x * 25.4) for x in __import__("build_book").TRIMS[trim])
        spine = next((l for l in cover.splitlines() if l.startswith("- Spine width")), "")
        order = f"""# Print order: {meta['title']}

Hand this sheet and the interior PDF to the print shop.

| Item | Spec |
|---|---|
| Interior file | `{pdf.name}` |
| Finished size | {trim.upper()} ({w_mm} x {h_mm} mm), portrait |
| Pages | {pages} (single pages in reading order, page 1 is a right-hand page) |
| Interior | black and white, {a.paper} paper (cream book wove if they have it) |
| Binding | perfect bound (glued spine){" - or saddle stitch if under ~48 pages and divisible by 4" if pages <= 64 else ""} |
| Cover | full colour, 250-300gsm art card, matte lamination, 3 mm bleed |
| {spine.replace("- ", "").split(":")[0] if spine else "Spine"} | {spine.split(":", 1)[1].strip() if spine else "ask the shop"} (estimate: ask them to confirm for their paper) |
| Bleed (interior) | none (text only) |
| Fonts | embedded in the PDF |
| Quantity | ___ copies (ask for one proof copy first) |

Ask the shop: their exact spine width, whether they want the cover as one flat PDF (back + spine + front), and a printed proof before the full run.
"""
        (pack / "PRINT-SHOP-ORDER.md").write_text(order, encoding="utf-8")
        import shutil
        shutil.copy2(pdf, pack / pdf.name)

    must = [l for l in check.split("## Must fix", 1)[-1].split("## Should fix")[0].splitlines() if l.startswith("- ")] if check else []
    try:
        rep = __import__("json").loads((build / "build-report.json").read_text(encoding="utf-8"))
        if rep.get("drafted_unapproved"):
            must.append("- drafted text not yet approved by the author: " + ", ".join(rep["drafted_unapproved"])
                        + " (see changes.md; set approved: true in each file)")
        if len(body) <= 1 and words > 3000:
            must.append("- no chapter structure: run structure_plan.py (see above)")
        d = rep.get("design", {})
        print(f"\nDesign: {d.get('preset')} preset, {d.get('body_font')} {d.get('body_size')}pt body, "
              f"{d.get('heading_font')} headings. Why: {d.get('preset_why')}. Override with layout.preset in book.yml.")
    except Exception:
        pass
    # deliver: only the files the user will use
    import shutil
    out_dir = Path(a.out).resolve() if a.out else (src.parent if src.is_file() else Path.home() / "Downloads") / \
        re.sub(r'[<>:"/\|?*]', "", meta["title"]).strip()
    out_dir.mkdir(parents=True, exist_ok=True)
    delivered = []
    if pdf.exists():
        target = out_dir / f"{re.sub(r'[<>:\"/\|?*]', '', meta['title']).strip()}.pdf"
        shutil.copy2(pdf, target)
        delivered.append(target)
    for f in build.glob("*.docx"):
        if extras & {"word", "docx"}:
            delivered.append(Path(shutil.copy2(f, out_dir / f"{target.stem}.docx")))
    for f in build.glob("*.epub"):
        if "epub" in extras:
            delivered.append(Path(shutil.copy2(f, out_dir / f"{target.stem}.epub")))
    print("\n=== Delivered (the only files in the output folder):")
    for f in delivered:
        print("   ", f)
    if pdf.exists():
        print(f"\nPrinter details: {pages} pages, {trim.upper()} ({w_mm} x {h_mm} mm), {spine.replace('- ', '').strip()}")
    print(f"Working files (hidden): {project}")
    if must:
        print("\nMUST FIX before printing:")
        for m in must:
            print("  ", m)
    else:
        print("\nPrint check passed. Look at the proof pages, then order ONE proof copy before the full run.")
    print(f"To change anything: edit {project / 'book.yml'} or the Markdown in {project / 'manuscript'}, then run this again.")


if __name__ == "__main__":
    main()
