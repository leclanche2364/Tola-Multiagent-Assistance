# Tola Brief — Growth Pipeline
**Run:** 2026-10-02T05:03:03.397710+00:00
**Products:** Shiftlyx + Revalidation Copilot

## Quality Summary

- revalidation_copilot: FAIL
- shiftlyx: FAIL

## Prioritized Plans

### revalidation_copilot
Pipeline blocked by data-quality FAIL: data-quality FAIL: ['sources_fresh']

### shiftlyx
Pipeline blocked by data-quality FAIL: data-quality FAIL: ['sources_fresh']

## Key Actions (AUTO)
- [x] Pull GA4 data for both products ✅
- [x] Pull website_events from Supabase ✅
- [x] Run data-quality gates ✅
- [x] Store results on blackboard ✅

## Key Actions (GATED — require human approval)
- [ ] Fix GSC service account permissions for both properties
- [ ] Fix PostHog authentication tokens
- [ ] Fix Brevo API adapter parameter naming
- [ ] Publish any experiment changes to production

## Data Quality Flags
🚨 revalidation_copilot: data-quality FAIL — ['sources_fresh']
🚨 shiftlyx: data-quality FAIL — ['sources_fresh']

## Source Refs
- GA4: `ga4:run_report` (RC=222 rows, SH=125 rows)
- website_events: `supabase:fetch_events` (RC=188, SH=188)
- PostHog: `posthog:get_recent_events` (403 errors)
- GSC: `gsc:get_search_analytics` (403/permission errors)
- Brevo: `brevo:get_campaigns` (400 error)
- App Store: `asc:get_app_store_apps` (2 apps)

*Tola brief — prioritized plans only, never raw data dumps.*