# Puzzle / Brain‑Teaser Game Research & Build Plan

**Goal:** Ship a polished puzzle / brain‑teaser game on Google Play, built on
**Flutter + Dart** (client) and **Go + Docker** (backend), able to support a
large concurrent audience. UI quality is treated as a first‑class feature.

**Date:** 2026‑05‑09
**Branch:** `claude/gaming-app-research-cieVm`

---

## 1. Reference Games on Play Store

The list below was filtered for: high install base, strong retention, clean /
minimalist UI, and a difficulty curve that works for both casual beginners and
"thinkers" who want depth. The user already named *Arrow Puzzle* — that whole
sub‑genre is included.

| # | Game | Studio | Core mechanic | Why it matters |
|---|------|--------|---------------|----------------|
| 1 | **Block Blast!** | Hungry Studio | Drag‑match‑disappear: place tetromino‑style blocks on an 8×8 grid, clear lines/columns | ~70 M DAU, ~$1 M/day revenue, #1 puzzle by downloads in 2025. Adaptive difficulty + "God Mode" piece drops keep retention high. |
| 2 | **Arrow Puzzle / Arrow Out / Arrows – Puzzle Escape** | Easybrain et al. | Tap arrows in an order that lets each one exit without colliding | The genre the user referenced. Tiny ruleset, infinite handcrafted levels, strong "one more level" pull. |
| 3 | **Brain Test: Tricky Puzzles** | Unico Studio | Lateral‑thinking riddles; solutions often require shaking, tilting, dragging items off‑screen | Best‑in‑class viral hook. Each puzzle is its own micro‑game; humour drives sharing. |
| 4 | **Sudoku.com** | Easybrain | Classic 9×9 sudoku with hint system + daily challenges | Gold standard for difficulty tiers (Easy → Expert) and daily‑habit retention. |
| 5 | **Two Dots** | Playdots | Connect dots of the same colour to clear them | 4 000+ handcrafted levels; weekly events; minimalist palette is widely imitated. |
| 6 | **Monument Valley 2** | ustwo games | Optical‑illusion architecture; rotate/twist to make a path | The premium gold standard for UI/art. $4.99 paid, no ads — proves the high‑craft model. |
| 7 | **Flow Free / Flow Fit** | Big Duck Games | Connect coloured endpoints with non‑crossing paths covering the grid | Clean rule, deep state space, scales from 5×5 → 14×14 — perfect "easy to learn, hard to master". |
| 8 | **Hexologic** | MythicOwl | Sudoku on a hex grid; sums per direction must match | Shows how a classic genre can be re‑skinned with a fresh geometry for novelty. |
| 9 | **Linelight / Mini Metro / Null State** | various | Minimalist line / node / management puzzles | Reference titles for the "premium minimalism" aesthetic the user asked for. |
| 10 | **Tetris / Candy Crush Saga** | TTC / King | Falling blocks / match‑3 | Benchmarks for liveops, daily streaks, and 1B+ download economics. |

### What the top performers have in common

1. **One‑sentence rule** you can teach in <10 seconds.
2. **Difficulty curve that fans out** — gentle for the first ~30 levels,
   then branches into chains of expert techniques (Sudoku model).
3. **Calm, minimalist UI** with tactile micro‑animations and haptics on every
   interaction.
4. **No timers in the casual mode** (per Arrow Puzzle / Two Dots reviews) —
   timers go in optional ranked / event modes.
5. **Daily puzzle + streak** as the retention backbone.
6. **Hybrid monetization** — rewarded video for hints/revives, low‑friction
   IAP for ad removal, optional cosmetic skins.
7. **Adaptive assistance** (Block Blast "God Mode", Sudoku hints) that fights
   churn without making the game trivial.

---

## 2. Game Ideas We Could Build

Each idea below is original but borrows mechanically from the reference set,
fits a Flutter client + Go backend, and has a clear "easy to start, hard to
master" curve.

### Idea A — **GridGo: Arrow Maze** *(recommended starter)*

- **Mechanic.** A grid of arrows, each pointing N/E/S/W (later NE/SE/SW/NW
  and "split" arrows). Tap an arrow to fire it; it travels in its direction
  until it leaves the board or hits another arrow. Clear the board without
  any collisions. Bonus stars for solving in the minimum tap count.
