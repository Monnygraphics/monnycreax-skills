# Pre-Flight Checklist (run before calling any page done)

Merged from taste-skill's pre-flight, Vercel Web Interface Guidelines, design-principles, and MonnyCreaX house rules. Fix every FAIL, then report the table.

## Mechanical greps (run them, don't eyeball)

```bash
# 1. Em / en dashes in anything user-visible (must be 0)
grep -rnE '—|–' src app pages components public *.html 2>/dev/null | grep -vE '\.(lock|map)'
# 2. Eyebrow count: small uppercase tracked labels above headings, must be <= ceil(sections/3)
grep -rnoE 'uppercase[^"]*tracking|tracking[^"]*uppercase|text-transform:\s*uppercase' src app components *.html *.css 2>/dev/null | wc -l
# 3. Banned CSS
grep -rnE 'transition:\s*all|transition-all|outline:\s*none|outline-none|user-scalable=no|maximum-scale=1|#000000|#000;' src app components *.html *.css 2>/dev/null
# 4. Placeholder slop
grep -rniE 'lorem|john doe|jane doe|acme|elevate|seamless|unleash|next-gen|revolutioni[sz]e|99\.99%' src app components *.html 2>/dev/null
# 5. Images without dimensions
grep -rnP '<img(?![^>]*\bwidth=)' src app components *.html 2>/dev/null
```

## Judgement checks

| # | Check | Pass when |
|---|---|---|
| 1 | Design Read stated | One line + dials, before code |
| 2 | Brand authority | Client brand used; MonnyCreaX system only on Monny's own materials |
| 3 | Hero | Fits 1280x720 viewport; ≤ 4 text elements; headline ≤ 2 lines; CTA visible |
| 4 | Nav | One line at 1024px; 64-80px tall |
| 5 | Layout variety | No 3 equal cards; ≤ 2 zigzags in a row; ≥ 4 layout families on an 8-section page |
| 6 | Bento | Cells = content items; 2-3 cells with visual variation |
| 7 | Accent lock | One accent hue everywhere; one neutral temperature |
| 8 | Radius lock | One documented radius scale |
| 9 | CTA intents | One label per intent; no CTA wraps on desktop |
| 10 | Contrast | AA on text, buttons, placeholders, helper/error text, ghost buttons on images |
| 11 | States | hover, focus-visible, active, disabled, loading, empty, error all exist |
| 12 | Forms | Labels above, correct type/autocomplete, inline errors, paste allowed |
| 13 | Semantics | button vs a correct; icon buttons labelled; heading order; skip link |
| 14 | Motion | transform/opacity only; reduced-motion respected; nothing loops > 5s without control |
| 15 | Dark mode | Tokens; tested in both; `color-scheme` + `theme-color` set |
| 16 | Responsive | 375px no horizontal scroll; every multi-column has a declared collapse |
| 17 | Perf | Hero image prioritised, others lazy; fonts preloaded with swap; no CLS from images |
| 18 | Copy | Specific, active voice, no AI filler, no em dashes, realistic names and numbers |
| 19 | Icons / assets | Real icon set; no div-built fake screenshots; no broken image URLs |
| 20 | Browser proof | Screenshots taken at 375 and 1280, light and dark, console clean |
