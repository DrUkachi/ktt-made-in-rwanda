# dispatcher.md — Weekly Leads Workflow for Offline Artisans
### S2.T1.3 · 'Made in Rwanda' Content Recommender · Product & Business Artifact

---

## 1. The Problem This Solves

The recommender system knows, in real time, which product types buyers are searching for.
An artisan leatherworker in Nyamirambo — no smartphone, intermittent data, low bandwidth
— gets none of that signal today. She restocks based on intuition, not demand.

This document describes how that signal gets from the server to her hands every week.

---

## 2. System Architecture (Data Flow)

```
 Buyer search queries
        │
        ▼
 Recommender (recommender.py)
        │  top-5 results per query, logged to DB
        ▼
 Nightly Aggregation Job (cron, 23:00 EAT)
        │  per-artisan: query_count, top product types, click count
        ▼
 Lead Digest Table  ──────────────────────────────────────────────┐
        │                                                          │
        ▼                                                          ▼
 SMS Gateway (MTN API)                              Coordinator Dashboard
 → artisans with phones                             → weekly PDF summary
        │                                                          │
        ▼                                                          ▼
 Artisan's feature phone                         Field Agent Visit / Voice Call
 (SMS, 160 chars, Kinyarwanda)                   (for non-readers / no phone)
```

---

## 3. Who Aggregates the Data

**Role: Cooperative Field Coordinator**

