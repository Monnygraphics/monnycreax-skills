# Book Anatomy (Stage 5)

The parts of a printed book, their order, which side of the spread they sit on, and what goes in them. Section names match the `type:` values the build pipeline understands.

Recto = right-hand page, odd number. Verso = left-hand page, even number. Page 1 of the file is always a recto.

## Front matter (roman folios, many show none)

| # | type | Page side | Folio shown | Notes |
|---|---|---|---|---|
| 1 | `halftitle` | recto | no | Title only. Optional; common in trade books, skip in short books. |
| 2 | `also-by` | verso of half title | no | "Also by". Optional. |
| 3 | `title` | recto | no | Title, subtitle, author, publisher. `auto:title` builds it from book.yml. |
| 4 | `copyright` | verso of title | no | See template below. `auto:copyright`. |
| 5 | `dedication` | recto | no | Author's own words, brief. |
| 6 | `epigraph` | recto | no | One quote the author chooses deliberately. Verify it (Stage 4). |
| 7 | `toc` | recto | yes (roman) | `auto:toc`. Built from body titles. |
| 8 | `foreword` | recto | yes | Written by someone else; their name under the title. |
| 9 | `preface` | recto | yes | The author: why and how the book came to be. |
| 10 | `introduction` | recto | yes (arabic starts here if present) | Part of the argument. Often the first thing to cut if Chapter One opens stronger. |
| 11 | `prologue` | recto | yes | Narrative nonfiction only. |

## Body (arabic folios, page 1 = first page of Introduction or Chapter One)

| type | Page side | Notes |
|---|---|---|
| `part` | recto, verso left blank | "Part One" + title, optional one-line description. No heads, no folio. |
| `chapter` | recto (chapter_start: right) or next page (any) | Label ("Chapter One") + title + optional subtitle. No running head on the opener. |

## Back matter (arabic folios continue)

| type | Notes |
|---|---|
| `epilogue` / `afterword` / `conclusion` | The closing section or crescendo. |
| `appendix` | Practices, calls to action, resources. |
| `acknowledgements` | A deliberate choice either way. Some authors place it in the front. |
| `glossary`, `notes`, `bibliography`, `resources` | Notes per chapter, in order. |
| `index` | Rare for short nonfiction; needs final pagination. |
| `about-author` | Review after all edits; match the book's scope. Photo optional. |
| `also-by-back` | Other books, series list (current book bold). |
| `colophon` | How the book was made (fonts, printer). Optional. |

## Copyright page template

Keep it on the verso of the title page, set small, bottom-aligned (the build does this).

```
Copyright © <year> <Author Name>
All rights reserved.
No part of this book may be reproduced, stored in a retrieval system, or transmitted in any form or by any means without the prior written permission of the publisher, except for brief quotations in reviews and articles.
[Disclaimer if needed: medical, financial, legal, or "names and details have been changed".]
[Scripture quotations are taken from the <translation>, copyright © <holder>. Used by permission.]
Published by <Publisher>, <City>, <Country>
First edition <year>
ISBN <13-digit> (paperback)
ISBN <13-digit> (ebook)
[Cover design by <name>. Photography by <name>.]
<contact: domain email or website>
[Printed in <country>]
```

Notes:
- **ISBN.** Each format needs its own ISBN (paperback, hardcover, ebook). In Kenya, ISBNs are issued by KNLS (Kenya National Library Service). KDP's free ISBN lists Amazon as publisher and only works on Amazon; IngramSpark needs your own ISBN to distribute widely.
- **Scripture permissions.** Most translations allow a set number of verses without written permission if the copyright notice is printed. Check the translation's own notice.
- **Contact.** Recommend a domain email for senior positioning; the author decides.

## Contents page rules

- Built from the body titles, never the source's own contents list (it drifts; Scribe found it differed in every book).
- Entries: front matter after the contents (preface, introduction), every part and chapter, back matter. Not the title, copyright or dedication.
- Label + title per chapter, optional quiet one-line description. No divider paragraphs.
- Page numbers only from final pagination. The build fills them in automatically; in Word, update the TOC field after the last edit, or leave numbers off (`toc_page_numbers: false`).

## Running heads and folios (what the build does)

- Verso head: author name (`verso_head: author`) or book title. Recto head: the section title.
- No heads on: title, copyright, dedication, epigraph, part pages, chapter openers, blank pages, the contents page.
- Folios bottom centre. None on title, copyright, dedication, epigraph, part pages and blanks. Openers keep their folio unless `drop_folio_on_openers: true`.
- Roman folios count from the first page of the file; arabic 1 is the first page of the Introduction, Prologue, Part One or Chapter One, whichever comes first.

## Section order checks

- A foreword precedes a preface. An introduction comes last in the front matter.
- Acknowledgements: back (common in trade nonfiction) or front, before the introduction.
- Every recto-start section that lands on an even page gets a blank verso before it. Count the blanks: too many in front matter can mean a section should be cut or combined.