- **Why.** Direct evolution of the Arrow Puzzle genre the user named. The
  rule fits in one screenshot. State space is huge but the engine is tiny
  (perfect for a Go solver service that auto‑generates and rates levels).
- **Skill ramp.** 5×5 with 4 arrows (beginner) → 9×9 with split/teleport
  arrows + move‑limit constraints (expert).
- **Live features.** Daily seed puzzle, weekly community puzzle leaderboard,
  "puzzle of the week" designed by a player.
- **Tech fit.** Pure deterministic logic ⇒ trivially testable, Go backend
  generates + verifies levels server‑side, Flutter renders a 2D grid with
  Flame for animation.

### Idea B — **HexLogic Daily**

- **Mechanic.** Sudoku‑style hex grid (à la Hexologic): each of the three
  axes has a target sum; place dots 1–3 in each cell so axis sums match.
- **Why.** Gives us the proven Sudoku retention loop (daily puzzle, streaks,
  difficulty tiers) but with a less crowded visual identity than 9×9
  Sudoku, which is dominated by Easybrain.
- **Skill ramp.** Hex size 4 → 9, then "twin grids" where two boards share
  a side.
- **Tech fit.** Backend generator writes one verified puzzle per difficulty
  per day into Redis; clients fetch a tiny JSON. Solver in Go is ~200 lines.

### Idea C — **FlowState**

- **Mechanic.** Flow‑Free style path connection on rectangular and
  hexagonal boards. "Pro" mode adds bridges, warps, and one‑way tiles.
- **Why.** Flow Free's mechanic is timeless and underserved at the polish
  tier of Monument Valley. Strong daily puzzle hook.
- **Differentiator.** A *creator* mode where players design their own
  puzzles, our solver verifies uniqueness, and the best are published as
  community levels — a content flywheel.

### Idea D — **TileShift: Tactile Block Battler**

- **Mechanic.** Block Blast style 8×8 placement, but with a real‑time 1v1
  ranked mode: both players draw from the same piece queue, first to
  trigger a 5‑line combo wins.
- **Why.** Shows off the Go matchmaking backend; piggy‑backs on Block
  Blast's familiar rule set.
- **Risk.** Block Blast clones are saturated — only worth pursuing if we
  commit to the multiplayer twist.

### Idea E — **Riddle Lab** (Brain Test–style, but curated)

- **Mechanic.** Bite‑sized lateral‑thinking levels, each its own
  micro‑interaction (shake, drag off‑screen, combine objects). Levels are
  authored as small Dart widgets + a JSON puzzle spec.
- **Why.** Highest viral coefficient in the reference set.
- **Risk.** Content‑heavy. Each level is bespoke, so velocity is the bottleneck.

> **Recommendation:** Start with **Idea A (GridGo: Arrow Maze)**. It is the
> closest match to what the user described, has the tightest scope for a v1
> (one rule, one screen), and exercises every part of the stack we want to
> learn. Idea B is a strong second app and shares ~80% of the codebase.

---

## 3. Architecture Plan (Flutter + Dart + Go + Docker)

```
 ┌────────────────────────────┐         ┌─────────────────────────────┐
 │  Flutter / Dart client     │ HTTPS   │  Go API (gin/chi)           │
 │  • UI in Material 3        │  +      │  • /levels  /daily  /score  │
 │  • Flame for board anim    │ WSS     │  • JWT auth (sign‑in w/     │
 │  • Riverpod state          │         │    Google Play Games)       │
 │  • Hive for offline cache  │         │  • WebSocket hub for        │
 └──────────────┬─────────────┘         │    multiplayer (Idea D)     │
                │                       └──────────┬──────────────────┘
                │                                  │
                │                                  ▼
                │                       ┌─────────────────────────────┐
                │                       │  Redis                      │
                │                       │  • daily‑puzzle cache       │
                │                       │  • leaderboards (ZSET)      │
                │                       │  • matchmaking queue (Idea D)│
                │                       └──────────┬──────────────────┘
                │                                  │
                │                                  ▼
                │                       ┌─────────────────────────────┐
                │                       │  PostgreSQL                 │
                │                       │  • users, scores, levels    │
                │                       │  • puzzle definitions       │
                │                       └─────────────────────────────┘
                │
                ▼
       Google Play Billing  +  AdMob (rewarded video, interstitial)
```