A single part-time coordinator, employed by a registered cooperative such as
[Inzora Cooperative](https://inzoracooperative.com) or the Rwanda Cooperatives
Confederation (RCC), manages the lead pipeline for 20 artisans.

Responsibilities:
- Runs or schedules the nightly aggregation script
- Reviews the weekly lead digest for anomalies (e.g. zero queries = data gap)
- Sends or triggers SMS dispatch every **Saturday at 08:00 EAT**
- Makes voice calls to 3–5 artisans per week who cannot receive SMS
- Visits 2 artisans per week in person (rotation) for illiteracy cases or high-value leads

One coordinator can manage 40–60 artisans at scale (2 hours/week of admin work).

---

## 4. Weekly Leads Workflow — Step by Step

| Day | Who | Action |
|-----|-----|--------|
| Mon–Fri | Recommender server | Logs every query → product match in the lead DB |
| Friday 23:00 | Cron job | Aggregates 7-day window: query count, top search terms, click count per artisan |
| Saturday 07:30 | Coordinator | Reviews dashboard; flags artisans with >50 queries (high-demand alert) |
| Saturday 08:00 | SMS gateway | Dispatches weekly digest SMS to all artisans with a registered phone number |
| Saturday 09:00–12:00 | Coordinator | Voice-calls artisans without SMS capability (5–10 min call, reads digest aloud) |
| Wednesday | Coordinator | Field visit (2 artisans/week on rotation) to collect conversion feedback |
| Friday | Coordinator | Logs sales reported by artisans; updates conversion tracker |

---

## 5. What Numbers Are Shared With the Artisan

Three numbers only — chosen to be actionable without overwhelming:

| Number | Why it matters | Example |
|--------|---------------|---------|
| **Weekly query count** | Shows demand volume for their product type | "23 people searched for leather sandals this week" |
| **Top search phrase** | Tells them what buyers are calling the product | "Most said 'Kigali leather sandals'" |
| **Leads last month → sales reported** | Closing the loop on conversions | "Last month: 18 leads → 3 sales reported" |

**Deliberately excluded:** individual buyer names/contacts (privacy), exact addresses,
platform revenue figures. Artisans receive demand signals, not personal data.

---

## 6. SMS Digest Templates

### 6a. Standard weekly digest (English)

> **INZORA ARTS** [Week 22]:  
> 23 buyers searched YOUR products this week.  
> Top item: leather sandals.  
> Last month: 18 leads → 3 sales.  
> Questions? Call 0788-300-200.

*(156 characters — fits one SMS)*

---

### 6b. Standard weekly digest (Kinyarwanda)

> **INZORA**: Iki cyumweru, abantu **23** basabye ibicuruzwa byawe.  
> Cyane: sandali z'uruhu.  
> Kwezi gushize: abakiriya 18 → kugurisha 3.  
> Indirimbo: 0788-300-200.

*(148 characters — fits one SMS)*

**Word choice justification:**

- **"abantu 23"** (23 people) rather than "leads" or "queries" — the artisan
  understands "people", not analytics jargon. The number 23 was chosen as the
  example because it is specific enough to feel real and actionable (vs. a round
  number like "20"), signalling accurate measurement.
- **"sandali z'uruhu"** (leather sandals) — the actual product name in Kinyarwanda,
  not a category code. The artisan knows what to stock.
- The coordinator's **phone number** (not a URL) — the artisan has no browser.

---

### 6c. High-demand alert (>50 queries in one week)

> **INZORA ALERT**: Abantu **61** basabye ibicuruzwa nk'ibyawe iki cyumweru —  
> inshuro 2.5 isanzwe. Twifashishe gutera imbere. Hamagara: 0788-300-200.

*Translation: "61 people searched for products like yours this week — 2.5× usual.  
Let us help you prepare. Call 0788-300-200."*

---

### 6d. Voice call script (for artisans without SMS / with low literacy)

Field agent reads the following aloud (Kinyarwanda):

> "Muraho [name]. Ndi [agent name] wo muri Inzora.  
> Iki cyumweru, abantu **[N]** basabye ibicuruzwa nk'ibyawe kuri interineti —  
> cyane cyane **[top product]**.  
> Kwezi gushize mwakiriye abakiriya **[M]** hanyuma mwagurishije **[S]** inshuro.  
> Hari ikibazo? Turaza ku ya [date] mu gitondo."

*Translation: "Hello [name]. I'm [agent] from Inzora. This week, [N] people searched  
for products like yours online — especially [top product]. Last month you had [M] leads  
and [S] sales. Any questions? We'll visit on [date] morning."*

---

## 7. Conversion Funnel (Weekly, Per Artisan)

```
~30 queries match artisan's product type in top-5
        │  (signal shared via SMS/call)
        ▼
~6 buyers click through to product page         (20% click rate)
        │
        ▼
~2 buyers make contact (DM, WhatsApp, call)     (30% of clicks)
        │
        ▼
~0.6 sales per week                             (30% contact → sale)
        │
        ▼
~2–3 sales per month per artisan
Avg transaction: 25,000 RWF (~$18)
Monthly GMV per artisan: ~65,000 RWF (~$47)
```

---

## 8. Three-Month Pilot — 20 Artisans

### Pilot scope

- **20 artisans**: 8 leather, 6 basketry, 4 jewellery, 2 apparel — all in Kigali
  (Nyamirambo, Kimironko, Remera)
- **1 field coordinator**: 2 days/week (part-time contract)
- **Duration**: 12 weeks
- **Success criteria**: ≥15 artisans report ≥1 sale attributed to a platform lead

### Onboarding per artisan

| Step | Who | Time | Cost (RWF) |
|------|-----|------|------------|
| Register artisan + products in catalog | Coordinator + artisan | 45 min | — |
| Photo the products (coordinator's phone) | Coordinator | 20 min | — |
| Explain SMS digest, teach feedback loop | Coordinator | 30 min | — |
| SIM registration check / top-up | Cooperative fund | — | 1,000 |
| Printed product card (QR + price, for market stall) | Print shop | — | 500 |
| **Total per artisan** | | **~1h 35min** | **1,500 RWF (~$1.10)** |

### Pilot cost breakdown (3 months)

| Item | Calculation | Cost (RWF) | Cost (USD) |
|------|-------------|------------|------------|
| Field coordinator (part-time) | 50,000 RWF/month × 3 | 150,000 | $110 |
| VPS hosting (recommender + DB) | $6/month × 3 | 24,600 | $18 |
| SMS gateway (MTN Rwanda API) | 20 RWF/SMS × 2/week × 20 artisans × 12 weeks | 9,600 | $7 |
| Artisan onboarding (SIM + print cards) | 1,500 RWF × 20 | 30,000 | $22 |
| Contingency (10%) | | 21,420 | $16 |
| **Total** | | **235,620 RWF** | **~$173** |

### Unit economics

| Metric | Value |
|--------|-------|
| **Cost per artisan onboarded** | 11,781 RWF (~$8.65) |
| **Cost per lead delivered** | ~33 RWF (~$0.02) *(7,200 lead-notifs over 12 weeks)* |
| **Cost per sale attributed** | 1,960 RWF (~$1.44) *(~120 sales expected over pilot)* |
| **Break-even GMV** | 2,946,000 RWF ($2,160) *(at 8% platform commission)* |
| **Expected pilot GMV** | 3,750,000 RWF ($2755) *(20 artisans × 2.5 sales/month × 25,000 RWF × 3 months)* |
| **Platform revenue at expected GMV** | 300,000 RWF (8% × 3,750,000)* |
|**Surplus above break-even** | 64,320 RWF (300,000 − 235,680 =  ~$47) |
| **Pilot GMV vs break-even** | **1.27× over break-even** |

### Key risks and mitigations

| Risk | Mitigation |
|------|------------|
| Artisan changes phone number | Coordinator verifies number at each field visit |
| Low SMS literacy | Voice call protocol (Section 6d); field visit rotation |
| Artisan doesn't report sales → funnel blind | Simple tally card left at artisan's stall; coordinator collects weekly |
| Power outage kills server batch job | Cron retry on next boot; coordinator manually triggers if digest is delayed >2 hrs |
| Artisan has no phone at all (~3 of 20 expected) | Cooperative visit + printed weekly lead sheet left at stall |

---

## 9. Scale-Up Path (Month 4+)

After a successful 3-month pilot:

- **40 artisans**: add 1 more coordinator; SMS costs scale linearly ($7 → $14/month)
- **USSD integration**: artisans dial *384# on any feature phone to check their live
  lead count between SMS digests — no data required
- **Voice IVR**: automated Saturday morning call in Kinyarwanda for fully illiterate
  artisans, using a pre-recorded message with the week's numbers inserted via TTS
- **WhatsApp Business API**: for the ~30% of artisans who have smartphones but
  prefer WhatsApp over SMS (free tier covers 1,000 conversations/month)
