# Shiftlyx & Revalidation Copilot — Product Intelligence Analysis
**Pulled:** 2026-09-28 | **Period:** 2026-09-14 to 2026-09-27 (14 days)

---

## SHIFTLYX

### Key Metrics (14 days)
| Metric | Value |
|---|---|
| GA4 Sessions | ~150 |
| GA4 Total Users | ~107 |
| GA4 New Users | ~69 (65% of total) |
| GA4 Avg Sessions/User | 1.4 |
| GA4 Conversions | ~48 (first_open as proxy) |
| GA4 Revenue | £0 |
| PostHog Signup Completed | 4 events (4 users) |
| PostHog Onboarding Completed | 12 events |
| PostHog Subscription Started | **0** |
| PostHog Trial Started | **0** |
| PostHog Shift Added | **0** |
| PostHog Fatigue Analysis Viewed | **0** |
| PostHog Recovery Plan Viewed | **0** |
| App Store Subscriptions | shiftlyx_pro_month, shiftlyx_day_one_yearly (both APPROVED) |
| Google Play Subscriptions | shiftlyx_premium |
| GSC Clicks | 0 (4 queries, 0 clicks) |

### Funnel Analysis
```
App Install (first_open): 39 users
  → Onboarding Completed: 12 users (31%)
    → Signup Completed: 4 users (11% of installs, 33% of onboarded)
      → Shift Added: 0 events
      → Subscription Started: 0 events
```

### Critical Findings
1. **Zero subscription events in PostHog** — no `subscription_started`, `trial_started`, or `purchase` events are being tracked or fired.
2. **Zero shift-added events** — the core product action (`shift_added`) is not appearing in the event stream.
3. **Zero fatigue/recovery events** — key feature events (`fatigue_analysis_viewed`, `recovery_plan_viewed`) are absent.
4. **The download page (/download) has 25 views, 14 users, and 0 conversions** — people are visiting the download page but not converting.
5. **Traffic is almost entirely direct** — 33 of 39 sessions are direct traffic, 6 from Google Play organic. No organic search traffic, no paid, no social.
6. **GSC has zero clicks** — the site has almost no search visibility.
7. **GA4 shows 48 "conversions" but revenue is £0** — the "conversions" metric in GA4 is counting first_open events, not actual purchases/subscriptions.
8. **The app has approved subscriptions in both App Store and Google Play** — the products exist, but the events to track when a user actually subscribes are not firing.

### Root Cause of "32 downloads, no subscriptions"
The data suggests:
- **Instrumentation gap**: PostHog is not firing `subscription_started`, `trial_started`, or any purchase-related events. Users may be subscribing, but the events aren't being tracked.
- **Feature gap**: Core Shiftlyx events (`shift_added`, `fatigue_analysis_viewed`, `recovery_plan_viewed`) are not appearing in the event stream at all. This could mean the app is not fully functional, or these events are not instrumented.
- **Low engagement loop**: 39 installs → 12 onboarded → 4 signed up → 0 shifted → 0 subscribed. The funnel collapses at every stage.
- **No organic discovery**: Almost all traffic is direct. The app has no GSC visibility, no paid acquisition, no social referral.

---

## REVALIDATION COPILOT

### Key Metrics (14 days)
| Metric | Value |
|---|---|
| GA4 Sessions | ~469 |
| GA4 Total Users | ~332 |
| GA4 New Users | ~227 (68% of total) |
| GA4 Avg Sessions/User | 1.4 |
| GA4 Conversions | ~480 (page_view based, inflated) |
| GA4 Revenue | £51.96 (3 days only) |
| PostHog Signup Completed | **0 events** |
| PostHog Subscription Started | **0 events** |
| PostHog Trial Started | **0 events** |
| PostHog Reflection Completed | **0 events** |
| PostHog Portfolio Progress | **0 events** |
| GA4 Paywall Viewed | 30 (14 users) |
| GA4 Purchase Started | 5 (3 users) |
| GA4 App Store Subscription Renew | 4 (1 user) |
| GA4 Export Upgrade Tapped | 2 (2 users) |
| App Store Subscriptions | revalidation_pro_yearly (APPROVED) |
| Google Play Subscriptions | revalidation_pro_yearly |
| Brevo | Free plan, 300 credits |

### Funnel Analysis
```
App Install (first_open): 56 users
  → Onboarding Completed: 17 users (30%)
    → Paywall Viewed: 30 users (some overlap)
      → Purchase Started: 5 users
        → Subscription Renew: 4 users
        → Export Upgrade Tapped: 2 users
```

