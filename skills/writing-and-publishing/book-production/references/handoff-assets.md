# Handoff Assets (Stage 8)

Templates for what leaves the building with the book. All new text follows the voice standard: no em dashes, run `humanizer` before showing.

## Back cover copy (200 to 250 words, its own .docx)

Built from the book's own language. Structure:

1. **Hook (1-2 sentences):** the tension the reader lives with, in the book's words.
2. **Promise (2-3 sentences):** what changes for the reader. Concrete, not abstract.
3. **What's inside (3-5 short lines or one paragraph):** the book's real moves (chapter ideas), not a list of chapter titles.
4. **Who it's for (1 sentence).**
5. **Author line (1-2 sentences):** credibility tied to the book's subject.
6. Optional: one verified endorsement, with permission.

Check: every claim is in the book; no quote appears that is not verified; it fits the cover template's text area at a readable size (about 10-11pt).

## Cover designer brief

```
COVER BRIEF: <Title>
Title treatment: <exact title, capitalisation>
Subtitle: <exact>            Tagline (optional): <exact>
Author name as printed: <exact>
Mood: <3 words>              References: <links / covers they like>
Palette: <brand colours or direction>   Fonts: <brand fonts if any>
Trim: <a5 / 6x9 ...>         Pages: <n>   Paper: <cream 80gsm / KDP cream ...>
Spine width: <from cover_calc.py> (print shop: confirm with them)
Full wrap with bleed: <W x H mm / in>   Resolution: 300 ppi, CMYK for print shops
Spine text: <title | author | logo>, allowed: <yes/no from cover_calc>
Back cover: copy (attached), barcode area <size, position>, publisher logo, price (optional)
Ebook cover: 1600 x 2560 px RGB JPG, same front design, title legible at thumbnail size
Deliver: print PDF (flat, back + spine + front), ebook JPG, source file
```

## Publisher concept note (only when pitching a publisher)

Sections: book snapshot (title, subtitle, word count, status), one-paragraph summary, target market and comparable titles, cultural context (why this book, why now, why this author in this market), chapter structure with one line per chapter, author bio with platform numbers (followers, list size, speaking), publishing rationale (what the author brings: pre-orders, events, bulk buyers). Keep to two pages.

## Upload and print checklists

**Print shop (local, A5 typical)**
- [ ] Interior PDF passes `check_print.py`, proofs looked at
- [ ] `PRINT-SHOP-ORDER.md` printed or sent with the file
- [ ] Spine width confirmed by the shop for their paper before the cover is final
- [ ] Cover as one flat PDF with 3 mm bleed, CMYK, 300 ppi
- [ ] One proof copy ordered and read before the full run (check margins in the gutter, page order, cover alignment)

**Amazon KDP paperback**
- [ ] Trim and paper selected match the PDF (cream or white) and `cover_calc.py --platform kdp`
- [ ] Interior PDF uploaded; Previewer shows no margin warnings
- [ ] Cover PDF at the exact full-wrap size (or KDP Cover Creator)
- [ ] ISBN: KDP free ISBN (Amazon only) or your own
- [ ] Order a proof copy

**IngramSpark**
- [ ] Own ISBN (KNLS in Kenya)
- [ ] Even page count; cover from Ingram's template generator with their barcode
- [ ] PDF/X if their check complains (Acrobat Preflight)

**Ebook (KDP / others)**
- [ ] EPUB from the build, checked in Kindle Previewer
- [ ] Cover 1600 x 2560 px
- [ ] Separate ebook ISBN if distributing beyond Amazon

## Session status report (end every session with this)

```
DONE THIS SESSION
- ...
REMAINING
Must fix: ...
Should fix: ...
Author's call: ...
NEXT ACTION: <one thing>
```