### Why this shape

- **Stateless Go API in Docker** behind a load balancer scales horizontally.
  All session state lives in Redis / Postgres, so any pod can serve any
  request.
- **Redis ZSET** is the standard pattern for leaderboards (O(log N) inserts,
  cheap top‑N reads).
- **WebSocket hub** is only needed for the multiplayer mode; for the
  single‑player puzzles, plain REST is enough — keep it simple.
- **Puzzle generation runs server‑side** in a Go worker, so we can ship new
  daily puzzles without app updates and prevent client‑side cheating on
  ranked modes.
- **Flutter + Flame** gives us one codebase for Android / iOS (and later
  web) with native‑feeling animation. Flame is a good fit specifically for
  2D grid puzzles.

### Repository layout (proposed)

```
gridgo/
├── client/                # Flutter app
│   ├── lib/
│   │   ├── ui/            # screens, theming, design tokens
│   │   ├── game/          # Flame components (board, arrow, fx)
│   │   ├── data/          # API client, offline cache
│   │   └── state/         # Riverpod providers
│   └── pubspec.yaml
├── server/                # Go services
│   ├── cmd/api/           # HTTP/WS entrypoint
│   ├── cmd/generator/     # daily puzzle generator job
│   ├── internal/puzzle/   # solver + level rater
│   ├── internal/store/    # postgres + redis adapters
│   └── go.mod
├── deploy/
│   ├── Dockerfile.api
│   ├── Dockerfile.generator
│   └── docker-compose.yml # local dev: api + redis + postgres
└── README.md
```

### UI / UX north star

- Material 3 dynamic colour, but with a custom 4‑colour palette per "world".
- Every tap = 60–120 ms spring animation + soft haptic.
- Onboarding is **playable**: the first 3 puzzles teach the rule with no
  text, à la Monument Valley.
- Accessibility from day one: colour‑blind safe palette, scalable font
  sizes, optional reduced‑motion.
- Dark mode is the default; light mode is a polished alternative, not an
  afterthought.

### Monetization (hybrid, retention‑safe)

- **Rewarded video:** "+1 hint", "skip level after 3 fails", "double daily
  reward". Opt‑in only — do not gate progression.
- **Interstitial:** at most once per N completed levels, never mid‑puzzle.
- **IAP:** $3.99 one‑time "Remove Ads + cosmetic theme pack". Optional
  $0.99 cosmetic packs after launch.
- **No energy / lives.** Reviews of the Arrow Puzzle clones repeatedly
  punish heavy ad / lives systems; we differentiate on respect for the player.

### Scalability notes for "large audience playing at the same time"

- API pods are CPU‑bound on JSON encoding — start with 2 vCPU / 512 MB
  pods, autoscale on RPS.
- Daily puzzle endpoint is hit by every active user near 00:00 UTC. Cache
  the response in Redis with a long TTL and serve via CDN edge for the
  static JSON.
