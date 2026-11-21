# Category requests preserve the menu

The category received from Zara now acts as a scroll target in the visual menu.
Previously, the renderer hid every dish outside that category. All catalog
sections remain available, and the existing voice-action scrolling targets the
requested heading. The category-scoped tool results still let Zara read the
requested items and prices. Search, dietary, availability and budget filters
retain their explicit filtering behavior.

The All filter stays active during category-only browsing, and the context
summary labels the category as the current section rather than claiming the
whole visual menu is limited to it. Runtime entry assets use `zara-31` with
matching static/public JavaScript copies. No worker source or configuration
change is needed for this presentation fix.

Verification:

- Reproduced the bug at 1440 px and 390 px: Karahi left only 2 dishes visible.
- 8 browser checks passed: both Urdu category entry paths (navigate/filter),
  Karahi→burgers→Karahi, all 28 dishes/9 groups, another-category cart add,
  Urdu follow-up ordering, sticky manual category jumps, slow-authority preview,
  and rapid manual filters. RTC/audio/model are synthetic in these regressions.
- 76 JavaScript and 49 website Python checks passed; browser build and JavaScript
  syntax check passed. Existing Starlette test-client deprecation warning remains.
- Live publication verification follows the Git push. No acoustic or new latency
  claims are made.
