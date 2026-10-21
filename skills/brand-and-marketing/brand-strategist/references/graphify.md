# /graphify — Token-Efficient Analysis Rendering

The principle: **the diagnostic phase should be rendered, not narrated.** Prose
analysis is expensive (many tokens) and slow to read. Compressing findings into
visual structures keeps Phase 1 cheap so the budget is spent on Phase 3 strategy,
where depth actually matters.

When Monny types `/graphify`, or whenever you run Phase 1, switch to this mode.

---

## The rules of graphify mode

1. **No flowing prose.** Observations are one-line bullets, max ~7 words each.
2. **Lead with structure**, not sentences: scorecard, gaps table, charts.
3. **Two charts maximum**: a radar of the scorecard, plus one of {bar, donut}.
4. **Tables over paragraphs** for anything comparative.
5. Reserve all narrative writing for Phase 3 deliverables.

A graphify read should fit on roughly one screen. If it sprawls, compress harder.

---

## Output skeleton (copy this shape)

```
SNAPSHOT
- [observation, <=7 words]
- [observation]
- [observation]
- [observation]

SCORECARD
Strategic Alignment   ██████░░░░  62
Visual Cohesion       ████░░░░░░  41
Market Disruptiveness ███░░░░░░░  35
Messaging Clarity     █████░░░░░  54
Expression Confidence ████░░░░░░  44
-----------------------------------
OVERALL                            47

[radar chart]

HIDDEN ASSET
> [the one underused line/angle, quoted]

GAPS
| Gap        | Evidence            | Fix                    |
|------------|---------------------|------------------------|
| Positioning| ...                 | ...                    |
| Language   | ...                 | ...                    |
| Visibility | ...                 | ...                    |

OPPORTUNITIES
1. ...
2. ...
3. ...

NEXT -> tailored discovery questionnaire (Phase 2)
```

The ASCII bars (`█` filled, `░` empty, 10 segments) give an instant read inline
with zero rendering cost. Use them in chat. Use real charts in the delivered doc.

---

## Inline radar (for the chat / HTML deliverable)

Lightweight inline SVG radar for the 5 scorecard dimensions. Drop into an HTML
deliverable or the visualize widget. Uses the brand palette.

```html
<svg viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg" font-family="Raleway, sans-serif">
  <!-- background rings -->
  <g fill="none" stroke="#2A2A2A" stroke-width="1">
    <circle cx="160" cy="160" r="120"/>
    <circle cx="160" cy="160" r="90"/>
    <circle cx="160" cy="160" r="60"/>
    <circle cx="160" cy="160" r="30"/>
  </g>
  <!-- 5 axes at -90, -18, 54, 126, 198 degrees -->
  <g stroke="#3A3A3A" stroke-width="1">
    <line x1="160" y1="160" x2="160" y2="40"/>
    <line x1="160" y1="160" x2="274" y2="123"/>
    <line x1="160" y1="160" x2="231" y2="257"/>
    <line x1="160" y1="160" x2="89"  y2="257"/>
    <line x1="160" y1="160" x2="46"  y2="123"/>
  </g>
  <!-- DATA polygon: replace each point with 160 + (score/100)*120 along its axis.
       Example scores 62,41,35,54,44 precomputed below. -->
  <polygon points="160,85 209,144 202,217 118,217 113,144"
           fill="#C9A84C" fill-opacity="0.25" stroke="#C9A84C" stroke-width="2"/>
  <!-- labels -->
  <g fill="#F5F5F5" font-size="9" text-anchor="middle">
    <text x="160" y="30">Strategic</text>
    <text x="292" y="123">Visual</text>
    <text x="231" y="275">Disruptive</text>
    <text x="89"  y="275">Messaging</text>
    <text x="28"  y="123">Expression</text>
  </g>
</svg>
```

To compute a data point on an axis: `r = (score/100) * 120`, then place at the
axis angle from center (160,160). Axis angles: top = -90 deg, then +72 deg each,
clockwise. For light-themed (.docx default) versions swap `#0A0A0A`/`#F5F5F5` to
white/charcoal and keep gold as the single accent (~30% theming rule).

---

## Scorecard + bar (ReportLab, for the premium PDF)

When building the full themed PDF deliverable, render the scorecard as horizontal
score bars. Snippet (palette and pattern match Monny's standard docs):

```python
from reportlab.lib import colors
from reportlab.lib.units import mm

GOLD = colors.HexColor("#C9A84C")
DARK = colors.HexColor("#0A0A0A")
DIM  = colors.HexColor("#2A2A2A")

def score_bar(c, x, y, label, score, width=90*mm, h=6*mm):
    c.setFont("Helvetica", 9)          # swap to registered Lufga/Raleway
    c.setFillColor(colors.HexColor("#F5F5F5"))
    c.drawString(x, y + 1.5*mm, label)
    track_x = x + 55*mm
    c.setFillColor(DIM)
    c.roundRect(track_x, y, width, h, 2, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.roundRect(track_x, y, width * (score/100.0), h, 2, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(GOLD)
    c.drawString(track_x + width + 3*mm, y + 1.5*mm, str(score))
```

Register Garamond/Lufga (or Raleway/Montserrat) with `pdfmetrics.registerFont`
before drawing; never ship the generic Helvetica fallback in a final deliverable.

---

## When NOT to graphify

- Phase 3 strategy deliverables (backbone, brand report) — those need full prose.
- Client-facing direction documents written *to* the client — warmth needs words.
- Anything where Monny explicitly asks for the long-form read.

Graphify is a Phase 1 / diagnostic tool. It compresses the read, not the strategy.
