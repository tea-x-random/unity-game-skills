# Economy-tuning sheet — a copyable structure

A practical, tool-agnostic layout for the spreadsheet that is the **source of truth for your economy
pre-launch**. Build it in any sheet tool (Google Sheets, Excel, Numbers). The goal: model expected **earn vs
spend** and **time-to-afford** per player segment so balance is a calculation, not a guess — then ship the
numbers as remote-config defaults and tune them live against ARPDAU + retention (`unity-analytics-liveops`).

Use one tab per block below. Keep every number a cell you can change in one place; downstream tabs reference
it so re-balancing is a single edit.

---

## Tab 1 — Currencies

One row per currency. Keep the list short (a soft + a hard is the casual default).

| Column | Example | Notes |
|--------|---------|-------|
| Currency | Coins | Name |
| Type | Soft / Hard | Soft = earned constantly; Hard = rare/premium/IAP |
| Earned from (summary) | Levels, daily, rewarded ads | One-line faucet summary |
| Spent on (summary) | Upgrades, retries, refills | One-line sink summary |
| Sellable via IAP? | No / Yes | Hard currency is usually the IAP-sold one |
| Starting balance | 100 | What a new player begins with (first-session generosity) |

---

## Tab 2 — Sources (faucets)

One row per way a currency enters the economy. The key output is **expected currency per day**.

| Column | Example | Notes |
|--------|---------|-------|
| Source | Level clear reward | The faucet |
| Currency | Coins | Which tank it fills |
| Amount per event | 25 | Payout per occurrence |
| Events per day (per segment) | 12 | Model separately for casual / engaged / payer |
| Expected/day | 300 | `Amount × Events/day` |
| Cap? | none / 5 per day | Daily/session caps (esp. rewarded ads) |
| Notes | scales with level length | |

Include rows for: level/round rewards, daily bonus/login streak, rewarded ads (double-coins, free-spin,
revive), achievement/milestone one-offs, IAP-granted currency. **Sum Expected/day per currency per segment.**

---

## Tab 3 — Sinks (drains)

One row per way a currency leaves the economy. Key output is **expected spend per day**.

| Column | Example | Notes |
|--------|---------|-------|
| Sink | Upgrade tier N | The drain |
| Currency | Coins | Which tank it drains |
| Cost | 500 | Price of the action |
| Frequency/day (per segment) | 0.6 | How often a player actually buys it |
| Expected/day | 300 | `Cost × Frequency/day` |
| Power? / Cosmetic? | Power | Power sinks pace difficulty; cosmetics are non-inflationary depth |
| Notes | from cost-curve tab | |

Include rows for: upgrades/progression, retries/continues, cosmetics, energy/lives refills,
consumables/boosters. **Sum Expected/day per currency per segment.**

---

## Tab 4 — Daily earn vs spend (the balance dashboard)

The headline table. One row per currency × segment, pulling totals from Tabs 2 and 3.

| Currency | Segment | Earn/day | Spend/day | Net/day | Faucet/sink ratio | Verdict |
|----------|---------|----------|-----------|---------|-------------------|---------|
| Coins | Casual | 300 | 240 | +60 | 1.25 | OK (slight surplus) |
| Coins | Engaged | 700 | 720 | -20 | 0.97 | OK |
| Coins | Payer | 900 | 1500 | -600 | 0.60 | OK (IAP covers gap) |
| Gems | Casual | 5 | 4 | +1 | 1.25 | watch |

**Faucet/sink ratio = Earn/day ÷ Spend/day.** Read it as the core balance check (see Checks below).

---

## Tab 5 — Progression cost curve

The spine of the economy: cost to advance each step, and how long it takes to afford.

| Level/Tier | Upgrade cost | Cumulative cost | Time-to-afford (free) | Time-to-afford (payer) | Power granted | Difficulty at this tier |
|-----------|--------------|------------------|------------------------|-------------------------|---------------|--------------------------|
| 1 | 50 | 50 | 0.2 day | instant | +5% | easy |
| 2 | 120 | 170 | 0.5 day | instant | +5% | … |
| … | (rising curve) | | | | | |

- **Time-to-afford (free)** = cumulative cost ÷ free Earn/day (from Tab 4). This is the long-tail engagement
  *and* the monetization-pressure gap. If it balloons into a wall, it's a churn risk, not a sale.
- Plot **Power granted vs Difficulty** — earned power should stay *slightly ahead* of difficulty. A tier where
  difficulty outruns affordable power is a **churn wall**; flatten the cost or boost the faucet.
- Early tiers: cheap/fast (habit). Later tiers: progressively dearer (long tail + reason to pay/watch).

---

## Tab 6 — IAP catalog

One row per product. Defines what's sold, at what tier, framed how.

| Product | Type | Price tier | Grants | $/unit currency | Framing | Audience |
|---------|------|------------|--------|------------------|---------|----------|
| Remove Ads | Non-consumable | $2.99 | no interruptive ads | — | one-time | converter |
| Starter Pack | Non-consumable bundle | $4.99 | 1000 coins + 50 gems + skin | best value, time-boxed | first purchase | new player |
| Gems S | Consumable | $0.99 | 50 gems | baseline | — | ladder floor |
| Gems M | Consumable | $4.99 | 300 gems (+20%) | "best value" | anchor mid | steered tier |
| Gems L | Consumable | $19.99 | 1500 gems (+50%) | high anchor | — | whale |

- Build a **price ladder** with a high anchor so mid tiers read as reasonable; mark one "best value".
- Compute **$/unit** so bigger tiers genuinely give more per dollar (honest value framing).
- Cross-check grants against Tab 5: what real progression does each pack buy? (time-to-afford saved.)

---

## Balancing checks (run these on every re-tune)

1. **Faucet/sink ratio** (Tab 4) per currency per segment. Target a *small* surplus or near-parity for free
   players (≈ 0.9–1.3) — runaway > ~1.5 trends to **inflation** (add aspirational sinks); chronically < ~0.7
   for free players risks a starved/**dead-feeling** economy or a paywall (add a faucet or lower a sink). Payer
   rows can run negative because IAP closes the gap.
2. **Time-to-afford key items** (Tab 5): is each milestone a reasonable wait for a free player and a clear
   time-save for a payer? No milestone should read as an *impassable* wall for free players (= churn).
3. **Payer vs non-payer paths:** confirm the **non-payer** can reach a satisfying end-state on ads + free
   progression alone (they're ~98% of players), and the **payer** path saves time/adds cosmetics without
   becoming pay-to-win (no raw power that ruins it for non-payers).
4. **Sink depth:** is there always *something worth wanting* (cosmetics, next tier) so the economy never dead-ends?
5. **First-session check:** does starting balance + early faucet make a new player feel rich fast (D1 lever)?
6. **Rewarded-ad balance:** with rewarded earns folded into Tab 2 (capped if needed), does heavy ad-watching
   inflate the economy or cannibalize IAP? Keep the ad path meaningful but slower than buying.

---

## From sheet to live game

- Every number in Tabs 2/3/5/6 is a candidate **remote-config key** with a safe in-code default — ship the
  sheet's values as defaults so the game works offline / before first fetch.
- Soft-launch, then **A/B one lever at a time** (a source rate, a sink cost, a price tier) against **ARPDAU +
  retention** via `unity-analytics-liveops`; promote winners. The sheet is the hypothesis; live data is the verdict.