- Leaderboards: shard ZSETs by region + day to keep hot keys reasonable.
- For the multiplayer mode, follow the standard pattern: stateless
  matchmaker reads from a Redis queue and assigns to game‑server pods;
  consider [Agones](https://github.com/googleforgames/agones) on
  Kubernetes when DAU justifies it.

---

## 4. Suggested First Milestones

1. **Week 1 — Prototype the rule.** Flutter + Flame, single hard‑coded
   level, tap to fire arrow, collision detection. Goal: prove the feel.
2. **Week 2 — Level format + solver.** Define puzzle JSON. Write the Go
   solver that, given a level, returns whether a solution exists and its
   minimum tap count. Use it to grade levels Easy / Medium / Hard / Expert.
3. **Week 3 — Backend + daily puzzle.** Stand up the Go API in Docker
   Compose with Postgres + Redis. `/daily` returns one puzzle per
   difficulty per day.
4. **Week 4 — UI polish + onboarding.** Theme system, animations, haptics,
   3‑level wordless tutorial, settings screen, accessibility pass.
5. **Week 5 — Liveops + telemetry.** Streaks, leaderboards, AdMob +
   billing integration, Crashlytics, analytics.
6. **Week 6 — Closed beta on Play Console.** 50 testers, iterate on
   difficulty curve and ad placement. Then production rollout.

---

## 5. Open Questions for the User

These would tighten the plan further:

1. **Solo or social?** Is Idea A (single‑player + leaderboards) enough for
   v1, or do we want real‑time 1v1 in the first release? Solo is much
   faster to ship.
2. **Premium or free‑to‑play?** Hybrid F2P is the default in this doc. If
   you'd prefer a Monument‑Valley‑style paid app, the architecture
   simplifies significantly (no ads SDK, no rewarded flow).
3. **Art direction.** Minimalist‑geometric (Linelight, Mini Metro) or
   warm‑illustrative (Two Dots, Monument Valley)? This decision drives
   the entire design system.
4. **Markets.** Worldwide from day one, or India / SEA first? Affects
   pricing tiers, ad eCPM expectations, and language packs.

---

## Sources

- [The 20 Most Popular Puzzle Games For Android Ever — AppBrain](https://www.appbrain.com/apps/most-downloaded/puzzle)
- [Best Puzzle Games for Android in 2026 — Tummy Games](https://tummygames.com/blog/best-puzzle-games-android)
- [Best puzzle games for Android phones and tablets in 2026 — Pocket Gamer](https://www.pocketgamer.com/android/best-puzzle-games-android/)
- [Best Android Puzzle Games in 2026 — Peakaso Games](https://peakaso.com/blog/best-android-puzzle-games-2026)
- [Arrows – Puzzle Escape on Google Play](https://play.google.com/store/apps/details?id=com.ecffri.arrows&hl=en_US)
- [Arrow Puzzle: Tap Puzzle Games on Google Play](https://play.google.com/store/apps/details?id=com.easybrain.arrow.puzzle.game&hl=en_US)
- [Arrow Out on Google Play](https://play.google.com/store/apps/details?id=com.arrow.out&hl=en_US)
- [Block Blast Review: 40 M DAU & $1 M/day — Felix Braberg](https://felixbraberg.substack.com/p/block-blast-review-what-is-behind-b38)
- [Block Blast monetization deconstruction — Balancy](https://balancy.co/blog/2025/03/26/how-could-block-blast-by-hungry-studio-earn-more-monetization-and-gameplay-deconstruction/)
- [Brain Test: Tricky Puzzles overview — LDPlayer](https://www.ldplayer.pro/brain-test-tricky-puzzles/)
- [Sudoku Puzzle Difficulty Levels Explained — SudokuGames Blog](https://www.sudokugames.org/blog/sudoku-puzzle-difficulty-levels)
- [Hexologic on the App Store](https://apps.apple.com/us/app/hexologic-sudoku-puzzle-game/id1343246862)
- [Flame Engine — Official site](https://flame-engine.org/)
- [flame-engine/flame on GitHub](https://github.com/flame-engine/flame)
- [Flutter Game Development: Is Flame a Real Competitor in 2025? — Genieee](https://genieee.com/flutter-game-development-is-flame-a-real-competitor-in-2025/)
- [Mobile Game Monetization in 2026 — TekRevol](https://www.tekrevol.com/blogs/mobile-game-monetization/)
- [Mobile Game Monetization Models That Still Work in 2026 — StudioKrew](https://studiokrew.com/blog/mobile-game-monetization-models-2026/)
- [Building a Multiplayer Game with WebSockets, Go and DynamoDB — serialized.net](https://serialized.net/2020/09/multiplayer/)
- [Designing a Simple Real‑Time Matchmaking Service — Medium](https://yashh21.medium.com/designing-a-simple-real-time-matchmaking-service-architecture-implementation-96e10f095ce1)
- [Scaling Dedicated Game Servers with Kubernetes (Part 1) — Game Developer](https://www.gamedeveloper.com/programming/scaling-dedicated-game-servers-with-kubernetes-part-1-containerising-and-deploying)
- [Agones — Dedicated Game Server Hosting on Kubernetes](https://github.com/googleforgames/agones)
- [How to Use Redis at Scale with Golang and Kubernetes — Mattermost](https://mattermost.com/blog/how-to-use-redis-at-scale-with-golang-and-kubernetes/)
