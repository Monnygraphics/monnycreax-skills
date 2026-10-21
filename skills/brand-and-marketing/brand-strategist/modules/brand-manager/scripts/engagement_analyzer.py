#!/usr/bin/env python3
"""
engagement_analyzer.py — Brand Manager performance analyst.

Reads a MANUAL EXPORT of post-level social analytics (CSV) and reports:
  - engagement rate per platform vs. industry benchmark
  - top and bottom posts (and a hint at why)
  - ROI when spend/revenue columns are present (currency-aware)

This tool does NOT scrape. Feed it data the user exported from their native
platform analytics. See assets/posts-export-template.csv for the expected shape.

Expected columns (case-insensitive, extras ignored, missing ones tolerated):
  platform, date, post, followers, impressions|reach, likes, comments, shares,
  saves, clicks, spend, revenue

Usage:
  python engagement_analyzer.py --csv posts.csv
  python engagement_analyzer.py --csv posts.csv --currency KES --json
  python engagement_analyzer.py --sample
"""
import argparse
import csv
import io
import json
import sys

# Median engagement-rate benchmarks (% of reach/impressions) by platform.
# Sourced as rough industry medians; treat as directional, not gospel.
BENCHMARKS = {
    "instagram": 1.2,
    "tiktok": 2.5,
    "x": 0.5,
    "twitter": 0.5,
    "linkedin": 2.0,
    "facebook": 0.6,
    "youtube": 1.5,
    "default": 1.0,
}

SAMPLE_CSV = """platform,date,post,followers,reach,likes,comments,shares,saves,spend,revenue
instagram,2026-06-01,Behind the scenes reel,5400,8200,540,32,18,77,0,0
instagram,2026-06-03,Client work showcase,5420,6100,210,9,4,21,0,0
instagram,2026-06-06,Promo: June offer,5460,9800,610,40,55,130,3000,21000
tiktok,2026-06-02,Quick design tip,3100,15400,1200,85,210,340,0,0
tiktok,2026-06-05,Trend remix,3160,4200,180,6,12,22,0,0
x,2026-06-02,Hot take on branding,2200,9100,140,28,33,0,0,0
x,2026-06-04,Thread: 5 lessons,2230,21000,410,52,180,0,0,0
linkedin,2026-06-03,Case study writeup,1800,4300,96,21,14,0,0,0
"""


def _f(row, *keys):
    """First matching numeric column value, else 0.0."""
    for k in keys:
        if k in row and str(row[k]).strip() not in ("", "-", "n/a", "N/A"):
            try:
                return float(str(row[k]).replace(",", "").replace("%", ""))
            except ValueError:
                continue
    return 0.0


def _s(row, *keys, default=""):
    for k in keys:
        if k in row and str(row[k]).strip():
            return str(row[k]).strip()
    return default


