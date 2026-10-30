# FoodEase image delivery, navbar and scroll text

Production assets are served from `website/static/img/catalog-v7/` (160, 320, 480, 640, 960px) and `website/static/img/editorial/fast-v7/` (480, 768, 1024px). These are resized/recompressed versions of the approved artwork; no food was regenerated or redesigned. Source artwork is retained. Reproduction utility: `website/tools/optimize-delivery.py`.

- Responsive source sets match the actual cards and hero. The hero is preloaded with high priority; lower images use native lazy loading and asynchronous decoding.
- Small selection thumbnails use 160px images. Detail images and the WebGL fallback are requested on demand, rather than downloaded while hidden.
- The versioned image families use `public, max-age=31536000, immutable`. Fonts cache for one day. WebP/WOFF2 MIME types are set explicitly for Windows. Do not overwrite a versioned family; create a new version for future artwork changes. Shopping APIs retain their existing no-store policy.
- The sticky navbar starts at top 0 on desktop and phone. Its width and approved hero layout are retained.
- Static headings and supporting copy below the hero reveal on intersection with a short stagger. JavaScript absence, reduced motion, and Calm motion keep text readable. Live status/transcript content and ordering controls are excluded from reveal effects.

## Local measurement

Same desktop viewport (1440x1000), new browser contexts, 80ms simulated latency and 8Mbps download. This is a local test, not a guarantee for other devices or networks.

| Measure | Before | After |
| --- | ---: | ---: |
| Initial image transfer | 1,145,028 bytes | 407,292 bytes |
| Image transfer reduction | — | 64.4% |
| Repeat-load image network transfer | 0 | 0 |
| Observed cold LCP in this run | 7788ms | 1376ms |

Raw measurements: `artifacts/performance/before.json` and `after-cache.json`. The image and interaction audits found no missing images, no horizontal overflow at 320–1440px, a flush-top navbar, visible text after reveal, and no hidden-preview downloads at startup. Screenshots are alongside those reports.

Validation: production build, 44 JavaScript tests, 41 Python website/cache tests, and 19 browser UI/3D tests passed. All 143 optimized image files verified. Voice-worker and orchestration code/processes were unchanged. Only the owned website-only preview on port 8193 was reloaded to activate static caching; its configured orchestration target was unreachable before reload.

Current preview: http://127.0.0.1:8193/?design=delivery-7
