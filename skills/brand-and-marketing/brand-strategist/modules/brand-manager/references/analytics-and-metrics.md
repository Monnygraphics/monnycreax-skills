# Analytics & Metrics Reference

Read this for Mode 4 (Performance Analyst) and the metrics side of Mode 2.

## Getting the data (manual export — no scraping)

Ask the user to export post-level analytics. Every platform supports this:
- **Instagram/Facebook:** Meta Business Suite → Insights → Export.
- **TikTok:** Creator tools → Analytics → Download data.
- **X:** Analytics → export, or Premium analytics.
- **LinkedIn:** Page analytics → Export, or per-post analytics.

Map their export into `assets/posts-export-template.csv`, or just paste a table and
read it into the same columns. Then run `engagement_analyzer.py --csv posts.csv`.

If there's no export, **say you can't analyze yet** and ask for one. Never invent
numbers.

## Core formulas

- **Engagement rate (by reach):**
  `(likes + comments + shares + saves + clicks) / reach × 100`
  This is the default — it normalizes for how many people actually saw the post.
- **Engagement rate (by followers):** same numerator ÷ follower count. Use only
  when reach isn't in the export.
- **ROI:** `(revenue − spend) / spend × 100`. Needs both `spend` and `revenue`
  columns. Report in the brand's currency (default KES).
- **CPM / cost per result:** spend ÷ (impressions/1000), spend ÷ conversions.

## What each metric actually tells you

| Metric | Reads as | Watch out for |
|--------|----------|---------------|
| Impressions/Reach | How many saw it | Vanity if engagement is flat |
| Likes | Low-effort approval | Weakest signal; don't optimize for it |
| Comments | Genuine interest / conversation | Even negative ones boost reach |
| Shares | "I'd send this to someone" | Strongest reach driver |
| Saves | "I'll come back to this" | Best signal of real value (esp. IG) |
| Clicks | Intent toward the offer | The bridge from social to revenue |
| Follower growth | Compounding audience | Slow; lags good content by weeks |

## Reading a report (what the analyzer gives you)

1. **Per-platform verdict vs benchmark** — STRONG / HEALTHY / SOFT / WEAK.
2. **Top posts** — reverse-engineer *why* (format, hook, pillar, time) and make more.
3. **Bottom posts** — find the shared pattern and stop doing it.
4. **ROI** — only when spend+revenue present; otherwise report engagement only.

## Turning analysis into action

Every analysis ends with **3 concrete changes**, each tied to a metric and a
target, e.g.:
- "More carousels (top 2 posts were carousels) — target +0.5pp IG engagement."
- "Cut single-image promos (bottom 3) — replace with proof-led Reels."
- "Add a CTA to every offer post — target click-through > 1%."

Then re-export in ~2 weeks and re-run to confirm the trend moved.