def analyze(rows, currency="KES"):
    platforms = {}
    posts = []
    for raw in rows:
        row = {k.strip().lower(): v for k, v in raw.items() if k}
        platform = _s(row, "platform", default="unknown").lower()
        reach = _f(row, "reach", "impressions")
        likes = _f(row, "likes")
        comments = _f(row, "comments")
        shares = _f(row, "shares")
        saves = _f(row, "saves")
        clicks = _f(row, "clicks")
        spend = _f(row, "spend", "cost")
        revenue = _f(row, "revenue", "sales")
        interactions = likes + comments + shares + saves + clicks
        denom = reach if reach > 0 else _f(row, "followers")
        er = round((interactions / denom) * 100, 2) if denom > 0 else 0.0

        rec = {
            "platform": platform,
            "post": _s(row, "post", "title", "name", default="(untitled)"),
            "date": _s(row, "date"),
            "reach": reach,
            "interactions": interactions,
            "engagement_rate": er,
            "spend": spend,
            "revenue": revenue,
        }
        posts.append(rec)

        p = platforms.setdefault(platform, {
            "posts": 0, "reach": 0.0, "interactions": 0.0,
            "spend": 0.0, "revenue": 0.0,
        })
        p["posts"] += 1
        p["reach"] += reach
        p["interactions"] += interactions
        p["spend"] += spend
        p["revenue"] += revenue

    summary = {}
    for name, p in platforms.items():
        er = round((p["interactions"] / p["reach"]) * 100, 2) if p["reach"] > 0 else 0.0
        bench = BENCHMARKS.get(name, BENCHMARKS["default"])
        if er >= bench * 1.5:
            verdict = "STRONG — well above benchmark"
        elif er >= bench:
            verdict = "HEALTHY — at or above benchmark"
        elif er >= bench * 0.6:
            verdict = "SOFT — below benchmark, fixable"
        else:
            verdict = "WEAK — well below benchmark"
        roi = None
        if p["spend"] > 0:
            roi = round(((p["revenue"] - p["spend"]) / p["spend"]) * 100, 1)
        summary[name] = {
            "posts": p["posts"],
            "avg_engagement_rate": er,
            "benchmark": bench,
            "verdict": verdict,
            "spend": round(p["spend"], 2),
            "revenue": round(p["revenue"], 2),
            "roi_pct": roi,
        }

    ranked = sorted(posts, key=lambda r: r["engagement_rate"], reverse=True)
    return {
        "currency": currency,
        "platforms": summary,
        "top_posts": ranked[:3],
        "bottom_posts": ranked[-3:][::-1] if len(ranked) > 3 else [],
        "total_posts": len(posts),
    }


def render(result):
    cur = result["currency"]
    out = []
    out.append("=" * 62)
    out.append("BRAND MANAGER — SOCIAL PERFORMANCE REPORT")
    out.append("=" * 62)
    out.append(f"Posts analyzed: {result['total_posts']}\n")
    out.append("PER-PLATFORM")
    out.append("-" * 62)
    for name, p in result["platforms"].items():
        out.append(f"  {name.upper()}  ({p['posts']} posts)")
        out.append(f"    Avg engagement: {p['avg_engagement_rate']}%  "
                   f"(benchmark {p['benchmark']}%)")
        out.append(f"    {p['verdict']}")
        if p["roi_pct"] is not None:
            out.append(f"    Spend {cur} {p['spend']:,.0f} -> Revenue "
                       f"{cur} {p['revenue']:,.0f}  |  ROI {p['roi_pct']}%")
        out.append("")
    out.append("TOP POSTS")
    out.append("-" * 62)
    for r in result["top_posts"]:
        out.append(f"  [{r['engagement_rate']}%] {r['platform']} — {r['post']}")
    if result["bottom_posts"]:
        out.append("\nBOTTOM POSTS (study these for what to drop)")
        out.append("-" * 62)
        for r in result["bottom_posts"]:
            out.append(f"  [{r['engagement_rate']}%] {r['platform']} — {r['post']}")
    out.append("\nNEXT 3 ACTIONS")
    out.append("-" * 62)
    out.append("  1. Make more of what's in TOP POSTS (format + hook + pillar).")
    out.append("  2. Cut or rework the BOTTOM POSTS pattern.")
    out.append("  3. Re-export in 2 weeks and re-run to confirm the trend.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Analyze exported social post data.")
    ap.add_argument("--csv", help="Path to CSV export of posts.")
    ap.add_argument("--currency", default="KES", help="Currency label (default KES).")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of report.")
    ap.add_argument("--sample", action="store_true", help="Run on built-in sample data.")
    args = ap.parse_args()

    if args.sample or not args.csv:
        if not args.sample and not args.csv:
            print("No --csv provided; running --sample. Use --help for usage.\n",
                  file=sys.stderr)
        reader = csv.DictReader(io.StringIO(SAMPLE_CSV))
        rows = list(reader)
    else:
        with open(args.csv, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))

    result = analyze(rows, currency=args.currency)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render(result))


if __name__ == "__main__":
    main()