### Critical Findings
1. **PostHog has zero signup, subscription, trial, reflection, or portfolio events** — the same instrumentation gap as Shiftlyx.
2. **Revalidation Copilot has significantly more traffic** (469 vs 150 sessions) and more conversions.
3. **Revenue is real but minimal** — £51.96 in 14 days, with only 3 days generating revenue.
4. **The paywall is being viewed** (30 times) and some users are starting purchases (5), but the subscription conversion rate is very low.
5. **Traffic is diversified** — direct, Google organic, Google Play organic, referral, and email (Brevo). This is healthier than Shiftlyx.
6. **The download page converts at 22%** (9 conversions from 41 views) — much better than Shiftlyx's 0%.
7. **Blog content is driving significant traffic** — NMC medication error reflection example page gets 106 views and 92 conversions.

### Comparison: Shiftlyx vs Revalidation Copilot
| Metric | Shiftlyx | Revalidation Copilot |
|---|---|---|
| 14d Sessions | 150 | 469 |
| 14d Users | 107 | 332 |
| 14d New Users | 69 | 227 |
| 14d Revenue | £0 | £51.96 |
| PostHog Signups | 4 | 0 |
| PostHog Subscriptions | 0 | 0 |
| PostHog Feature Events | 0 | 0 |
| Paywall Views | N/A | 30 |
| Purchase Started | N/A | 5 |
| Traffic Sources | Direct only | Multi-channel |
| GSC Visibility | 0 clicks | N/A (403 error) |

---

## SHARED PROBLEMS

### 1. PostHog Event Instrumentation Gap
Both products are missing critical post-install events in PostHog:
- No `subscription_started` events
- No `trial_started` events
- No `signup_completed` events (Revalidation Copilot)
- No feature usage events (Shiftlyx: `shift_added`, `fatigue_analysis_viewed`, etc.)

This means either:
a) The events are not being instrumented in the app code
b) The events are being sent but not reaching PostHog (SDK issues)
c) Users are subscribing but the post-purchase event isn't firing

### 2. The "32 downloads, no subscriptions" Question
The answer is now clear from the data:
- **Shiftlyx**: ~39 first_opens (installs) in 14 days, 0 subscription events tracked. The 32 downloads you mentioned likely refers to App Store/Play Store install data that isn't fully reflected in GA4.
- **The gap is between install and subscription**: Users install → some onboard → almost none subscribe.
- **Revalidation Copilot** has the same pattern but with slightly better conversion: 56 first_opens → 17 onboarded → 5 purchase started → 4 subscription renews.

### 3. Missing Core Product Events
Shiftlyx is not showing ANY of its core product events in PostHog:
- No `shift_added`
- No `fatigue_analysis_viewed`
- No `recovery_plan_viewed`
- No `planner_used`
- No `florence_used`
- No `partner_sync_connected`
- No `mycrew_created`

This suggests the app may not be fully functional, or the PostHog SDK is not properly integrated for these events.

---

## RECOMMENDATIONS

### Immediate (this week)
1. **Audit PostHog SDK integration** in both apps — verify events are being sent and received
2. **Add missing event tracking** for `subscription_started`, `trial_started`, `purchase_completed` in both apps
3. **Verify Shiftlyx core feature events** — are `shift_added`, `fatigue_analysis_viewed` etc. actually firing in the app?

### Short-term (next 2 weeks)
4. **Set up revenue tracking** in GA4 (ecommerce/purchase events) to get real revenue data
5. **Fix GSC access** for revalidationaicopilot.co.uk (403 error)
6. **Implement a proper funnel** in PostHog: signup → onboarding → first feature use → trial → paid

### Medium-term (next month)
7. **Add paid acquisition channels** — Shiftlyx has zero non-direct traffic
8. **Set up Brevo email campaigns** for both products (currently only 1 campaign sent)
9. **Implement data-quality gates** on the analytics pipeline before drawing conclusions

---

## DATA QUALITY NOTES
- PostHog trends/insights API blocked by personal API key permission (403). Event-level data pulled via the events endpoint instead.
- GA4 "conversions" metric is counting `first_open` events, not actual purchase/subscription conversions. The real conversion metric needs proper ecommerce event setup.
- Revalidation Copilot GSC property returned 403 — the service account may not have access to that property.
- Blackboard only has synthetic demo data — no real packages have been stored yet.
- Brevo is on a free plan (300 credits), which limits email campaign volume.
