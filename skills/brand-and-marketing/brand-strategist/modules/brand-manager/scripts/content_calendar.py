#!/usr/bin/env python3
"""
content_calendar.py — Brand Manager social calendar generator.

Builds an N-week, multi-platform content calendar from content pillars and a
posting cadence. Deterministic (no LLM): rotates pillars across slots, assigns a
platform-appropriate post type and a hook template the manager can fill in.

Usage:
  python content_calendar.py --weeks 4 \
      --platforms instagram,tiktok,x,linkedin \
      --pillars "education,behind-the-scenes,social-proof,offers" \
      --per-week 4
  python content_calendar.py --sample
  python content_calendar.py --json --weeks 2 --platforms instagram,tiktok
"""
import argparse
import json
import sys

# Platform-appropriate post formats to rotate through.
POST_TYPES = {
    "instagram": ["Reel", "Carousel", "Single image", "Story series"],
    "tiktok": ["Talking-head", "Tutorial", "Trend remix", "Day-in-the-life"],
    "x": ["Single tweet", "Thread", "Hot take", "Poll"],
    "twitter": ["Single tweet", "Thread", "Hot take", "Poll"],
    "linkedin": ["Text post", "Document carousel", "Case study", "Poll"],
    "facebook": ["Photo post", "Link share", "Video", "Event"],
    "youtube": ["Long-form", "Short", "Tutorial", "Q&A"],
}

# Hook templates by pillar — fill-in-the-blank starters, not finished copy.
HOOKS = {
    "education": "Teach one thing: \"How to ____ in 3 steps\"",
    "behind-the-scenes": "Show the process: \"What making ____ actually looks like\"",
    "social-proof": "Result/testimonial: \"How [client] got ____\"",
    "proof": "Result/testimonial: \"How [client] got ____\"",
    "offers": "Clear CTA: \"____ is open — here's how to grab it\"",
    "story": "Personal hook: \"The day I almost quit ____\"",
    "engagement": "Ask the audience: \"____ or ____? Tell me below\"",
}

DEFAULT_HOOK = "Hook: open with a bold claim or question about ____"
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def build(weeks, platforms, pillars, per_week):
    calendar = []
    slot = 0
    # Spread `per_week` posts across the 7 days, front-loading weekdays.
    day_order = [0, 2, 4, 1, 3, 5, 6]  # Mon, Wed, Fri, Tue, Thu, Sat, Sun
    for w in range(1, weeks + 1):
        for i in range(per_week):
            platform = platforms[slot % len(platforms)]
            pillar = pillars[slot % len(pillars)]
            ptypes = POST_TYPES.get(platform, ["Post"])
            ptype = ptypes[slot % len(ptypes)]
            hook = HOOKS.get(pillar.lower(), DEFAULT_HOOK)
            day = DOW[day_order[i % len(day_order)]]
            calendar.append({
                "week": w,
                "day": day,
                "platform": platform,
                "pillar": pillar,
                "post_type": ptype,
                "hook": hook,
            })
            slot += 1
    return calendar


def render(calendar, weeks):
    out = []
    out.append("=" * 70)
    out.append(f"BRAND MANAGER — {weeks}-WEEK CONTENT CALENDAR")
    out.append("=" * 70)
    for w in range(1, weeks + 1):
        out.append(f"\nWEEK {w}")
        out.append("-" * 70)
        for item in [c for c in calendar if c["week"] == w]:
            out.append(
                f"  {item['day']:>3} | {item['platform']:<10} | "
                f"{item['post_type']:<16} | {item['pillar']}"
            )
            out.append(f"        -> {item['hook']}")
    out.append("\nNEXT 3 ACTIONS")
    out.append("-" * 70)
    out.append("  1. Fill each hook's ____ with a real, specific idea.")
    out.append("  2. Batch-shoot/write a full week in one sitting.")
    out.append("  3. Schedule, then track results to re-run engagement_analyzer.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Generate a content calendar.")
    ap.add_argument("--weeks", type=int, default=4)
    ap.add_argument("--platforms", default="instagram,tiktok,x,linkedin",
                    help="Comma-separated platforms.")
    ap.add_argument("--pillars", default="education,behind-the-scenes,social-proof,offers",
                    help="Comma-separated content pillars.")
    ap.add_argument("--per-week", type=int, default=4, help="Posts per week.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sample", action="store_true")
    args = ap.parse_args()

    if args.sample:
        platforms = ["instagram", "tiktok", "x"]
        pillars = ["education", "behind-the-scenes", "social-proof", "offers"]
        weeks, per_week = 2, 4
    else:
        platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
        pillars = [p.strip() for p in args.pillars.split(",") if p.strip()]
        weeks, per_week = args.weeks, args.per_week

    if not platforms or not pillars:
        print("Need at least one platform and one pillar.", file=sys.stderr)
        sys.exit(2)

    calendar = build(weeks, platforms, pillars, per_week)
    if args.json:
        print(json.dumps(calendar, indent=2))
    else:
        print(render(calendar, weeks))


if __name__ == "__main__":
    main()
