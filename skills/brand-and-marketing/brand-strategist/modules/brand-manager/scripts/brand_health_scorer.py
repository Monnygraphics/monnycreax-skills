#!/usr/bin/env python3
"""
brand_health_scorer.py — Brand Manager brand-health diagnostic.

Scores a brand 0-100 across 6 weighted dimensions, returns a verdict, and surfaces
the 3 weakest dimensions as prioritized actions. Inputs are 0-10 self-ratings the
manager assigns from the brand brief + analytics; deterministic, no LLM.

Dimensions (weight):
  clarity        0.20  — is the positioning/offer instantly clear?
  consistency    0.18  — voice, visuals, cadence consistent across platforms?
  audience_fit   0.20  — content matches who you're trying to reach?
  engagement     0.17  — audience interacts (vs. just impressions)?
  differentiation 0.15 — distinct from competitors?
  conversion     0.10  — audience takes the next action (lead/sale)?

Usage:
  python brand_health_scorer.py --clarity 7 --consistency 5 --audience-fit 8 \
      --engagement 6 --differentiation 4 --conversion 5
  python brand_health_scorer.py --sample
  python brand_health_scorer.py --sample --json
"""
import argparse
import json
import sys

WEIGHTS = {
    "clarity": 0.20,
    "consistency": 0.18,
    "audience_fit": 0.20,
    "engagement": 0.17,
    "differentiation": 0.15,
    "conversion": 0.10,
}

ACTIONS = {
    "clarity": "Rewrite your bio/positioning so a stranger understands the offer in 5 seconds.",
    "consistency": "Lock a voice spec + visual template and apply it to every post for 30 days.",
    "audience_fit": "Re-check your top 3 posts against your persona — make more of what fits.",
    "engagement": "Shift to formats that invite replies (questions, hot takes, polls); reply fast.",
    "differentiation": "Name the one thing you do that competitors don't, and lead with it.",
    "conversion": "Add a single clear CTA + a frictionless next step (link, DM word, offer).",
}


def score(ratings):
    breakdown = {}
    total = 0.0
    for dim, weight in WEIGHTS.items():
        r = max(0.0, min(10.0, float(ratings.get(dim, 0))))
        contribution = r * weight * 10  # 0-10 rating -> 0-100 scaled
        breakdown[dim] = {"rating": r, "weight": weight,
                          "points": round(contribution, 1)}
        total += contribution
    total = round(total, 1)
    if total >= 80:
        verdict = "STRONG — brand is healthy; optimize at the margins."
    elif total >= 65:
        verdict = "HEALTHY — solid base with clear fixable gaps."
    elif total >= 50:
        verdict = "SOFT — real weaknesses dragging results; prioritize the bottom 3."
    else:
        verdict = "WEAK — foundational work needed before scaling spend."
    weakest = sorted(breakdown.items(), key=lambda kv: kv[1]["rating"])[:3]
    return {
        "total": total,
        "verdict": verdict,
        "breakdown": breakdown,
        "priority_actions": [
            {"dimension": d, "rating": v["rating"], "action": ACTIONS[d]}
            for d, v in weakest
        ],
    }


def render(result):
    out = []
    out.append("=" * 62)
    out.append("BRAND MANAGER — BRAND HEALTH SCORE")
    out.append("=" * 62)
    out.append(f"  SCORE: {result['total']} / 100")
    out.append(f"  {result['verdict']}\n")
    out.append("DIMENSIONS")
    out.append("-" * 62)
    for dim, v in result["breakdown"].items():
        bar = "#" * int(v["rating"]) + "-" * (10 - int(v["rating"]))
        out.append(f"  {dim:<16} {bar} {v['rating']:>4}/10  "
                   f"({v['points']} pts)")
    out.append("\nTOP 3 PRIORITY ACTIONS (weakest first)")
    out.append("-" * 62)
    for i, a in enumerate(result["priority_actions"], 1):
        out.append(f"  {i}. [{a['dimension']} @ {a['rating']}/10]")
        out.append(f"     {a['action']}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Score brand health 0-100.")
    for dim in WEIGHTS:
        ap.add_argument(f"--{dim.replace('_', '-')}", type=float, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sample", action="store_true")
    args = ap.parse_args()

    if args.sample:
        ratings = {"clarity": 7, "consistency": 5, "audience_fit": 8,
                   "engagement": 6, "differentiation": 4, "conversion": 5}
    else:
        ratings = {dim: getattr(args, dim) for dim in WEIGHTS}
        if all(v is None for v in ratings.values()):
            print("No ratings provided; running --sample. Use --help for usage.\n",
                  file=sys.stderr)
            ratings = {"clarity": 7, "consistency": 5, "audience_fit": 8,
                       "engagement": 6, "differentiation": 4, "conversion": 5}
        else:
            ratings = {k: (v if v is not None else 5) for k, v in ratings.items()}

    result = score(ratings)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render(result))


if __name__ == "__main__":
    main()
