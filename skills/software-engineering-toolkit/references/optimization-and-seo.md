# Conditional performance and SEO candidates

## Decision rule

On every project turn evaluate applicability and new evidence for these candidates; perform relevant reasonable improvements. Preserve required behavior, correctness, accessibility, privacy, security, resource limits, and architecture. State the intended benefit and verify it proportionately. Do not repeatedly run an unchanged audit without a useful purpose.

Routine changes within existing capabilities can proceed under the project's authorization. Obtain a developer decision for major refactoring, architecture changes or new third-party integrations; explain benefit, impact, cost, maintenance, constraints, and alternatives. Record approvals, rejections or deferrals with timestamps/rationale in the decision file and affected records. If impact or relevance is ambiguous, ask before dependent work.

Do not install a CDN, load balancer, cache service, pooler, framework or account merely because it appears here. Shared-host limitations are a reason to establish applicability and discuss alternatives, not silently mark a requirement satisfied.

## All performance candidates

| Candidate | Project-specific consideration |
|---|---|
| 1. Compress images, preferably losslessly | Preserve originals where needed, fidelity and asset identity; measure delivered size |
| 2. Lazy loading | Identify noncritical resources; preserve timely loading of critical content |
| 3. Split code into chunks | Use compatible existing build capabilities; verify loading behavior |
| 4. Cache API responses | Define eligible data, authorization boundaries, keys, freshness and invalidation |
| 5. Add CDN | Discuss new provider/integration and actual benefit; confirm content and access behavior |
| 6. Minify JS/CSS | Fit existing build/deployment and retain debuggability/source handling |
| 7. Index the database | Inspect actual queries, write/storage costs, migration impact and engine support |
| 8. Reduce unnecessary renders | Use actual render/state evidence; preserve visible behavior |
| 9. Debounce input handlers | Apply to suitable interactions without delaying required responses |
| 10. Paginate large lists | Preserve search/filter/order/access rules and usability |
| 11. Remove unused dependencies | Establish actual non-use including dynamic/build/runtime paths; verify affected behavior |
| 12. Defer noncritical scripts | Preserve dependency order and required functionality |
| 13. Loading skeletons | Match actual loading states and accessible behavior; do not disguise persistent failure |
| 14. Add load balancer | Requires demonstrated need and supported topology; developer decides infrastructure changes |
| 15. Compress API payloads | Confirm supported client/server mechanisms and useful savings |
| 16. Database connection pooling | Confirm runtime/driver/host support and connection lifecycle; no assumed external pooler |
| 17. Cache expensive queries | Define safe keys, invalidation, user/tenant isolation and resource limits |
| 18. Fix N+1 queries | Verify actual access patterns and avoid changing business/access semantics |
| 19. Server-side caching | Use supported mechanisms with freshness/invalidation and private-data boundaries |
| 20. Lighthouse audit | Use for applicable web surfaces; record environment/results and act on relevant findings |

## All SEO candidates

Apply to relevant web/public-discovery surfaces; do not add web SEO features to unrelated native/game components. Confirm intended indexing for each page class. Do not infer that every publicly reachable URL belongs in search results. Private routes also require actual access controls; indexing directives are not authorization.

| Candidate | Required interpretation |
|---|---|
| 1. Build sitemap.xml | Include appropriate canonical public URLs, following actual route/indexing policy |
| 2. Add robots.txt | Reflect confirmed crawler policy; avoid contradictory indexing assumptions |
| 3. Remove noindex where appropriate | Only for pages confirmed intended for indexing; preserve intentional exclusions, including relevant private/admin/privileged pages |
| 4. Canonical tags | Reflect intended equivalent/preferred URLs rather than pointing distinct pages at an arbitrary default |
| 5. Meta titles/descriptions | Accurate, useful, page-specific content |
| 6. Heading order/hierarchy | Clear semantic structure aligned with actual page content |
| 7. Alt text | Accurate purpose/context; handle decorative images appropriately without keyword filler |
| 8. Schema markup | Only applicable types/properties supported by actual page content and project facts |
| 9. Internal links | Relevant navigation/content links with working, authorized destinations |
| 10. Fix broken links | Verify destinations and intended redirects; do not invent replacements |
| 11. Compress images | Share the performance workflow; avoid duplicate or lossy repeat processing |
| 12. Improve Core Web Vitals | Use relevant measurements and verify useful changes |
| 13. Fix mobile layout | Test applicable viewport, content and interaction behavior |
| 14. Enforce HTTPS | Confirm deployment/certificate/proxy capabilities and avoid redirect or mixed-content regressions |
| 15. Clean URL slugs | Account for existing links, identifiers, redirects and compatibility; discuss material changes |
| 16. Add og:image | Use a relevant approved image and correct reachable metadata |
| 17. Verify Search Console | Coordinate account/domain access and ownership; never claim verification without actual evidence |
| 18. Add LMS.txt | Clarify the developer's intended file (`llms.txt` or another file) before implementing |

Keep indexing and content claims synchronized across implementation, metadata, sitemaps, knowledge, and documents. Record audit/verification evidence and open issues. Tool scores, structured data and discovery files do not guarantee search placement.

Use current primary documentation for substantive implementation details: [Google Search Essentials](https://developers.google.com/search/docs/essentials), [Lighthouse](https://developer.chrome.com/docs/lighthouse/), and [Core Web Vitals](https://web.dev/articles/vitals). Confirm current product behavior when interacting with external search services.
