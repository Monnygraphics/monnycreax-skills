# DOCX Surgery (Stage 7, route A)

Editing the author's own .docx in place, when the Word file is the deliverable and its styling must survive. Read the `anthropic-skills:docx` skill once per session before the first edit.

## Unpack, edit, validate, pack

```python
import zipfile, shutil, lxml.etree as ET
src, out = "Manuscript.docx", "Manuscript (Clean).docx"
z = zipfile.ZipFile(src)
xml = z.read("word/document.xml").decode("utf-8")
# ... edits on `xml` ...
ET.fromstring(xml.encode("utf-8"))            # validate after every batch: raises on broken XML
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as o:
    for item in z.infolist():
        data = xml.encode("utf-8") if item.filename == "word/document.xml" else z.read(item.filename)
        o.writestr(item, data)                 # every other part copied byte for byte: styles, rels, numbering
```

On claude.ai the same flow exists as `/mnt/skills/public/docx/scripts/office/unpack.py` and `pack.py ... --original manuscript.docx`.

## Rules that prevent broken files

- **Python string replacement, first match only:** `xml.replace(old, new, 1)`. No line-indexed edits; large text blocks often live in one `<w:t>`.
- **Match the raw XML encoding in anchors.** Read text with `re.findall(r'<w:t[^>]*>([^<]+)</w:t>', xml)`, but replacements must use what is in the file: `&#x201C;` / `&#x201D;` curly double quotes, `&#x2019;` apostrophe, `&#x2014;` em dash, `&amp;`. Word may also store them as literal characters. Search both ways before concluding text is missing.
- **Text split across runs.** A sentence can be cut into several `<w:r>` by spellcheck or formatting marks. If the anchor is not found, locate the paragraph and rebuild its runs.
- **Paragraph boundaries:** `xml.rfind('<w:p ', 0, idx)` / `xml.rfind('<w:p>', 0, idx)` and `xml.find('</w:p>', idx)`. After replacing content inside multi-run paragraphs, check for orphaned `<w:p ...>` openers.
- **Self-closing empty paragraphs** (`<w:p .../>`) are valid. Do not flag them.
- **TOC entries versus real headings.** "Chapter One" appears in the TOC first; the real heading comes later. Anchor on the second occurrence or on the heading style.
- **Never cache paragraph indices across edits** that insert or delete paragraphs (Scribe bug #4). Re-find the anchor every time.
- **Reading text: never `''.join(run.text)`.** It drops `<w:br/>` and fuses words. Use `bookcore.read_docx()` or walk runs inserting `\n` at each `<w:br/>`.

## Page numbers

Footer page numbers use `<w:fldSimple w:instr=" PAGE \* MERGEFORMAT "><w:r><w:t>1</w:t></w:r></w:fldSimple>`. Write them to every footer part the document uses (often `footer1.xml`, `footer2.xml`, `footer3.xml` for first, odd and even pages). Ask first: some authors add page numbers themselves after the final read.

## Comments and tracked changes

- Comments: `word/comments.xml` (full text); markers in document.xml are `<w:commentRangeStart>`, `<w:commentRangeEnd>`, `<w:commentReference>`. To remove a comment, delete all three markers and the `<w:comment>` entry.
- Tracked changes: `<w:ins>` (keep the runs inside to accept), `<w:del>` with `<w:delText>` (remove to accept). Never silently accept or reject: ask the author first.

## Render and look

LibreOffice is not installed on Monny's machine. To see pages: open in Word and export PDF, or rebuild through the pipeline (`import_docx.py` + `build_book.py`) for a typeset proof. On claude.ai: `python /mnt/skills/public/docx/scripts/office/soffice.py --headless --convert-to pdf output.docx`, then `pdftoppm -jpeg -r 110 -f 5 -l 5 output.pdf check`.

## Known bugs catalog (from the Scribe skill, 10 books)

| # | Symptom | Fix |
|---|---|---|
| 1 | duplicate section number with a matching gap (two "Law 69", no 68) | renumber the first duplicate into the gap; anything more complex goes to the author |
| 2 | number heading missing, content present | insert the heading after confirming with the author |
| 3 | two labelled sections fused into one paragraph | split on the line breaks inside the paragraph, rebuild runs |
| 4 | fixes stop working halfway through the book | stale cached paragraph indices; re-scan the live document every lookup |
| 5 | fused words `GodIsTalking` | lost `<w:br/>`; line-break-aware reading plus a guarded split |
| 6 | emoji in section labels | strip (no glyphs in print fonts) |
| 7 | inconsistent label casing | normalise to the book's dominant convention |
| 8 | source TOC differs from body titles | always rebuild the TOC from body titles |
| 9 | parts listed in TOC, absent from body | insert divider pages after confirming names |
| 10 | two naming schemes for the same parts | the author picks one |
| 11 | sourced scripture text | verify reference-to-verse mapping; flag if unsure |
| 12 | many images | no placeholders; the author places images |
| 14 | a fix function corrupted correct text | test every fix on clean text too; log every change |
