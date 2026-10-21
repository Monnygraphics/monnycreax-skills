# Intake: the questions Claude asks MONNY

Different from `questionnaire-bank.md` (that is the client-facing discovery
form). This is the fast conversation where Monny says "I have a new client,
Mr. Peter" and Claude prompts him for what it needs.

## Rules

- **Ask in rounds, max 5 questions per round.** Use AskUserQuestion where the
  options are predictable; plain questions where they are open.
- **Never ask what you can infer** from what Monny already said, from memory, or
  from the client's public footprint.
- **Accept "I don't know."** Mark it as a gap, make a reasoned assumption, label it
  `ASSUMPTION`, and move on. Gaps feed the client questionnaire.
- **Stop asking when the brand type and stage are clear.** Then produce output.

## Round 1: always (frame)

1. Name and one line on who they are.
2. **Brand type:** personal brand / business brand / both (person + business).
3. **The outcome** they want in 12-36 months (Brand Journey Q1).
4. What exists today: platforms, rough following, website, offers, revenue
   (ballpark), team.
5. What did they ask Monny for, and what does Monny think they actually need?

From Round 1, place them on the stage ladder (`sequencing.md`) and choose which
Round 2 set to use.

## Round 2A: personal brand

1. Their story in 3 beats: origin, turning point, now. Anything private?
2. Who is the one person they serve, and what does that person want badly?
3. What do they believe that their peers don't? What do they stand against?
4. How do they naturally communicate: teacher, pastor, storyteller, operator?
5. What have they already posted that worked, and what felt fake?

## Round 2B: business brand

1. What does the business sell, to whom, at what price points?
2. Why do customers choose them over the obvious alternative? (in customer words)
3. Who is the founder, and will the founder be a face of the brand?
4. Back end: delivery capacity, team, systems, sales process, what breaks first
   if demand doubles.
5. Front end: current name, visuals, website, reviews, proof assets.

## Round 2C: both

Run 2A for the person, then only questions 1, 4 and 5 from 2B. Decide the
architecture: which door leads (default: the person) and how they link
(collab posts, "founder of" lines, shared proof).

## Round 3: only if needed for the requested output

- Content: shoot capacity, preferred formats, platforms, audience timezone.
- Monetization: current offers and prices, close rate, what clients say after.
- Visual: existing assets, colours or styles they love or hate.

## Then produce

The default first output after intake is a **Brand Snapshot** (one screen):

```
CLIENT / TYPE / STAGE
OUTCOME (long-term)
POSITION (draft claim + one word)
PERSONALITY (known FOR x2, AGAINST x2, belief, delivery)
FRONT END (identity, content, platforms, website status)
BACK END (offers, pricing, delivery, systems, team)
MARKETING (primary channel, mix, lead path)
30 DAYS / 90 DAYS / NOT YET
GAPS + ASSUMPTIONS (feed the client questionnaire)
```

Then offer the next step: client questionnaire (Phase 2), full strategy
(Phase 3), or content plan (`content-engine.md`).
