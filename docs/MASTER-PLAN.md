# Ghostpack master implementation plan and honest status
Updated 2026-09-20. This is the single source of truth for scope. "Scaffold" means code exists but end-to-end integration has NOT been demonstrated. No feature is production-ready until automated tests, Discord/Ghost integration tests, and deployment checks pass.

## 0. Release gates (NOT DONE)
- [ ] Automated CI installs dependencies and passes all tests; run security/privacy tests.
- [ ] End-to-end staging Ghost + Discord + Stripe test; verify permissions, reconnects, retries, deletion, concurrency.
- [ ] Bot VPS deploy and verified Discord login; Ghost/site/media deployments separately verified.
- [ ] No staff-only channel content or audit logs in public APIs. Public forum allowlist plus Discord effective-permission checks and explicit publication/moderation of each public reply.

## 1. Infrastructure and media (SCAFFOLD)
- [x] Compose definitions for bot, live API, media worker; private bot attachment volume; guided Ubuntu bot deployment script with smoke-test commands (not run remotely).
- [ ] Reverse proxy/TLS for ghostbot.postdated.org with strict separation of public and private API routes; secure service-to-service auth.
- [ ] Ghost native editor media upload handler through VPS, AVIF images, AV1 video, watermark, AV1 codec/AVIF compatibility verification, unlimited-duration Ghost uploads subject to operational limits; GhostLive video max 120 seconds.
- [ ] Async durable transcode queue, storage retention, upload-to-Ghost and public media URLs, retries/observability, malware and content validation.

## 2. Staff Discord and GhostLive (PARTIAL)
- [x] Initial /live command creates reporting thread and draft event; /end closes event; editor queue with approve/hold buttons; private attachment download and live SQLite event/update state.
- [ ] One server: staff-only @postdated channels and public community forums; actual channel creation, permission validation and migration.
- [ ] @live role required for live participation; guided /live title/description/featured image, publish Ghost live article and link to event.
- [ ] Durable approval controls after restart, editor-only hold feedback, revisions, idempotent Ghost publication and immediate media processing/upload.
- [ ] /end confirmation, thread locking, final key points and safe private archive delivery.
- [ ] Public timeline theme, refresh/SSE, verified staff badge, contributor 🌐 badge, official attribution.

## 3. Live update reactions, pins and discussion (DATA SCAFFOLD ONLY)
- [x] Live SQLite schema and public API fields for reaction counts, linked replies, author kind and single current pin; only published updates returned.
- [ ] Discord message ID <-> published update ID mapping, reaction add/remove reconciliation, up/down auto-reactions, vote deduplication, karma calculation and abuse controls.
- [ ] Editor-only 📌 pin event handler; prior pin label 'Prior key point' retained in chronological location and auditable pin history; editor-only 💡 contributor nomination, editorial review before publication.
- [ ] Each published update gets its own public Discord discussion thread/reply target; mirror permitted replies to correct site update with parent/child mapping, edit/delete handling, moderation and privacy boundary.
- [ ] Ghost theme timeline renders reactions (votes first), pinned key point, prior key point label, nested replies and author badges. Discord client reaction ordering cannot be guaranteed.

## 4. Article discussions (API SCAFFOLD ONLY)
- [x] Authenticated allowlisted article discussion metadata endpoint and public article/community snapshot read endpoints; no generic message log exposed.
- [ ] Ghost publish/update/unpublish webhook -> create/update/archive #articles forum post with headline, excerpt, featured image/video where supported, article link, linked author Discord mention.
- [ ] Persist Ghost post/forum mapping, duplicate/retry handling, tags and permissions, article-specific discussion URL.
- [ ] Ghost theme article panel with server icon, actual forum tags, total/online members (nullable), boost count, Discord purple #5865F2 button and white official Discord logo.
- [ ] Optional site comment mirror only for explicitly public, moderated replies; never copy staff-only content.

## 5. Monitors, Wire and AI (PARTIAL)
- [x] RSSHub rsstown.com HTTPS feed checks, requested intervals 5M,10M,15M,30M,60M,2H,3H,6H,8H,12H,18H,24H,48H,82H; SQLite dedupe, role pings, /monitor basic arguments, 7pm Eastern active-feeds txt, 10-day yes/no review buttons (restart recovery unimplemented).
- [ ] Guided /monitor form/modal, multiple roles and [cron][link][roles] message parser; permission checks, pause/delete/list/edit; secure RSSHub URL/network policy and robust retry/rate limits.
- [ ] Monitor discussion threads in #topics, archive on stop, AI discussion summary and key points.
- [ ] #wire AI sourced digests, breaking alerts, citations, staff review and configurable schedules/thresholds.
- [ ] Comprehensive Discord message/action audit in private SQLite with consent/retention/access controls, 7pm Eastern AI server digest; no private-to-public bridge.

## 6. Roles, payments and account linking (NOT BUILT)
- [ ] Native Ghost-editable postdated.org/link page + reusable HTML-card Discord button, secure Ghost member session and Discord OAuth linking, CSRF/state/replay protection.
- [ ] Pinned subscriber introduction notice linking to /link; Ghost/Stripe subscription verification, signed webhook + scheduled reconciliation, cancellation/grace handling, safe failure behavior.
- [ ] @postdated staff, @contributor, @subscriber paid, @reader free, @rising recent engagement, @newcomer first 14 days, @seasoned >6 months qualifying paid membership, @fresh first 24 hours.
- [ ] Bot-enforced @fresh per-member slow mode, expiry and removal, moderator exemptions, persistence, audit; subscription role reconciliation and account unlink/relink.

## 7. Editorial summaries and newsroom theme (NOT WIRED)
- [x] Standalone keypoints helper prototype.
- [ ] Published-only 3-5 key points on publish, every 30 min when changed, and final close; editor review/lock, audit and hallucination checks.
- [ ] Ghostpack responsive Ghost theme, newsletters/podcast/video layouts, Ghost native cards and end-to-end Ghost version compatibility.

## Known current defects to address before deployment
- Bot currently lacks reaction and reply event listeners and does not assign roles or create article forum posts.
- Public timeline reply storage currently has no per-reply moderation state; do not ingest arbitrary replies until it does.
- Existing docs/BOT-STATUS.md and docs/LIMITATIONS.md are outdated; use this plan and actual code for status.
- Monitor renewal views are not registered persistently after restart. Current bot deployment script and CI have not been validated end to end.
- Article discussion API metadata alone does not prove Discord forum visibility; Discord permissions must be checked before any public message mirror.
