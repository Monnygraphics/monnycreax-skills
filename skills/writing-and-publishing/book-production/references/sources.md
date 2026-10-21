# Sources and Licences

This skill was written for Monny / MonnyCreaX from the UNBRAND-END production process, then extended with ideas studied from four open-source projects on 2026-10-18. No code was copied verbatim; the scripts are new, built on what each project taught.

| Project | Licence | What it contributed |
|---|---|---|
| [AvinashWalton/AuthorPro](https://github.com/AvinashWalton/AuthorPro) | MIT | Full front/back matter catalogue (half title to colophon), copyright-page autofill from book details, trim presets, running heads (title verso, chapter recto), no heads on title/copyright/TOC pages, word count and page-estimate stats |
| [worlduniting/bookpub](https://github.com/worlduniting/bookpub) | MIT | One manuscript source -> many formats; a project folder with a YAML config of meta + layout; frontmatter/bodymatter/backmatter folders; named pages for blank, front matter (roman folios) and chapters; EPUB built and validated as part of the pipeline |
| [dclericc/Scribe](https://github.com/dclericc/Scribe) | MIT | Line-break-aware .docx reading (the root cause of fused words), the guarded fused-word fix, change log with review mode, tracked-changes detection, structure detection (numbered / chapter / section), TOC rebuilt from body titles, blank-paragraph ratio check, the known-bugs catalogue, "test fixes on clean text too" |
| [dclericc/Booksmith](https://github.com/dclericc/Booksmith) | MIT | Designed-interior classification (default prose; pull-quote, callout, table, chart, infographic), density rules, genre font pairings, self-hosted fonts, validate the rendered PDF (headings present, plausible page count, look at every block type), KDP trim and margin tables, non-technical re-export instructions |
| [EB Garamond](https://github.com/google/fonts/tree/main/ofl/ebgaramond) (Georg Duffner, Octavio Pardo) | SIL OFL 1.1 | Bundled body font; static cuts generated from the variable font with fontTools (see `assets/fonts/README.md`) |

Third-party skills were read as reference, not installed. Before installing either Scribe or Booksmith as a skill of its own, run `skill-inspector` on it (CLAUDE.md rule).
