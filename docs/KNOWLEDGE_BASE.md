# Astova Knowledge Base

> The canonical explanation of every finding the Astova engine can produce. This is the source of
> truth an AI coding agent (or a human) uses to understand and safely fix an AI Readiness issue.
> Maintained alongside the engine: every finding has a corresponding Knowledge Card here.
> Last updated: 2026-06-29. Engine report schema: v12.
>
> **Machine-readable now:** this knowledge is exposed to AI coding agents via the MCP tool
> `explain_finding(finding_id)` and the HTTP API `GET /findings/{id}`. The structured registry lives
> in `engine/astova_engine/knowledge.py`; when a card here changes, update `knowledge.py` in the same commit.

## How to read this

Findings are grouped into Knowledge Cards by shared knowledge - near-identical findings (a check's
pass/fail/length variants) share one card, listed under "# Finding ID". Each card follows a fixed
structure. Cards reference six shared guidance blocks (RB-1..RB-6) below instead of repeating them.

The single most important section in every card is **"How should an AI coding agent approach this?"** -
that is what makes this a knowledge base for agents, not a checklist.

---

## Shared guidance (RB-1 .. RB-6)

### RB-1: How AI answer engines read pages
Many AI crawlers (GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot) fetch **raw HTML and do not execute
JavaScript**. Google/Gemini and Bing/Copilot do render JS; ChatGPT, Claude and Perplexity largely do
not - so "how each engine sees you" splits on JS execution. Engines extract and **cite discrete,
self-contained chunks** (a paragraph, a list item, a Q&A pair, a schema object), weighting the top of
the page and quotable/structured units most heavily. AI Readiness therefore means: your content is in
the HTML, structured into liftable chunks, led by a direct answer, from a source the engine trusts and
can fetch. This is about retrieval and citation, never keyword ranking.

### RB-2: Why findings are VERIFIED
Every deterministic finding is read straight from the parsed HTML (or, for performance, an authoritative
Google API) and reproduces exactly on re-run. No model judgement, no sampling, no estimation. That
reproducibility is what lets a finding carry confidence = VERIFIED and lets an agent treat it as fact,
not opinion. (Visibility/citation sampling is the separate MEASURED layer and is not part of this engine.)

### RB-3: Framework head injection patterns
Where `<head>` elements (meta, link, JSON-LD) belong, per framework. Next.js: the Metadata API in
`layout.tsx`/`page.tsx` for meta/title/canonical; JSON-LD via a `<script type="application/ld+json">`
in the server component. Astro: the layout component `<head>`. WordPress: the `wp_head` hook /
`header.php`, or an SEO plugin. Static HTML: the literal `<head>`. Rules: exactly one canonical and one
title; JSON-LD as `<script type="application/ld+json">`; be idempotent (do not duplicate a tag that
already exists).

### RB-4: Framework root files
Where `robots.txt` / `llms.txt` / `sitemap.xml` live, per framework. Next.js: `public/` or the dynamic
`app/robots.ts` / `app/sitemap.ts`. Astro: `public/`. Gatsby: `static/`. WordPress: the site root or a
plugin (robots is often virtual). Static: the site root. These are site-scope files (one file affects
the whole domain); create once, and reference the sitemap from robots.

### RB-5: Safe content editing
When changing visible copy: **never invent facts, numbers, names, dates or claims**; preserve the
author's meaning and voice; locate where content is authored (MDX/markdown/CMS field/component prop),
not the rendered HTML; do not break layout or markdown/MDX/JSX syntax; propose drafts for human review
for anything user-facing; demote marketing copy below the answer rather than deleting it.

### RB-6: Verification model
A fix is verified by **re-running the specific check and asserting it now passes**, or by a structural
assertion over the resolved target (e.g. "exactly one self-referencing canonical exists"). Astova owns
the definition of "done": re-scan and read the finding status / `meta.diff`. A fix is never complete
until the check passes.

## On-page findings

---

# Finding ID
title.missing, title.length

# Name
Page title

# Summary
The page either has no `<title>` element at all (`title.missing`) or one whose length falls outside the readable 15-60 character band (`title.length`).

# Why this matters
See RB-1. AI answer engines use the `<title>` as the primary label for a page when they index, chunk, and later cite it. A missing title leaves ChatGPT, Claude, Perplexity, and Gemini with no canonical name for the page, so it gets referenced by a guessed heading or URL fragment, or dropped from candidate answers entirely. A title that is too short carries no topical signal; one that is too long gets truncated when an engine renders a source label, hiding the disambiguating part.

# How Astova detects it
See RB-2. Astova reads `soup.title.string`, strips it, and checks emptiness. If empty it emits `title.missing` (FAIL, CRITICAL). Otherwise it measures `len(title)` and emits `title.length` with PASS when `15 <= n <= 60`, otherwise WARN (MEDIUM). The character count and the first 120 characters of the title are stored as `value` and `evidence`. This is VERIFIED: it is read straight from the parsed DOM and re-running reproduces the exact count.

# Evidence Example
A failing page has `<head>` with no `<title>` (evidence: "no `<title>` element in the page `<head>`"), or a title like `"Home"` (n=4, below 15) or a 95-character marketing string that will be cut off.

# How to fix it
Add exactly one `<title>` in the document `<head>` with a unique, descriptive label of roughly 50-60 characters that names the specific page topic, not just the brand. Front-load the distinctive words.

# Framework Examples
See RB-3. Next.js: set `metadata.title` (or `generateMetadata`) in the route's `layout.tsx`/`page.tsx`. Astro: use `<title>` in the layout `<head>`, usually fed by a frontmatter/prop value. WordPress: the active theme or an SEO plugin controls the title tag; edit the template's `wp_head`/`document_title` filter or the per-page SEO field rather than hardcoding. Static HTML: edit the `<title>` in each page's `<head>` directly.

# Can Astova generate the fix?
Yes (deterministic) for `title.missing` - Astova has a deterministic generator that produces a title tag. `title.length` is a content-judgement rewrite (no deterministic generator); treat as AI assisted.

# Can an AI coding agent safely automate this?
Usually. Adding a missing title is safe. Rewriting an existing too-long/too-short title touches copy a human may care about, so it is closer to "Sometimes" - propose the new title rather than silently overwriting brand-approved wording.

# How should an AI coding agent approach this?
Search for where the page head is assembled: in Next.js look for `metadata`, `generateMetadata`, or any `<title>` in `app/`; in Astro look in `src/layouts/*.astro`; in WordPress look in `header.php` / `wp_head` hooks and SEO plugin config; in static sites grep each HTML file for `<title>`. The file most likely involved is the shared layout, because a single missing/duplicate title there often affects every route. Common mistakes: adding a second `<title>` when a layout already injects one (creates duplicates the engine will still pass but browsers ignore the second); hardcoding a title in a template that is meant to be dynamic, flattening every page to the same string; appending the brand so aggressively that the unique part is pushed past 60 chars. Do NOT change `og:title` logic or the H1 as a side effect - they are separate findings. Avoid breaking the app by keeping the title a static string or a value already available in scope; do not introduce a new async data fetch just to compute a title.

# Verification
See RB-6. Re-run the on-page scan: `title.missing` clears when a non-empty `<title>` is present; `title.length` flips to PASS when the character count lands in [15, 60].

# Related Findings
opengraph (og:title), h1.missing/h1.multiple, meta.description.missing.

# Future Improvements
Detect templated duplicate titles across crawled pages; flag titles that are pure brand boilerplate with no page-specific terms.

---

# Finding ID
meta.description.missing, meta.description.length

# Name
Meta description

# Summary
The page has no `<meta name="description">` (`meta.description.missing`) or one whose length is outside the 80-160 character band (`meta.description.length`).

# Why this matters
See RB-1. AI answer engines frequently lift the meta description as a ready-made, human-authored summary of the page when building an answer preview or deciding whether the page is relevant to a query. A missing description forces the engine to synthesise its own summary from body text, which is less controllable and may misrepresent the page. A description that is too short under-specifies the topic; too long and the engine truncates it mid-thought.

# How Astova detects it
See RB-2. Astova finds `<meta name="description">`, reads and strips its `content`. Empty/absent yields `meta.description.missing` (FAIL, MEDIUM). Otherwise it measures length and emits `meta.description.length` PASS when `80 <= n <= 160`, else WARN (LOW). The count and first 160 chars are stored. VERIFIED - read directly from the DOM.

# Evidence Example
Failing: `<head>` with no description meta (evidence: 'no `<meta name="description">` in the page `<head>`'), or a 40-character stub, or a 220-character paragraph that will be cut off.

# How to fix it
Add one `<meta name="description">` in `<head>` summarising the page in ~120-160 characters, written as a standalone sentence or two that answers "what is this page about."

# Framework Examples
See RB-3. Next.js: `metadata.description` in `layout.tsx`/`page.tsx`. Astro: a `<meta name="description">` in the layout head driven by a prop. WordPress: SEO plugin's per-page description field or a `wp_head` filter. Static HTML: add the meta tag directly per page.

# Can Astova generate the fix?
Yes (deterministic) for `meta.description.missing` - a deterministic generator emits a description meta tag. `meta.description.length` is a copy rewrite; AI assisted.

# Can an AI coding agent safely automate this?
Usually. Adding a missing description is low-risk. Rewriting length is content editing - propose, do not silently replace marketing copy.

# How should an AI coding agent approach this?
Search the same head-assembly locations as the title (`metadata` in Next.js `app/`, Astro layouts, WordPress `wp_head`/SEO field, static `<head>`). The shared layout is the most likely file when every page is missing a description. Common mistakes: setting one global description on the layout so every page shares an identical, generic summary (engines treat duplicate descriptions as low-value); confusing `name="description"` with `og:description` (they are distinct findings - fixing one does not fix the other); HTML-escaping issues when the copy contains quotes. Do NOT auto-generate descriptions by truncating the first paragraph - that often produces a half-sentence. See RB-5 for safe content editing. Keep the value a plain string available in scope.

# Verification
See RB-6. Re-run: missing clears when a non-empty description meta exists; length PASSes in [80, 160].

# Related Findings
opengraph (og:description), title.length.

# Future Improvements
Cross-page duplicate-description detection; flag descriptions that merely repeat the title.

---

# Finding ID
h1.missing, h1.multiple, h1.ok, headings.structure, onpage.heading_order

# Name
Headings & H1

# Summary
Covers the presence of exactly one H1 (`h1.missing` / `h1.multiple` / `h1.ok`), whether subheadings exist (`headings.structure`), and whether heading levels are nested without skipping (`onpage.heading_order`).

# Why this matters
See RB-1. AI answer engines split a page into retrievable chunks largely along its heading outline. The H1 names the document; H2/H3 subheadings define the extractable sections an engine quotes when answering a sub-question. No H1 leaves the page without a clear topic anchor; multiple H1s create competing topic signals; a flat page with no subheadings is one undifferentiated blob that is hard to chunk and cite; and skipped levels (H1 to H3) break the implied hierarchy the engine uses to understand which section sits under which.

# How Astova detects it
See RB-2. `find_all("h1")`: zero gives `h1.missing` (FAIL, HIGH); more than one gives `h1.multiple` (WARN, MEDIUM) with up to three H1 texts as evidence; exactly one gives `h1.ok` (PASS). `headings.structure` is PASS if any of H2-H6 exist, else WARN (LOW). `onpage.heading_order` walks all H1-H6 in document order and flags any jump where `lvl > prev + 1` (e.g. `h1→h3`), WARN (LOW) listing up to four skips; PASS if none; the check is skipped entirely when the page has no headings. All VERIFIED - counted directly from the DOM.

# Evidence Example
A `<div class="title">` styled to look like a heading but with no real `<h1>` triggers `h1.missing`. A page with both a logo `<h1>` and a content `<h1>` triggers `h1.multiple`. A page that jumps from `<h1>` straight to `<h3>` triggers `onpage.heading_order` with evidence "skipped: h1→h3".

# How to fix it
Use exactly one `<h1>` that states the page's main topic. Break content into `<h2>`/`<h3>` sections. Never skip a level - go H1, then H2, then H3, in order. Use real heading tags, not styled `<div>`s.

# Framework Examples
See RB-3 and RB-5. Next.js/Astro: headings live in component JSX/markup, not the head - edit the page or content component. WordPress: theme templates and the block editor; ensure the theme does not wrap the site logo in an `<h1>` on inner pages. Static HTML: edit the body markup. No framework can auto-fix heading *order* - it depends on authored content structure.

# Can Astova generate the fix?
No - explain. Headings are body content tied to meaning; Astova has no deterministic generator for them. An AI-assisted restructure is possible but is a content edit, not a generated artifact.

# Can an AI coding agent safely automate this?
Sometimes. Demoting a stray second H1 to an H2 is usually safe. Reordering or re-tagging headings risks changing visible styling (CSS often keys off tag names) and document meaning, so do it carefully.

# How should an AI coding agent approach this?
Search the rendered body markup for `h1`/`<h1`, and in component frameworks grep for heading components or markdown that compiles to headings. The most likely file is the page/content component, but a duplicate H1 often comes from a shared header/logo component, so check that too. Common mistakes: changing a heading's tag and breaking CSS that targets `h1`/`h2` selectors - check the stylesheet before re-tagging; treating an SVG/logo `<h1>` as the content H1; "fixing" order by bumping every level and accidentally leaving the page with no H1. Do NOT convert headings to non-heading elements to silence `h1.multiple` - that removes the structural signal. Avoid breaking layout by preferring to add a missing H1 over re-tagging existing ones, and verify visually if styling is tag-based.

# Verification
See RB-6. Re-run: exactly one `<h1>` yields `h1.ok`; at least one H2-H6 yields `headings.structure` PASS; no level jumps yields `onpage.heading_order` PASS.

# Related Findings
title.length (page name), geo.frontload (answer placement under the H1).

# Future Improvements
Flag H1 text that duplicates the `<title>` verbatim vs. complements it; detect heading text that is non-descriptive ("Section 1").

---

# Finding ID
canonical

# Name
Canonical tag

# Summary
Checks for a single, present, absolute, self-referencing `<link rel="canonical">`, warning on absence, duplicates, an empty href, a relative URL, or a canonical that points to a different URL.

# Why this matters
See RB-1. The canonical URL tells engines which URL is the authoritative version of a page. AI answer engines consolidate signals and citations onto the canonical URL, so a wrong or cross-pointing canonical can cause the page's content to be attributed to (and cited as) a different URL, or cause this URL to be dropped as a duplicate. A missing canonical leaves duplicate/parameterised variants competing.

# How Astova detects it
See RB-2. `_canonical_check` finds all `link rel="canonical"`. None: WARN (LOW), "add a self-referencing canonical." More than one: WARN (MEDIUM), "conflicting." Empty href: WARN (LOW). If a page URL is known, it resolves the href against the page URL with `urljoin`, normalises both via `_norm_url` (scheme+lowercased host+path, dropping fragment, query, and trailing slash), and if they differ emits WARN (MEDIUM) "declares a different canonical." A self-referencing relative href is WARN (LOW, "use absolute"); a self-referencing absolute href is PASS. The `value` records present/count/self_referencing/absolute/target. VERIFIED - string comparison of parsed attributes.

# Evidence Example
Two `<link rel="canonical">` tags (evidence: "2 canonical tags - conflicting"); or `<link rel="canonical" href="/page">` on `https://site.com/page` passing only as relative (WARN "use absolute"); or a product page whose canonical points at the homepage (WARN "canonical → https://site.com/").

# How to fix it
Add exactly one `<link rel="canonical">` in `<head>` whose href is the page's own absolute `https://` URL, unless you deliberately want this page consolidated into another.

# Framework Examples
See RB-3. Next.js: `metadata.alternates.canonical` per route. Astro: a `<link rel="canonical">` in the layout head, typically `new URL(Astro.url.pathname, site)`. WordPress: SEO plugin emits canonicals automatically - prefer fixing its settings over hardcoding. Static HTML: add the absolute-URL canonical per page.

# Can Astova generate the fix?
Yes (deterministic) - Astova has a deterministic canonical generator that emits a self-referencing absolute canonical link for the scanned URL.

# Can an AI coding agent safely automate this?
Usually for adding a missing self-referencing canonical. A cross-pointing canonical is "Sometimes" - it may be intentional (intended consolidation); never flip it without confirming intent, because a wrong change can de-index a page.

# How should an AI coding agent approach this?
Search for `rel="canonical"`, `alternates.canonical`, `canonical` in metadata/layout files and SEO plugin config. The most likely file is the shared layout (a single hardcoded canonical there can wrongly point every page at one URL - a frequent bug). Common mistakes: hardcoding the homepage URL into a layout so every page self-cross-canonicalises; emitting both a plugin canonical and a manual one (duplicate); using a relative href; including the query string or trailing-slash variant so the canonical does not match the indexed URL after normalisation. Do NOT "fix" a deliberate cross-canonical (e.g. paginated or syndicated pages) without checking. Avoid breakage by deriving the canonical from the request path, not a constant.

# Verification
See RB-6. Re-run: exactly one absolute, self-referencing canonical yields PASS; `_norm_url(target) == _norm_url(page)` must hold.

# Related Findings
robots.noindex (both control indexing), onpage.hreflang (alternates).

# Future Improvements
Cross-check canonical target against actual reachability (200 vs redirect/404); detect canonical chains across crawled pages.

---

# Finding ID
robots.noindex, robots.indexable, onpage.snippet_directives

# Name
Indexability signals

# Summary
Detects a `noindex` meta robots directive (`robots.noindex` / `robots.indexable`) and reports snippet/preview directives that limit how much of the page engines may display (`onpage.snippet_directives`).

# Why this matters
See RB-1. `noindex` tells engines to exclude the page entirely - an AI answer engine will not index or cite a noindexed page, so it can never appear as a source no matter how good its content. Snippet directives (`nosnippet`, `max-snippet:0`, `max-image-preview:none`, `noimageindex`) cap how much text/image the engine may surface in an answer preview, shrinking the page's visibility in AI Overviews even when it is indexed. Conversely `max-image-preview:large` permits rich previews.

# How Astova detects it
See RB-2. For indexability: it reads `<meta name="robots">`, lowercases content, and if it contains `noindex` emits `robots.noindex` (FAIL, HIGH); otherwise `robots.indexable` (PASS). For snippets, `_snippet_directives` collects tokens from every `<meta name="robots">` and `<meta name="googlebot">`, splitting content on commas. If any token is in the restrictive set (`nosnippet`, `noimageindex`, `max-snippet:0`, `max-image-preview:none`) it WARNs (LOW) listing them; if `max-image-preview:large` is present it PASSes; otherwise INFO recommending `max-image-preview:large`. VERIFIED - directives parsed from meta tags.

# Evidence Example
`<meta name="robots" content="noindex, follow">` triggers `robots.noindex` (evidence: "noindex, follow"). `<meta name="robots" content="nosnippet">` triggers `onpage.snippet_directives` WARN (evidence: "restrictive: nosnippet"). A page with no robots meta gets the INFO suggestion to add `max-image-preview:large`.

# How to fix it
If the page should be discoverable, remove `noindex` from its robots meta (and confirm no header/CDN sets `X-Robots-Tag: noindex`). Remove restrictive snippet directives unless intentional, and add `max-image-preview:large` to allow rich previews.

# Framework Examples
See RB-3. Next.js: `metadata.robots` (`{ index: true }`) per route. Astro: the `<meta name="robots">` in the layout. WordPress: SEO plugin "search engine visibility" toggle and per-page index/noindex setting - often the cause is the site-wide "discourage search engines" checkbox. Static HTML: edit/remove the robots meta. Note: a `noindex` can also come from an HTTP `X-Robots-Tag` header, which is server/CDN config, not markup.

# Can Astova generate the fix?
Yes (deterministic) - Astova has a deterministic robots generator that can emit a correct meta robots directive (indexable + `max-image-preview:large`).

# Can an AI coding agent safely automate this?
Sometimes. `noindex` is very often intentional (staging, thank-you pages, admin, faceted duplicates). Never strip `noindex` without confirming the page is meant to be public. Removing snippet restrictions / adding `max-image-preview:large` is usually safe.

# How should an AI coding agent approach this?
Search for `noindex`, `name="robots"`, `metadata.robots`, `X-Robots-Tag`, and SEO-plugin visibility settings. Critically, also check server config, middleware, and CDN headers - a `noindex` is not always in the HTML. The most likely file is the route metadata or a global layout/middleware that blanket-applies `noindex`. Common mistakes: removing a deliberate `noindex` from non-public pages; assuming the directive is in markup when it is an `X-Robots-Tag` header; adding `index` while leaving a conflicting `noindex` token elsewhere. Do NOT touch `robots.txt` for this - that is a separate technical-pillar concern (`disallow` is not the same as `noindex`). Avoid breakage by scoping the change to the specific route, not the global default.

# Verification
See RB-6. Re-run: absence of `noindex` yields `robots.indexable` PASS; presence of `max-image-preview:large` (or no restrictive tokens) clears `onpage.snippet_directives`.

# Related Findings
canonical, technical-pillar robots.txt / AI-crawler directives.

# Future Improvements
Read the live `X-Robots-Tag` response header so header-set noindex is reported alongside the meta-set one.

---

# Finding ID
schema.jsonld, schema.missing, schema.validation

# Name
Structured data (JSON-LD)

# Summary
Reports which JSON-LD `@type`s are present (`schema.jsonld`), warns when there is no JSON-LD at all (`schema.missing`), and validates that known rich-result types carry their required properties (`schema.validation`).

# Why this matters
See RB-1. JSON-LD gives AI answer engines explicit, machine-readable facts - entity names, authors, prices, FAQ question/answer pairs, addresses - instead of asking them to infer those from prose. Engines use this to ground entities and to extract exact answers (a `FAQPage` becomes directly quotable Q&A). No structured data forces inference and weakens entity grounding; structured data that is present but missing required properties is ineligible for the rich treatment and may be ignored.

# How Astova detects it
See RB-2. `_jsonld_nodes` parses every `<script type="application/ld+json">`, JSON-decodes it (silently skipping invalid JSON), and flattens top-level lists and `@graph` containers into individual nodes. `_jsonld_types` collects `@type` values (original casing). If any types exist: `schema.jsonld` PASS listing sorted types; else `schema.missing` WARN (MEDIUM). `_schema_validation` then checks each node whose lowercased `@type` is in `SCHEMA_REQUIRED` (article→headline, product→name, faqpage→mainentity, localbusiness→name+address, event→name+startdate+location, etc.) for the presence of those lowercased keys; missing ones produce `schema.validation` WARN (MEDIUM) listing up to four problems, else PASS. It returns nothing if no JSON-LD exists or no validated type is found. VERIFIED - parsed and key-checked directly.

# Evidence Example
A page with no `<script type="application/ld+json">` triggers `schema.missing`. A `{"@type":"Product"}` node with no `name` triggers `schema.validation` (evidence: "product: missing name"). A `{"@type":"FAQPage"}` with no `mainEntity` triggers "faqpage: missing mainentity". Note malformed JSON is silently skipped, so broken JSON-LD reads as `schema.missing`.

# How to fix it
Add a valid JSON-LD `<script>` describing the page's primary entity (Organization, Article, Product, FAQPage, LocalBusiness, etc.), ensuring every required property for that type is filled. Keep the markup's facts consistent with the visible page.

# Framework Examples
See RB-3. Next.js: render a `<script type="application/ld+json" dangerouslySetInnerHTML>` with a JS object, or use the metadata route. Astro: inline a JSON-LD `<script set:html={JSON.stringify(data)}>`. WordPress: SEO/schema plugins emit JSON-LD - configure the entity fields there. Static HTML: add the script block in `<head>` or body.

# Can Astova generate the fix?
Yes (deterministic) for `schema.missing` - Astova has a deterministic schema generator (it can emit base Organization/Article/FAQ scaffolds; `geo.faq` likewise generates FAQPage JSON-LD). Filling *correct values* into a validation gap is AI assisted, since the values come from page content.

# Can an AI coding agent safely automate this?
Usually for adding a scaffold and for filling obviously-derivable required properties (e.g. `name` from the H1). Sometimes when values must be accurate and not invented - never fabricate prices, dates, or addresses to satisfy `schema.validation`.

# How should an AI coding agent approach this?
Search for `application/ld+json`, `@type`, schema plugin config, or existing structured-data helpers. The most likely file is the layout (site-wide Organization) or the page/content template (per-page Article/Product/FAQ). Common mistakes: emitting JSON-LD whose facts contradict the visible page (engines distrust mismatched markup); producing invalid JSON via unescaped quotes (the engine silently skips it, so it reads as missing - always `JSON.stringify` an object, never hand-concatenate); duplicating an entity already emitted by a plugin; lowercasing matters only to the checker, not to schema.org, so keep correct camelCase (`mainEntity`, `startDate`) in output. Do NOT invent required-property values to pass validation. Verify the script parses as JSON before committing.

# Verification
See RB-6. Re-run: a parseable JSON-LD block with `@type` clears `schema.missing` and lists types in `schema.jsonld`; required keys present clears `schema.validation`.

# Related Findings
geo.faq (FAQPage generation), local (LocalBusiness/NAP), opengraph (entity hints).

# Future Improvements
Surface invalid-JSON as a distinct finding (currently silently treated as missing); validate property *values* (URL/date formats), not just presence.

---

# Finding ID
opengraph

# Name
Open Graph & Twitter tags

# Summary
Checks completeness of social/preview meta: the core `og:title`, `og:description`, `og:image` plus `og:url`, `og:type`, and `twitter:card`.

# Why this matters
See RB-1. Open Graph and Twitter Card tags provide a curated title, description, and image that AI engines and link-unfurlers use to render a rich preview of the page. When an answer engine cites or surfaces a link, these tags control how that citation appears; missing core tags (especially `og:image`) yield a bare, less-clickable reference and remove an author-controlled summary the engine could reuse.

# How Astova detects it
See RB-2. `_social_meta` checks for `<meta property="og:title|og:description|og:image|og:url|og:type">` and `<meta name="twitter:card">`. The "core" set is `og:title` AND `og:description` AND `og:image`: PASS if all three present, else WARN (LOW) naming the missing core tags. `value` lists present/missing. VERIFIED - presence checks on the parsed DOM.

# Evidence Example
A page with only `<meta property="og:title">` and no `og:description`/`og:image` WARNs (evidence: "present: og:title"; recommendation names og:description, og:image). A page with no social tags WARNs with evidence "no social tags".

# How to fix it
Add the three core OG tags (`og:title`, `og:description`, `og:image` with an absolute image URL), and ideally `og:url`, `og:type`, and `twitter:card`. Keep `og:title`/`og:description` aligned with the page's title and description.

# Framework Examples
See RB-3. Next.js: `metadata.openGraph` and `metadata.twitter` per route (Next can also auto-generate images via `opengraph-image`). Astro: OG `<meta property>` tags in the layout head fed by props. WordPress: SEO plugin's social settings. Static HTML: add the meta tags in `<head>`.

# Can Astova generate the fix?
No - explain. There is no deterministic OG generator in the engine's listed set. The values (image especially) are content-dependent; an AI-assisted draft can reuse the title/description, but the image must be supplied.

# Can an AI coding agent safely automate this?
Usually for `og:title`/`og:description`/`og:url`/`og:type`/`twitter:card`, which can be derived from existing metadata. `og:image` is "Sometimes" - it needs a real, absolute image URL; do not point it at a placeholder.

# How should an AI coding agent approach this?
Search for `openGraph`, `og:`, `twitter:card`, or social-meta helpers in metadata/layout files. The most likely file is the shared layout (for defaults) plus per-route metadata (for page-specific title/image). Common mistakes: using a relative `og:image` URL (must be absolute for unfurlers); leaving every page with one identical OG image/title from the layout; setting `og:title` to a value that contradicts the `<title>`; forgetting `twitter:card` so Twitter falls back to a tiny preview. Do NOT duplicate tags that a framework/plugin already injects. Avoid breakage by reusing the same title/description sources as the `<title>`/meta-description fixes so the three stay consistent.

# Verification
See RB-6. Re-run: presence of `og:title`, `og:description`, and `og:image` flips `opengraph` to PASS.

# Related Findings
title.length, meta.description.length (OG mirrors these).

# Future Improvements
Validate that `og:image` resolves and meets minimum dimensions; flag OG title/description that diverge from the page's `<title>`/meta description.

---

# Finding ID
onpage.hreflang

# Name
hreflang

# Summary
When a page declares hreflang alternates, validates that the language codes are well-formed and that an `x-default` is present; emits nothing when the site uses no hreflang.

# Why this matters
See RB-1. hreflang tells engines which language/region variant of a page to serve. For AI answer engines that respond to a user in a given locale, broken or incomplete hreflang can cause the wrong-language version to be retrieved and cited, or the variants to be treated as unrelated duplicates rather than equivalents. A missing `x-default` leaves no fallback for unmatched locales.

# How Astova detects it
See RB-2. `_hreflang` collects `hreflang` values from `<link rel="alternate">`. If none, it returns nothing (no penalty for monolingual sites). Otherwise each code is matched against `^[a-z]{2,3}(-[a-z]{2,4})?$|^x-default$` (case-insensitive); non-matching codes are "invalid". It also checks whether any value is `x-default`. Any invalid codes or a missing x-default produce WARN (LOW) listing the issues; otherwise PASS. VERIFIED - regex validation of parsed attributes.

# Evidence Example
`<link rel="alternate" hreflang="en_US" href="...">` (underscore, not hyphen) is invalid (evidence: "invalid codes: en_US"). A set of valid alternates with no `x-default` entry WARNs with "no x-default".

# How to fix it
Use valid `lang` or `lang-REGION` codes (e.g. `en`, `en-GB`, `fr-CA`), one `<link rel="alternate" hreflang>` per variant, and include an `hreflang="x-default"` fallback. Make the alternates reciprocal across all variants.

# Framework Examples
See RB-3. Next.js: `metadata.alternates.languages` plus an `x-default`. Astro: render the alternate `<link>` set in the layout from a locale config. WordPress: a multilingual plugin (WPML/Polylang) usually emits hreflang - fix its config rather than hardcoding. Static HTML: add the alternate links per page.

# Can Astova generate the fix?
No - explain. hreflang requires the full set of variant URLs, which Astova does not have from a single page. No generator exists for it; an AI agent can correct code *format* but needs the site's locale map to build the set.

# Can an AI coding agent safely automate this?
Sometimes. Fixing a malformed code (`en_US`→`en-US`) or adding a missing `x-default` is safe if the variant URLs already exist. Building a fresh hreflang set requires knowing every locale URL and reciprocity, which is easy to get wrong.

# How should an AI coding agent approach this?
Search for `hreflang`, `rel="alternate"`, `alternates.languages`, or the multilingual plugin/i18n config. The most likely file is the layout or an i18n/locale config that generates the alternate links. Common mistakes: using underscores instead of hyphens; using uppercase region without the hyphen format the regex expects; omitting `x-default`; non-reciprocal alternates (variant A links B but B does not link A); pointing alternates at non-existent URLs. Do NOT add hreflang to a genuinely monolingual site - the engine intentionally does not require it. Avoid breakage by sourcing codes from the existing locale list, not by hand.

# Verification
See RB-6. Re-run: all codes match the regex and an `x-default` is present yields PASS.

# Related Findings
canonical (alternates + canonical interplay), onpage.lang.

# Future Improvements
Cross-page reciprocity check across the crawl; verify alternate URLs resolve.

---

# Finding ID
images.alt

# Name
Image alt text

# Summary
Measures the share of `<img>` elements that have an `alt` attribute (present, including the valid decorative `alt=""`), passing at >=90% coverage.

# Why this matters
See RB-1. Alt text is the only textual description of an image that an AI answer engine can read; it lets the engine understand and, where relevant, cite or describe the image, and it grounds the surrounding content. Images with no alt are invisible to text-based retrieval and to assistive technology. The check deliberately treats `alt=""` as valid (intentionally decorative) per WCAG/Lighthouse, so it does not punish decorative images.

# How Astova detects it
See RB-2. From `find_all("img")`: `has_alt` counts images where `alt is not None` (so `alt=""` counts as present); `descriptive` separately counts non-empty alts. Coverage `pct = round(100 * has_alt / total)`. PASS if `pct >= 90`, else WARN (LOW). Evidence lists up to three filenames of images missing the attribute entirely. VERIFIED - attribute presence counted directly.

# Evidence Example
Ten `<img>` where two have no `alt` attribute at all gives pct=80, WARN (evidence: "missing alt on: hero.jpg; logo.png"). Note: a present-but-empty `alt=""` does NOT fail this check.

# How to fix it
Add an `alt` attribute to every `<img>`. Use a concise description for meaningful images; use `alt=""` (empty, but present) for purely decorative ones so they are correctly skipped.

# Framework Examples
See RB-3 and RB-5. Next.js: the `<Image>`/`<img>` `alt` prop (Next requires `alt`, so missing-alt usually means raw `<img>` usage). Astro: `alt` on `<img>`/`<Image>`. WordPress: the media library "Alt text" field, surfaced in the block editor. Static HTML: add `alt` to each tag.

# Can Astova generate the fix?
No - explain. Meaningful alt text describes image content and is not in the engine's deterministic generator set. An AI agent can draft alt from filename/context, but accurate descriptions need the actual image.

# Can an AI coding agent safely automate this?
Sometimes. Adding `alt=""` to clearly-decorative images (icons, spacers, background flourishes) is safe. Writing descriptive alt for content images requires understanding the image; an agent can draft but should not assert details it cannot see.

# How should an AI coding agent approach this?
Search for `<img` and image components lacking an `alt` prop/attribute. The most likely files are page/content components and any shared media component. Common mistakes: filling every missing alt with the filename or a generic "image" (worse than empty for decorative ones, useless for content ones); marking a meaningful content image as `alt=""`; not realising a CMS-driven image needs the alt set in the CMS field, not the template. Do NOT change `src`, dimensions, or `loading` here - those belong to `onpage.images.dims`. See RB-5. Avoid breakage by only adding the attribute, never altering layout.

# Verification
See RB-6. Re-run: when >=90% of images carry an `alt` attribute (empty or not), `images.alt` PASSes.

# Related Findings
onpage.images.dims (same `<img>` set), schema.jsonld (ImageObject).

# Future Improvements
Flag low *descriptive* coverage separately (the engine already tracks `descriptive`); detect filename-as-alt anti-pattern.

---

# Finding ID
onpage.images.dims

# Name
Image dimensions & lazy-load

# Summary
Measures the share of `<img>` with explicit `width` and `height` attributes (passing at >=80%) and tracks how many use `loading="lazy"`.

# Why this matters
See RB-1. Explicit image dimensions prevent layout shift (CLS) as the page renders, which keeps the rendered DOM stable - important when a headless renderer or AI crawler captures "what the bot saw." A stable, fast-settling layout means the bot reads the final content rather than a mid-reflow snapshot, and `loading="lazy"` on below-the-fold images keeps initial delivery lean.

# How Astova detects it
See RB-2. From `find_all("img")`: `with_dims` counts images having both `width` and `height` attributes; `with_lazy` counts `loading="lazy"`. `pct_dims = round(100 * with_dims / total)`. PASS if `pct_dims >= 80`, else WARN (LOW), recommending explicit width/height and lazy-loading for below-the-fold images. VERIFIED - attribute presence counted directly.

# Evidence Example
Ten images where only five declare `width` and `height` gives pct_dims=50, WARN ("5 image(s) lack explicit width/height ... add them, and loading=\"lazy\" for below-the-fold images").

# How to fix it
Add intrinsic `width` and `height` attributes to each `<img>` matching the image's real aspect ratio, and add `loading="lazy"` to images that start below the fold (but not to the LCP/hero image).

# Framework Examples
See RB-3. Next.js: `<Image>` requires/derives `width`/`height` and lazy-loads by default - converting raw `<img>` to `<Image>` fixes both. Astro: `<Image>` with `width`/`height`, or add the attributes to raw `<img>`. WordPress: core normally adds dimensions and lazy-loading automatically; missing ones usually come from hand-written template `<img>`. Static HTML: add the attributes per tag.

# Can Astova generate the fix?
No - explain. Correct dimensions are the image's real pixel size, which Astova does not have for an arbitrary source. Not in the deterministic generator set. An agent can read the file's intrinsic size if it has filesystem access, but the engine does not generate this.

# Can an AI coding agent safely automate this?
Sometimes. Adding `loading="lazy"` to clearly below-the-fold images is low-risk. Adding `width`/`height` requires the true intrinsic dimensions; wrong values distort the image, so derive them from the asset, not guesses.

# How should an AI coding agent approach this?
Search for `<img` tags missing `width`/`height`, and consider whether the framework's image component should be used instead. The most likely files are content/page components and shared media components. To get real dimensions, read the asset file's pixel size (if local) rather than guessing. Common mistakes: setting `width`/`height` to CSS-display sizes that do not match the file's aspect ratio (causes distortion); adding `loading="lazy"` to the hero/LCP image (delays the most important paint); breaking responsive CSS that assumes no inline dimensions. Do NOT change `alt` here (that is `images.alt`). Avoid breakage by preferring the aspect-ratio-correct intrinsic size and testing the hero image is not lazy-loaded.

# Verification
See RB-6. Re-run: when >=80% of images carry both `width` and `height`, `onpage.images.dims` PASSes.

# Related Findings
images.alt (same image set), performance pillar (CWV/CLS).

# Future Improvements
Distinguish above- vs below-the-fold to correctly score lazy-loading and warn on a lazy-loaded LCP image.

---

# Finding ID
onpage.links, onpage.outbound, onpage.link_attrs, onpage.crawlable_anchors, onpage.jump_links

# Name
Links & anchors

# Summary
Covers anchor-text quality (`onpage.links`), presence of outbound source links (`onpage.outbound`), `rel`/`target` hygiene on external links (`onpage.link_attrs`), JavaScript-only uncrawlable links (`onpage.crawlable_anchors`), and whether in-page jump links resolve to real ids (`onpage.jump_links`).

# Why this matters
See RB-1. Descriptive anchor text tells an AI engine what a linked page is about, strengthening the link as a relationship signal. Outbound links to authoritative sources are a trust/citation signal. Links that navigate only via JavaScript cannot be followed by crawlers or AI bots, so those destinations are invisible to retrieval. In-page jump links that resolve to real ids make sections deep-linkable, so an engine can cite a specific section. `rel`/`target` hygiene (`noopener` on `target="_blank"`) is a security and link-quality concern.

# How Astova detects it
See RB-2. `_link_stats` classifies each `<a href>` as internal (same host or relative) or external, skipping `#`/`mailto:`/`tel:`/`javascript:`. An anchor is "generic" if its normalised text is in `GENERIC_ANCHORS` ("click here", "read more", etc.), is a bare URL, or is empty with no aria-label/title. `onpage.links` PASSes when `generic/total <= 0.10` (ratio-based, not a fixed count), else WARN (MEDIUM). `onpage.outbound` PASSes when `external >= 1`, else INFO. `_link_attrs` looks only at external links; it WARNs (LOW) when any `target="_blank"` link lacks both `noopener` and `noreferrer` in `rel`; returns nothing if there are no external links. `_crawlable_anchors` WARNs (MEDIUM) on `href="javascript:..."` or an `onclick` with empty/`#` href. `onpage.jump_links` collects `#fragment` links and PASSes when at least one resolves to an element with that `id`, else INFO. All VERIFIED - derived from parsed anchors.

# Evidence Example
Many "click here"/"read more" anchors exceeding 10% of links WARN `onpage.links` (evidence lists up to three). `<a target="_blank" href="https://x.com">` with no `rel` WARNs `onpage.link_attrs`. `<a href="javascript:void(0)" onclick="go()">` WARNs `onpage.crawlable_anchors`. A `<a href="#pricing">` with no element `id="pricing"` leaves `onpage.jump_links` INFO ("0 of 1 ... resolve").

# How to fix it
Replace generic/bare-URL anchor text with descriptive phrases. Link out to authoritative sources where relevant. Add `rel="noopener"` to `target="_blank"` links (and `sponsored`/`ugc` where applicable). Use real `<a href="…">` URLs instead of JavaScript-only navigation. Ensure every `#anchor` link has a matching element `id`.

# Framework Examples
See RB-3 and RB-5. Next.js: use `<Link href>`/`<a href>` with descriptive children; avoid `onClick`-only navigation. Astro/Static HTML: edit the anchor markup and add ids to target sections. WordPress: edit link text and headings/anchors in the block editor; jump-link ids come from block "HTML anchor" fields.

# Can Astova generate the fix?
No - explain. None of these are in the deterministic generator set. Adding `rel="noopener"` and fixing jump-link ids are mechanical and AI-automatable, but anchor-text rewrites and choosing outbound sources are content judgements (AI assisted at most).

# Can an AI coding agent safely automate this?
Sometimes. Adding `rel="noopener"` to `_blank` links and converting `javascript:` links to real hrefs (when the URL is known) are usually safe. Rewriting anchor text and adding outbound citations are content edits; jump-link fixes are safe only when you know which heading the link targets.

# How should an AI coding agent approach this?
Search for anchor markup: `target="_blank"`, `javascript:`, `onclick=` on anchors, `href="#`, and generic phrases like "click here"/"read more". The most likely files are content/page components and shared nav/footer components. For `onpage.link_attrs`, simply add `rel="noopener"` (preserving any existing rel). For `onpage.crawlable_anchors`, only convert to a real `href` if the destination URL genuinely exists - do not invent one; if navigation is truly app-internal, a real route href is correct. For `onpage.jump_links`, add the missing `id` to the target heading/section, matching the fragment exactly. Common mistakes: stripping an existing `rel` (e.g. `nofollow`) when adding `noopener` - append, do not overwrite; removing `onclick` handlers that do real work while "fixing" crawlability; adding an `id` that duplicates an existing one. Do NOT mass-rewrite anchor text into keyword-stuffed phrases. Avoid breakage by preserving event handlers and existing rel tokens.

# Verification
See RB-6. Re-run: generic ratio <=0.10 PASSes `onpage.links`; >=1 external link PASSes `onpage.outbound`; no unsafe `_blank` PASSes `onpage.link_attrs`; no `javascript:`/`onclick`-only anchors PASSes `onpage.crawlable_anchors`; >=1 resolving fragment PASSes `onpage.jump_links`.

# Related Findings
onpage.heading_order (jump-link targets are headings), technical pillar (crawlability).

# Future Improvements
Detect broken internal links (404 targets); score outbound-link authority; flag `nofollow` on internal links.

---

# Finding ID
onpage.lang

# Name
Page language

# Summary
Checks that the root `<html>` element carries a `lang` attribute.

# Why this matters
See RB-1. The `<html lang>` attribute states the page's language unambiguously. AI answer engines use it to confirm the language of the content (rather than guessing from the text) when matching a query's locale and when deciding which language results to surface; it also drives assistive-technology pronunciation. A missing `lang` leaves the language to inference.

# How Astova detects it
See RB-2. It finds the `<html>` tag and checks for a non-empty `lang` attribute. PASS with the value recorded if present, else WARN (LOW) recommending `<html lang="…">`. VERIFIED - single attribute read.

# Evidence Example
`<html>` with no `lang` attribute WARNs. `<html lang="en">` PASSes with value "en".

# How to fix it
Set a valid language (or language-region) code on the root element, e.g. `<html lang="en">` or `<html lang="en-GB">`.

# Framework Examples
See RB-4. Next.js: the `<html lang>` on the root in `app/layout.tsx`. Astro: `<html lang>` in the base layout. WordPress: the theme's `language_attributes()` in `header.php` (usually already correct from the site language setting). Static HTML: set `lang` on the `<html>` tag in every page.

# Can Astova generate the fix?
No - explain. The engine has no `lang` generator in its set. It is a one-attribute edit an AI agent can apply, but the correct value depends on the site's actual language.

# Can an AI coding agent safely automate this?
Usually. Adding `lang="en"` (or the site's known language) to the root element is a safe, isolated change - provided the language is known and correct.

# How should an AI coding agent approach this?
Search for the root `<html` tag - in app frameworks this is in the single root layout, not per page. The most likely file is `app/layout.tsx` (Next), the base layout (Astro), or `header.php` (WordPress). Common mistakes: setting the wrong language; setting it per-component instead of on the one root element; hardcoding `en` on a multilingual site where it should be dynamic per locale. Do NOT confuse this with `hreflang` (alternates) - this is the single document language. Avoid breakage by editing only the root element's attribute.

# Verification
See RB-6. Re-run: a non-empty `lang` on `<html>` flips `onpage.lang` to PASS.

# Related Findings
onpage.hreflang (per-variant language), onpage.form_labels (accessibility group).

# Future Improvements
Validate the `lang` value against BCP-47; cross-check it against detected content language.

---

# Finding ID
onpage.form_labels

# Name
Form control labels

# Summary
Checks that every visible form control (`input`/`select`/`textarea`, excluding hidden/submit/button/reset/image) has an accessible label.

# Why this matters
See RB-1. Labeled form controls give an AI engine (and assistive technology) the semantic meaning of each field, which helps it understand interactive content - what a form collects and how to describe or act on it. Unlabeled controls are opaque inputs with no programmatic name, weakening both accessibility and the engine's comprehension of the page.

# How Astova detects it
See RB-2. It selects `input`/`select`/`textarea` whose `type` is not in (hidden, submit, button, reset, image). `_is_labeled` returns true if the control has `aria-label`, `aria-labelledby`, or `title`; or an `id` matched by a `<label for=...>`; or is wrapped in a `<label>`. PASS when no controls are unlabeled, else WARN (LOW) with the unlabeled count. VERIFIED - structural label-association check.

# Evidence Example
`<input type="text" name="email">` with no associated `<label>`, `aria-label`, or wrapping label WARNs (evidence: "1 form control(s) lack a label").

# How to fix it
Associate every input with a label: a `<label for="id">` matching the control's `id`, an `aria-label`, an `aria-labelledby`, or wrap the control in a `<label>`.

# Framework Examples
See RB-3 and RB-5. Next.js/Astro: add `<label htmlFor>`/`<label for>` matching the input `id`, or an `aria-label`, in the form component. WordPress: form-builder plugins usually emit labels - missing ones come from hand-coded template forms. Static HTML: add labels in the markup.

# Can Astova generate the fix?
No - explain. Not in the deterministic generator set. The label *text* must describe the field's purpose, which is a content judgement (AI assisted at most).

# Can an AI coding agent safely automate this?
Sometimes. Adding a label is safe mechanically, but the label text must accurately name the field, and a wrong `for`/`id` pairing silently fails. Visually-hidden labels may be the design intent, so prefer `aria-label` or a visually-hidden `<label>` to avoid altering layout.

# How should an AI coding agent approach this?
Search for `<input`, `<select`, `<textarea>` and check for an associated label, `aria-label`, or wrapping. The most likely files are form components and shared search/newsletter widgets. Common mistakes: adding a `<label for="x">` whose `for` does not match the control's `id` (no association, still fails and confuses screen readers); using placeholder text as a substitute for a label (the engine does not count `placeholder`); inserting a visible label that breaks a deliberately label-free design - use `aria-label` or a visually-hidden label instead. Do NOT relabel submit/buttons (they are excluded). Avoid breakage by matching `id`/`for` exactly and not disturbing layout.

# Verification
See RB-6. Re-run: when every non-excluded control is labeled, `onpage.form_labels` PASSes.

# Related Findings
onpage.lang (accessibility group), images.alt.

# Future Improvements
Flag placeholder-as-label anti-pattern; check that label text is non-empty and meaningful.

---

# Finding ID
onpage.url

# Name
URL structure

# Summary
Flags URL paths that are hard to read or noisy: uppercase letters, underscores, deep nesting (>4 segments), a query string, or total length over 100 characters; passes when at most one issue is present.

# Why this matters
See RB-1. Clean, descriptive URLs act as a compact topic signal an AI engine reads when assessing and citing a page; a readable path reinforces what the page is about. Noisy URLs (query junk, deep nesting, mixed case) are harder to interpret, more prone to duplicate variants, and look less trustworthy when surfaced as a citation.

# How Astova detects it
See RB-2. `_url_quality` parses the URL and collects issues: any uppercase in the path; an underscore; more than four non-empty path segments; a non-empty query string; total URL length over 100. PASS if `len(issues) <= 1`, else WARN (LOW) listing the issues. VERIFIED - computed from the parsed URL string.

# Evidence Example
`https://site.com/Blog/2024/My_Post?ref=twitter&utm=x` collects uppercase, underscore, and query-string issues and WARNs (evidence: the full URL).

# How to fix it
Prefer short, lowercase, hyphenated paths with shallow depth and no tracking query parameters in the canonical URL. Keep total length reasonable (under ~100 chars).

# Framework Examples
See RB-4. Next.js: URLs come from the `app/` route folder structure - rename route segments/files (lowercase, hyphenated) and add redirects. Astro: the `src/pages/` file path defines the URL - rename files/folders and add redirects. WordPress: the permalink structure and the page/post slug field. Static HTML: the file/folder path and any server rewrite rules.

# Can Astova generate the fix?
No - explain. Changing a URL is a routing/structural change with redirect implications; it is not in the deterministic generator set and is not safe to auto-emit.

# Can an AI coding agent safely automate this?
Never (without explicit human sign-off and redirects). Renaming a live URL changes its address: it breaks inbound links, loses accrued authority, and 404s the old path unless a redirect is added. This is the highest-risk on-page finding to automate.

# How should an AI coding agent approach this?
Treat this as advisory. Search the routing structure (`app/` folders in Next, `src/pages/` in Astro, permalink/slug in WordPress, file paths + rewrites in static) to understand how the URL is derived. The most likely files are route directories/files, not a metadata tag. If a change is sanctioned, the critical companion work is a 301 redirect from the old URL to the new one and updating every internal link to it. Common mistakes: renaming a route without adding a redirect (instant 404s and lost citations); changing only the displayed link while the actual route stays noisy; stripping a query parameter the app depends on for functionality. Do NOT silently rename URLs - propose them and require sign-off. Most "issues" here (a single query param, slight length) are tolerable; the PASS threshold already allows one.

# Verification
See RB-6. Re-run against the new URL: `onpage.url` PASSes when at most one issue remains. Also confirm the old URL 301-redirects and internal links are updated (outside the on-page check).

# Related Findings
canonical (which URL is authoritative), technical pillar (redirects/status).

# Future Improvements
Detect tracking-only query params separately from functional ones; check old-URL redirect status as part of the fix verification.

---

I read the full on-page module (`/Users/joshuawalsh/Desktop/Sites/damask/engine/astova_engine/modules/onpage.py`) and wrote 16 Knowledge Cards, one per requested family, all grounded in the actual detection logic.

Key accuracy points captured from the code:
- Exact thresholds: title 15-60, meta description 80-160, images alt >=90%, image dims >=80%, generic-anchor ratio <=0.10, URL "at most one issue" / >4 path segments / >100 chars.
- Real finding ids and statuses/severities (e.g. `title.missing` is FAIL/CRITICAL, `h1.missing` FAIL/HIGH, `robots.noindex` FAIL/HIGH, most warns LOW/MEDIUM).
- Subtle behaviours worth flagging to fixers: `alt=""` counts as present (decorative-valid); malformed JSON-LD is silently skipped so it reads as `schema.missing`; canonical comparison uses `_norm_url` (drops query/fragment/trailing slash); snippet directives read both `robots` and `googlebot` metas; `_schema_validation`/`_hreflang`/`_link_attrs`/`_crawlable_anchors` return nothing when not applicable (no false penalties).
- Generator capability mapped to the real engine: deterministic generators exist for `title.missing`, `meta.description.missing`, `canonical`, `schema.missing` (and `geo.faq`, robots); everything else marked "No" or "AI assisted" accordingly. `onpage.url` flagged as the highest-risk ("Never" auto-automate) because of redirect/link-breakage.

All cards use the verbatim heading structure in order, reference RB-1 through RB-6 by name rather than rewriting them, talk about AI answer engines rather than SEO, and use plain hyphens. Cards are separated by `---`. No new findings were invented and no patches were written beyond illustrative framework snippets.agentId: a6470aafd56f42efa (use SendMessage with to: 'a6470aafd56f42efa' to continue this agent)
<usage>subagent_tokens: 49762
tool_uses: 1
duration_ms: 252496</usage>

## Technical findings

---

# tech.https
# Name
HTTPS

# Summary
The page must be served over HTTPS. This is the single most foundational technical check: a non-HTTPS page is flagged CRITICAL.

# Why this matters
See RB-1: How AI answer engines read pages. AI crawlers (GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot) and the indexes that feed answer engines deprioritize or skip insecure origins. An `http://` page is treated as lower-trust source material; many fetch pipelines will not cite content served without TLS. HTTPS is also a precondition for HSTS, clean mixed-content state, and modern HTTP features that affect how fast and reliably a bot can read the page.

# How Astova detects it
The module parses the final (post-redirect) URL and checks `urlparse(final_url).scheme == "https"`. If true: `Status.PASS`; if false: `Status.FAIL` at `Severity.CRITICAL` with recommendation "Serve the site over HTTPS." This is read directly from the resolved URL scheme, so it reproduces exactly on re-run. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=False` on a page whose final URL resolves to `http://example.com/`.

# How to fix it
This is an infrastructure fix, not a code change. Obtain a TLS certificate (Let's Encrypt is free and automatable) and configure the web server, load balancer, or CDN to serve the site over HTTPS. Then redirect all `http://` traffic to `https://` at the server/edge so the canonical scheme is always secure.

# Framework Examples
This is server, hosting, or CDN configuration, not application code. Next.js / Astro / WordPress / Static HTML cannot enable HTTPS themselves. On managed hosts (Vercel, Netlify, Cloudflare Pages) HTTPS is provisioned automatically by the platform; on self-hosted nginx/Apache it requires a certificate and listener config. No framework file fixes this.

# Can Astova generate the fix?
No - HTTPS is infrastructure (certificate provisioning plus server/edge config). There is no deterministic code generator for it.

# Can an AI coding agent safely automate this?
Never. Enabling TLS touches certificate issuance, DNS validation, and server/CDN listeners. An agent editing the repo cannot provision a certificate or reconfigure a load balancer, and a wrong move can take the whole site offline.

# How should an AI coding agent approach this?
Do not attempt a code patch. Diagnose and report: confirm whether the hosting platform already supports HTTPS (check for `vercel.json`, `netlify.toml`, Cloudflare config, or a reverse-proxy config like `nginx.conf` / `.htaccess`). If the app is on a managed host, the fix is usually "enable HTTPS / force HTTPS" in the dashboard, not in code. If self-hosted, the operator needs to install a certificate and add an HTTP-to-HTTPS redirect at the server. The agent's correct output is a clear hand-off note naming the likely place (host dashboard vs server config) and the steps, never a speculative edit to application files. Do NOT hardcode `https://` rewrites in app routing as a substitute for real TLS.

# Verification
See RB-6: Verification model. Re-scan: the finding clears only when the final resolved URL scheme is `https`.

# Related Findings
tech.hsts, tech.tls, tech.mixed_content, tech.redirect (http→https hop).

# Future Improvements
Detect TLS protocol version and cipher strength; flag HTTPS that downgrades or serves an incomplete chain.

---

# tech.status
# Name
HTTP status

# Summary
The page must return a 2xx success status. Anything outside 200-299 is a FAIL.

# Why this matters
See RB-1: How AI answer engines read pages. A bot can only extract and cite content it actually receives. A 4xx or 5xx means there is no usable page body for an answer engine to read, so the URL contributes nothing to AI visibility and may be dropped from the index entirely. A page that 404s or 500s under a crawler's request is invisible regardless of how good its content is.

# How Astova detects it
If a `status_code` is present, the module computes `ok = 200 <= status_code < 300`. PASS when in range; otherwise `Status.FAIL` at `Severity.HIGH`. The raw status code is stored in `value`. It is read straight from the HTTP response, so it is VERIFIED. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=503` (FAIL) or `value=200` (PASS).

# How to fix it
Depends on the code: 404 means the URL no longer maps to content (fix routing or restore the page or redirect it); 5xx means the server or application errored (fix the failing handler, dependency, or capacity issue); 401/403 means access is gated (open it to crawlers if the page should be public).

# Framework Examples
The cause spans application code and infrastructure. In Next.js / Astro a 404 may be a missing route or a thrown error in a page handler; a 500 is an unhandled exception in server code. In WordPress a 5xx is often a PHP fatal or database connection failure. For Static HTML a 404 is simply a missing file. The fix is wherever the request actually fails, so it is not a single mechanical change.

# Can Astova generate the fix?
No - the root cause (routing, a crashing handler, server capacity) is specific to the app and infrastructure, not a deterministic patch.

# Can an AI coding agent safely automate this?
Sometimes. A clear, reproducible application 404/500 (a broken route, a typo'd path, an unhandled exception with a stack trace) can be safely fixed in code after diagnosis. Status codes caused by server capacity, auth gateways, or upstream services are infrastructure and the agent should not guess at them.

# How should an AI coding agent approach this?
First determine whether the failure is in application code or infrastructure. Reproduce the request locally and read the actual error. For a 404, search the router (Next.js `app/`/`pages/`, Astro `src/pages/`, WP rewrite rules) for the missing path and decide between restoring content and adding a redirect. For a 500, find the throwing handler from the stack trace and fix it; do not swallow the error silently. Do NOT mask a real error by returning a hardcoded 200 with empty content, and do NOT add a blanket catch-all route that hides other broken URLs. If the status is environmental (timeouts, gateway, scaling), hand off with the evidence rather than patching.

# Verification
See RB-6: Verification model. Re-scan and confirm the URL returns 200-299.

# Related Findings
tech.redirect / tech.redirect.chain (3xx responses), tech.x_robots_tag, tech.index_conflict.

# Future Improvements
Distinguish soft-404s (200 status with not-found body) and report per-status-class guidance.

---

# tech.redirect
# Name
Redirect (single/short)

# Summary
The page was reached through a redirect of 1-2 hops. This is INFO, not a failure; it just notes the page is not served at its final URL directly.

# Why this matters
See RB-1: How AI answer engines read pages. Crawlers follow redirects but every hop is latency and a chance to drop the request. One or two hops (for example `http`→`https` or apex→`www`) is normal and harmless. The signal matters mainly so that internal links and any canonical or cited URL point at the final destination, so the engine indexes the resolved page rather than a chain of redirectors.

# How Astova detects it
`_redirect_checks(chain)` runs only when a `redirect_chain` (list of `(status_code, url)`) was captured. With `hops = len(chain)` and `hops <= 2`, it emits `tech.redirect` as `Status.INFO`. The full chain is recorded in `evidence` as `"<code> <url> → …"`. VERIFIED from the observed response chain. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=1`, evidence `301 http://example.com/ → 200 https://example.com/`.

# How to fix it
Nothing to fix at the server level for 1-2 hops. The only action is to update internal links (and any externally shared or canonical URL) to point straight at the final URL so future requests skip the hop.

# Framework Examples
Not a redirect-config fix; it is a content/link-hygiene action. In any framework, search the codebase and content for links to the pre-redirect URL and update them to the final URL. See RB-5: Safe content editing. The redirect rule itself (for example forcing `https` or `www`) should usually stay in place.

# Can Astova generate the fix?
No - the redirect itself is intended infrastructure; the remaining action (relinking to the final URL) is content-specific and not a deterministic patch.

# Can an AI coding agent safely automate this?
Sometimes. Rewriting internal links to the canonical final URL is a safe, mechanical content edit. Do not remove the redirect rule itself, since http→https and apex→www redirects are deliberate.

# How should an AI coding agent approach this?
Treat this as link hygiene, not redirect surgery. Grep the repo and content for the source URL form and replace with the final URL. Leave server redirect rules untouched. Do NOT collapse a deliberate canonicalization redirect (http→https, www normalization) just to remove a hop.

# Verification
See RB-6: Verification model. After relinking, the page is reached with zero hops from internal navigation; the redirect rule may still exist for external traffic.

# Related Findings
tech.redirect.chain (the >2-hop warning variant), tech.https, tech.status.

# Future Improvements
Flag temporary (302/307) redirects used where a permanent (301/308) is intended.

---

# tech.redirect.chain
# Name
Redirect chain (long)

# Summary
The page was reached through more than 2 redirect hops. This is a WARN: long chains cost crawl time and risk being abandoned.

# Why this matters
See RB-1: How AI answer engines read pages. Each redirect is a round trip. AI crawlers cap how much work they spend per URL; a chain of 3+ hops increases the odds the bot times out or stops before it reaches the real content, so the page may never be read or cited. Long chains often hide accidental redirect-on-redirect loops introduced by stacked rules (http→https→www→trailing-slash).

# How Astova detects it
In `_redirect_checks`, when `hops > 2` it emits `tech.redirect.chain` as `Status.WARN` (`Severity.LOW`), with `value=hops` and the full path in `evidence`. The threshold is strictly greater than 2. VERIFIED from the observed chain. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=4`, evidence `301 http://x.com/ → 301 https://x.com/ → 301 https://www.x.com/ → 200 https://www.x.com/home`.

# How to fix it
Collapse the chain so the first request lands on the final URL in at most one hop. Identify the redundant intermediate rules and replace them with a single direct redirect from the original URL to the final destination.

# Framework Examples
Redirect rules live in host or server config. Next.js: the `redirects()` array in `next.config.mjs`, or `vercel.json` `redirects`. Astro: the host's redirect config (Netlify `_redirects`, Vercel `vercel.json`) since Astro has no built-in redirect engine for static output. WordPress: a redirect plugin's rule table or `.htaccess`. Static HTML / nginx: consolidate the `location`/rewrite rules so one rule maps source to final. The fix is editing redirect rules, which an agent can do carefully.

# Can Astova generate the fix?
No - the correct collapsed target depends on the site's canonical-URL policy (which intermediate hops are intended), so it is not a deterministic generator.

# Can an AI coding agent safely automate this?
Sometimes. Merging an obvious A→B→C chain into A→C is safe when the final URL is unambiguous. It is risky when multiple rules interact (case, locale, trailing slash) because collapsing the wrong one can break other paths or create a loop.

# How should an AI coding agent approach this?
Read the full chain from the finding evidence first. Map every hop to the rule that produced it (search `next.config.mjs`, `vercel.json`, `netlify.toml`/`_redirects`, `.htaccess`, or `nginx.conf`). Replace the multi-step chain with one direct rule to the final URL, keeping the original entry URL as the source. Test that no other path depended on an intermediate. Do NOT delete canonicalization redirects (http→https, apex→www) outright, just chain them so they resolve in one hop. Watch for redirect loops, the most common mistake when consolidating.

# Verification
See RB-6: Verification model. Re-scan and confirm `hops <= 1` from the original URL.

# Related Findings
tech.redirect, tech.https, tech.status.

# Future Improvements
Detect redirect loops explicitly and identify which rule introduces each hop.

---

# tech.hsts
# Name
HSTS header

# Summary
On an HTTPS page, the response should carry a `Strict-Transport-Security` header. Missing it is a WARN.

# Why this matters
See RB-1: How AI answer engines read pages. HSTS tells clients to always use HTTPS for the origin, eliminating the initial insecure request and the http→https redirect hop on repeat visits. For AI crawlers this means fewer round trips and a consistently secure, higher-trust origin. Its absence is low-severity, since HTTPS still works, but enabling it removes a hop and hardens the origin's trust profile.

# How Astova detects it
Only runs when the page is HTTPS. It checks `"strict-transport-security" in headers`. PASS if present, else `Status.WARN` at `Severity.LOW` with recommendation "Add a Strict-Transport-Security header." Read directly from response headers, so VERIFIED. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=False` when an HTTPS response has no `Strict-Transport-Security` header.

# How to fix it
Send a `Strict-Transport-Security` response header on HTTPS responses, for example `max-age=31536000; includeSubDomains`. Set this at the server, edge, or in the framework's header config. Roll out a long `max-age` only once you are confident every subdomain is HTTPS, and consider `preload` only when fully committed.

# Framework Examples
See RB-3: Framework head injection patterns (note: HSTS is an HTTP response header, not a `<head>` tag, so it must be set at the response layer, not in HTML). Next.js: a `headers()` entry in `next.config.mjs`, or `vercel.json` `headers`. Astro: the host's header config (`netlify.toml`, `vercel.json`) since it is response-level. WordPress: server config or a security plugin. Static HTML / nginx: `add_header Strict-Transport-Security` in the server block; Apache: a `Header set` directive in `.htaccess`. Cannot be set from an HTML file.

# Can Astova generate the fix?
No - HSTS is a response-header configuration that depends on the host/server, and a too-aggressive `max-age`/`includeSubDomains`/`preload` can lock out non-HTTPS subdomains, so Astova does not auto-generate it.

# Can an AI coding agent safely automate this?
Sometimes. Adding a conservative HSTS header is mechanical, but `includeSubDomains` and especially `preload` are effectively irreversible for the cache lifetime and can break any subdomain still served over HTTP. The agent must confirm all subdomains are HTTPS first.

# How should an AI coding agent approach this?
Locate the response-header config (`next.config.mjs` `headers()`, `vercel.json`, `netlify.toml`, `nginx.conf`, `.htaccess`). Add `Strict-Transport-Security` with a modest `max-age` initially. Do NOT add `includeSubDomains` or `preload` without explicit confirmation that every subdomain is HTTPS, because a wrong setting locks browsers out of insecure subdomains for the full `max-age`. Never put HSTS in a `<meta>` tag; it only works as a real HTTP header.

# Verification
See RB-6: Verification model. Re-scan and confirm the header is present on the HTTPS response.

# Related Findings
tech.https (prerequisite), tech.security_headers, tech.tls.

# Future Improvements
Parse `max-age`, `includeSubDomains`, and `preload` and warn on a too-short `max-age`.

---

# tech.tls
# Name
TLS certificate

# Summary
The TLS certificate must be valid and not near expiry. Expired is CRITICAL; expiring within 14 days is a HIGH warning.

# Why this matters
See RB-1: How AI answer engines read pages. An expired or invalid certificate causes secure clients, including AI crawler fetch pipelines, to refuse the connection outright. The page becomes completely unreachable to bots, so it cannot be read or cited, and the failure is abrupt rather than gradual. Catching an impending expiry prevents a future total outage.

# How Astova detects it
`_tls_check(tls)` runs when TLS info was gathered. It reads `days_remaining`. If not an int, PASS (INFO). If `days < 0`: `Status.FAIL`, `Severity.CRITICAL`, evidence "expired N day(s) ago". If `days <= CERT_EXPIRY_WARN_DAYS` (14): `Status.WARN`, `Severity.HIGH`, evidence "expires in N day(s)". Otherwise PASS with "valid for N more day(s)". Read from the live certificate, so VERIFIED. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=-3`, evidence `expired 3 day(s) ago (2026-06-26T00:00:00)`; or `value=9`, evidence `expires in 9 day(s) (...)`.

# How to fix it
Renew or reissue the certificate before it expires and ensure auto-renewal is configured so it never lapses again. If the certificate is valid but presented with a broken chain, fix the intermediate-certificate chain on the server.

# Framework Examples
Certificate lifecycle is infrastructure, not application code. Next.js / Astro / WordPress / Static HTML do not manage TLS certificates. On managed hosts (Vercel, Netlify, Cloudflare) renewal is automatic and a failure means a domain-verification or DNS problem to fix in the dashboard. On self-hosted servers, certbot/ACME auto-renewal or a manual reissue is the fix. No framework file addresses this.

# Can Astova generate the fix?
No - certificate issuance and renewal are infrastructure (ACME, DNS validation, server config), not generable code.

# Can an AI coding agent safely automate this?
Never. The agent cannot issue or install certificates, and certificate operations touch DNS validation and the live server. A mistake takes the site fully offline for all clients.

# How should an AI coding agent approach this?
Do not patch the repo. Report the exact expiry status from the evidence and the likely owner of the fix: managed-host dashboard (domain/DNS verification) or server-side ACME renewal (e.g. certbot timer not running). Check for any ACME/renewal config in the repo or infra files and note if auto-renewal appears misconfigured, but treat the actual renewal as an operator task. Do NOT attempt to commit certificate files or private keys.

# Verification
See RB-6: Verification model. Re-scan and confirm `days_remaining` is comfortably positive.

# Related Findings
tech.https (prerequisite), tech.hsts, tech.mixed_content.

# Future Improvements
Report issuer, chain completeness, and certificate type; warn earlier on short-lived certs.

---

# tech.mixed_content
# Name
Mixed content (insecure sub-resources)

# Summary
An HTTPS page is loading one or more sub-resources over `http://`. This is a FAIL.

# Why this matters
See RB-1: How AI answer engines read pages. Browsers block or downgrade insecure sub-resources on a secure page, so images, scripts, or stylesheets may fail to load, breaking the rendered page a crawler or headless renderer sees. A bot reading the rendered DOM gets a degraded, partially-broken page, which weakens both extractability and the origin's trust signal.

# How Astova detects it
`_mixed_content(soup)` runs only on HTTPS pages. It collects resource-loading URLs that start with `http://`: any element with a `src` (img, script, iframe, audio, video, source), `<link rel="stylesheet" href>`, and `<object data>`. Navigational `<a href>` and `link rel=canonical/alternate` are deliberately excluded, since they are not mixed content. If any are found: `tech.mixed_content`, `Status.FAIL`, `Severity.MEDIUM`, `value=count`, `evidence=first insecure URL`. VERIFIED by parsing the DOM. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=2`, evidence `http://cdn.example.com/banner.jpg`.

# How to fix it
Change each insecure sub-resource URL to `https://` (or to a protocol-relative/relative path) wherever it is referenced. Confirm the resource is actually available over HTTPS first; if a third-party host has no HTTPS endpoint, self-host the asset or replace it.

# Framework Examples
See RB-5: Safe content editing. The fix is editing the asset URLs in templates, components, content, or config. Next.js: image/script/link `src`/`href` in components and `next.config` image domains. Astro: component and layout markup. WordPress: hardcoded `http://` URLs in posts, theme files, or the database (a search-replace of `http://yourdomain` → `https://yourdomain`), plus the site/home URL settings. Static HTML: the `src`/`href` attributes in the markup. All framework-agnostic content edits.

# Can Astova generate the fix?
No - rewriting third-party and content asset URLs to HTTPS is content-dependent (the agent must verify each host serves HTTPS), so it is not a deterministic generator.

# Can an AI coding agent safely automate this?
Usually. Switching same-host or known-HTTPS asset URLs to `https://` is safe and mechanical. It is only risky when a third-party host genuinely lacks an HTTPS endpoint, in which case blindly rewriting the URL breaks the resource.

# How should an AI coding agent approach this?
Start from the evidence URL, then grep the codebase and content for `http://` in resource-loading attributes (`src=`, stylesheet `href=`, `<object data=`). Rewrite to `https://` where the host supports it; prefer protocol-relative or relative paths for same-origin assets. Verify each external host actually serves HTTPS before rewriting. For WordPress, also fix URLs stored in the database and the site/home URL options, not just theme files. Do NOT touch `<a href>` links or canonical/alternate tags; those are not mixed content and the engine intentionally ignores them.

# Verification
See RB-6: Verification model. Re-scan; mixed content clears and the finding flips to tech.mixed_content.ok.

# Related Findings
tech.mixed_content.ok (the clean state), tech.https, tech.security_headers (a CSP `upgrade-insecure-requests` can mitigate).

# Future Improvements
List all insecure URLs (not just the first) and detect protocol-relative URLs on http-origin pages.

---

# tech.mixed_content.ok
# Name
Mixed content (clean)

# Summary
The HTTPS page loads no insecure sub-resources. This is the PASS state of the mixed-content check.

# Why this matters
See RB-1: How AI answer engines read pages. A fully-secure resource graph means a headless renderer or crawler loads every image, script, and stylesheet without browser blocking, so the rendered page the bot reads matches what users see. This is the desired baseline, recorded explicitly so the report shows the check ran and passed.

# How Astova detects it
On an HTTPS page, when `_mixed_content(soup)` returns an empty list, the module emits `tech.mixed_content.ok` as `Status.PASS`, `Severity.INFO`, `value=0`. It only appears on HTTPS pages (an http page produces neither this nor the FAIL). VERIFIED by DOM inspection. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=0` on an HTTPS page with all sub-resources served over HTTPS.

# How to fix it
Nothing to fix; this is a pass. Keep new assets on HTTPS to maintain it.

# Framework Examples
No action needed in any framework. To preserve the state, ensure newly added images/scripts/styles use HTTPS or relative URLs.

# Can Astova generate the fix?
No fix needed - this is the passing state.

# Can an AI coding agent safely automate this?
Not applicable; nothing to change.

# How should an AI coding agent approach this?
No action. If introducing new sub-resources during other work, keep them on HTTPS or relative paths so the page does not regress into tech.mixed_content.

# Verification
See RB-6: Verification model. Remains PASS as long as no `http://` sub-resources are added.

# Related Findings
tech.mixed_content (the failing state), tech.https.

# Future Improvements
None specific; tracked alongside tech.mixed_content.

---

# tech.viewport
# Name
Mobile viewport

# Summary
The page should declare a responsive `<meta name="viewport">` tag. Missing it is a WARN.

# Why this matters
See RB-1: How AI answer engines read pages. The viewport meta tag signals a mobile-responsive, modern page. Its absence correlates with non-responsive layouts that render poorly and are treated as lower-quality, mobile-unfriendly sources. Answer engines favor pages that present cleanly across devices, and the missing tag is a cheap, high-confidence signal that the page may not.

# How Astova detects it
`soup.find("meta", attrs={"name": "viewport"})`. PASS if found, else `Status.WARN`, `Severity.MEDIUM`, with recommendation "Add a responsive <meta name=viewport> tag." `value=bool(viewport)`. Parsed straight from the head, so VERIFIED. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=False` when no `<meta name="viewport">` is present in the document head.

# How to fix it
Add `<meta name="viewport" content="width=device-width, initial-scale=1">` to the document head so the page renders at device width.

# Framework Examples
See RB-3: Framework head injection patterns. Next.js (App Router): export `viewport` metadata or add the tag in the root layout, instead of hardcoding it in every page. Astro: add the tag to the shared layout's `<head>`. WordPress: the active theme's `header.php` (or via `wp_head`). Static HTML: add the tag directly in each page's `<head>`. This is a single deterministic head tag.

# Can Astova generate the fix?
Yes (deterministic) - the viewport tag is a fixed, standard string; Astova has a deterministic generator for it.

# Can an AI coding agent safely automate this?
Usually. Adding the standard viewport tag is safe and well-defined. The only caution is to add it once in the shared head/layout, not duplicated per page, and not to override an existing custom viewport.

# How should an AI coding agent approach this?
Find the single source of the document head (Next.js root layout / `viewport` export, Astro base layout, WP `header.php`, or each static page). Insert the standard responsive viewport tag there. See RB-3: Framework head injection patterns. Do NOT add a second viewport tag if one already exists with custom content, and avoid `maximum-scale=1`/`user-scalable=no`, which harm accessibility. For multi-page static sites, apply the same tag to every page's head.

# Verification
See RB-6: Verification model. Re-scan and confirm the tag is present.

# Related Findings
tech.resource_hints (other head-delivery signals); on-page meta findings.

# Future Improvements
Warn when the viewport tag disables zoom (`user-scalable=no`) for accessibility.

---

# tech.robots.missing
# Name
robots.txt missing

# Summary
No usable `robots.txt` was served at the site root (non-200 or empty). This is a WARN.

# Why this matters
See RB-1: How AI answer engines read pages. `robots.txt` is the first file most crawlers, including AI crawlers, request. Its absence is not fatal (crawlers assume everything is allowed), but it means you have no place to declare crawl rules, no place to point to your sitemap, and no explicit statement about AI-crawler access. Publishing one gives you control over how GPTBot, ClaudeBot, and others treat the site.

# How Astova detects it
`_robots_checks(status, text)` runs when `robots_status` is not None. If `status != 200` or the text is blank, it emits `tech.robots.missing` as `Status.WARN`, `Severity.LOW`, `value=status`. VERIFIED from the fetched response. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=404` when no robots.txt is served.

# How to fix it
Publish a `robots.txt` at the site root. A minimal good default allows all crawlers and references the sitemap. Only add `Disallow` rules for paths you genuinely want kept out of crawls.

# Framework Examples
See RB-4: Framework root files. Next.js (App Router): `app/robots.ts` generating the file, or a static `public/robots.txt`. Astro: `public/robots.txt`. WordPress: a physical `robots.txt` at web root or via an SEO plugin (note WP serves a virtual one if no file exists). Static HTML: a `robots.txt` file at the domain root. Deterministic content.

# Can Astova generate the fix?
Yes (deterministic) - Astova has a deterministic robots.txt generator. It produces a sane default (allow crawlers, declare the sitemap) that the team can review.

# Can an AI coding agent safely automate this?
Usually. Creating a permissive default `robots.txt` with a sitemap reference is safe. The danger is generating an over-broad `Disallow` that blocks crawlers; the default must allow access unless the user explicitly wants paths blocked.

# How should an AI coding agent approach this?
Place the file in the correct root location for the framework (`app/robots.ts` or `public/robots.txt` for Next.js, `public/` for Astro, web root for static/WP). See RB-4: Framework root files. Start from a permissive template that allows all user-agents and includes a `Sitemap:` line. Do NOT add `Disallow: /` or broad disallows, and do NOT block AI crawler user-agents unless the user explicitly asked. Check there is not already a virtual/generated robots.txt (common in WordPress) before adding a conflicting static file.

# Verification
See RB-6: Verification model. Re-scan; a 200 robots.txt flips this to tech.robots.ok.

# Related Findings
tech.robots.ok, tech.robots.ai, tech.robots.sitemap, tech.sitemap.missing.

# Future Improvements
Distinguish a 404 from a 5xx (server error vs deliberately absent) in the guidance.

---

# tech.robots.ok
# Name
robots.txt present

# Summary
A valid, non-empty `robots.txt` was served (200). This is the PASS state, recording its length.

# Why this matters
See RB-1: How AI answer engines read pages. A served `robots.txt` means crawlers, including AI crawlers, have an explicit ruleset to read. This is the baseline for the two follow-on checks (AI-crawler access and sitemap declaration). Its presence is good; the content still needs to be correct, which the related findings assess.

# How Astova detects it
When `robots_status == 200` and the text is non-empty, `_robots_checks` parses it and emits `tech.robots.ok` as `Status.PASS`, `Severity.INFO`, `value=info.length` (the byte length). VERIFIED from the fetched file. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=148` (a 148-byte robots.txt was served).

# How to fix it
Nothing to fix; this is a pass. Verify the related checks (AI-crawler access, sitemap declaration) are also healthy.

# Framework Examples
No action. See RB-4: Framework root files for where the file lives if you need to edit its contents for the related checks.

# Can Astova generate the fix?
No fix needed - this is the passing state. (Edits for content live under tech.robots.ai and tech.robots.sitemap.)

# Can an AI coding agent safely automate this?
Not applicable; nothing to change here.

# How should an AI coding agent approach this?
No action for this finding itself. If the related tech.robots.ai or tech.robots.sitemap findings flag issues, edit the existing robots.txt rather than creating a new one.

# Verification
See RB-6: Verification model. Stays PASS while a non-empty robots.txt is served.

# Related Findings
tech.robots.missing (the failing state), tech.robots.ai, tech.robots.sitemap.

# Future Improvements
Surface a parsed summary (group count, total rules) alongside byte length.

---

# tech.robots.ai
# Name
AI crawler access

# Summary
Checks whether `robots.txt` blocks known AI crawlers from the whole site. If any are blocked at root, this is a WARN.

# Why this matters
See RB-1: How AI answer engines read pages. This is the GEO wedge made concrete. If `robots.txt` sends `Disallow: /` to GPTBot, ClaudeBot, PerplexityBot, Google-Extended, or OAI-SearchBot, those engines cannot read the site and therefore cannot cite it in AI answers. A site can rank in classic search yet be entirely invisible to answer engines because of one robots rule. The check surfaces exactly which AI agents are locked out so the team can confirm it is intentional.

# How Astova detects it
After parsing robots.txt, it tests each agent in `AI_CRAWLERS` (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, `OAI-SearchBot`) with `RobotsInfo.blocks_root`, which returns true if that agent's group, or the `*` group, has `Disallow: /`. If any are blocked: `Status.WARN`, `Severity.MEDIUM`, `value=[blocked agents]`, evidence `Disallow: / for <names>`. Otherwise PASS with `value="allowed"`. VERIFIED by parsing the actual rules. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=["GPTBot", "ClaudeBot"]`, evidence `Disallow: / for GPTBot, ClaudeBot`.

# How to fix it
If the block is unintended, remove the `Disallow: /` for those AI user-agents (or remove a global `Disallow: /` under `User-agent: *` that catches them). If you want AI crawlers in, ensure no group covering them disallows the root. If the block is deliberate (you do not want AI training/citation), leave it and treat the finding as informational confirmation.

# Framework Examples
See RB-4: Framework root files. The edit is to the robots.txt content wherever it is produced: `app/robots.ts` or `public/robots.txt` (Next.js), `public/robots.txt` (Astro), the root file or SEO plugin (WordPress), the root file (static). Remove or scope the disallow rules for the AI user-agents. Deterministic content edit.

# Can Astova generate the fix?
Yes (deterministic) - Astova can deterministically generate robots.txt rules that explicitly allow the AI crawler user-agents, since the agent list and rule format are fixed.

# Can an AI coding agent safely automate this?
Sometimes. Unblocking AI crawlers is a deliberate policy decision, not a pure bug. The agent can safely propose or apply the rule change only when the intent (the site wants to be cited by AI engines) is confirmed, because some sites block these agents on purpose.

# How should an AI coding agent approach this?
Read the existing robots.txt and identify exactly which group blocks the AI agents (a per-agent `Disallow: /` or a catch-all `User-agent: *` `Disallow: /`). Confirm intent before changing policy. To allow them, remove the disallow for those agents or add explicit allow groups. See RB-4: Framework root files. Do NOT silently flip a deliberate block, and do NOT accidentally open up paths the site intends to keep private when loosening rules. Be precise about which user-agent group you edit.

# Verification
See RB-6: Verification model. Re-scan and confirm `value` is `"allowed"`.

# Related Findings
tech.robots.missing, tech.robots.ok, tech.x_robots_tag (header-level blocking), tech.index_conflict.

# Future Improvements
Detect partial disallows (key paths blocked, not just root) and per-agent crawl-delay rules.

---

# tech.robots.sitemap
# Name
Sitemap declared in robots.txt

# Summary
Checks whether `robots.txt` contains a `Sitemap:` directive. Present is PASS; absent is INFO.

# Why this matters
See RB-1: How AI answer engines read pages. A `Sitemap:` line in robots.txt is the canonical, crawler-agnostic way to advertise your sitemap. Crawlers, including AI crawlers, that read robots.txt first discover the full URL list from there, helping them find and index more of your content for potential citation. Without it, discovery relies on the crawler guessing `/sitemap.xml` or following internal links.

# How Astova detects it
After parsing robots.txt, if `info.sitemaps` is non-empty it emits `tech.robots.sitemap` as `Status.PASS`, `Severity.LOW`, `value=[sitemap URLs]`; otherwise `Status.INFO` with a recommendation to add a `Sitemap:` line. `parse_robots` collects every `Sitemap:` directive value. VERIFIED from the parsed file. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=["https://example.com/sitemap.xml"]` (PASS), or no value with the add-sitemap recommendation (INFO).

# How to fix it
Add a `Sitemap: https://yourdomain/sitemap.xml` line to robots.txt pointing at the real, absolute sitemap URL. If you have a sitemap index, point at the index.

# Framework Examples
See RB-4: Framework root files. Next.js: include the sitemap URL in `app/robots.ts` output, or in `public/robots.txt`. Astro: add the line to `public/robots.txt`. WordPress: most SEO plugins add this automatically; otherwise add it to the root file. Static HTML: add the line to the root robots.txt. Deterministic content.

# Can Astova generate the fix?
Yes (deterministic) - adding a `Sitemap:` directive is part of Astova's deterministic robots.txt generation, given the sitemap URL.

# Can an AI coding agent safely automate this?
Usually. Adding a correct absolute `Sitemap:` line is safe and mechanical, provided a sitemap actually exists at that URL.

# How should an AI coding agent approach this?
Confirm the sitemap exists (check tech.sitemap) and use its absolute URL. Add the `Sitemap:` directive to the existing robots.txt source for the framework. See RB-4: Framework root files. Do NOT point at a relative path (the directive requires a full URL) and do NOT reference a sitemap that does not yet exist. If a sitemap index is present, declare the index URL.

# Verification
See RB-6: Verification model. Re-scan and confirm the `Sitemap:` directive is parsed.

# Related Findings
tech.sitemap, tech.sitemap.missing, tech.robots.ok.

# Future Improvements
Validate that the declared sitemap URL actually resolves to a valid sitemap.

---

# tech.sitemap
# Name
XML sitemap (present and valid)

# Summary
A valid sitemap (urlset) or sitemap index was served. PASS, with the entry count recorded.

# Why this matters
See RB-1: How AI answer engines read pages. A valid XML sitemap gives crawlers, including AI crawlers, an explicit list of every URL you want discovered, plus freshness hints. It maximizes the share of your content that engines find and consider for citation, especially deep pages weakly linked internally. A healthy sitemap is a core crawlability foundation for GEO.

# How Astova detects it
`_sitemap_checks` runs when `sitemap_status` is not None. On a 200 with non-empty XML, `parse_sitemap` determines `kind`: a `sitemapindex` root counts child `<sitemap>` entries (labelled "Sitemap index"); a `urlset` root counts `<url>` entries (labelled "XML sitemap"). It emits `tech.sitemap` as `Status.PASS`, `Severity.INFO`, `value=count`, evidence "N URLs" or "N sitemaps". VERIFIED by XML parse. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=42`, evidence `42 URLs`; or for an index, `value=5`, evidence `5 sitemaps`.

# How to fix it
Nothing to fix; this is a pass. Keep the sitemap accurate and current (see tech.sitemap.freshness) and declared in robots.txt (see tech.robots.sitemap).

# Framework Examples
See RB-4: Framework root files. No action needed, but for reference the sitemap is produced by: Next.js `app/sitemap.ts` or a generator; Astro `@astrojs/sitemap` integration; WordPress an SEO plugin; Static HTML a build-time generator or hand-maintained file.

# Can Astova generate the fix?
No fix needed - this is the passing state. (Generation of a missing sitemap is framework-dependent; see tech.sitemap.missing.)

# Can an AI coding agent safely automate this?
Not applicable; nothing to change here.

# How should an AI coding agent approach this?
No action. If working on related findings (freshness, robots declaration), edit the existing sitemap pipeline rather than introducing a parallel one.

# Verification
See RB-6: Verification model. Stays PASS while a valid sitemap is served.

# Related Findings
tech.sitemap.missing, tech.sitemap.invalid, tech.sitemap.freshness, tech.robots.sitemap.

# Future Improvements
Cross-check sitemap URL count against discovered internal links; flag sitemaps over the 50k/50MB limits.

---

# tech.sitemap.missing
# Name
XML sitemap missing

# Summary
No sitemap was served at the expected location (non-200 or empty). This is a WARN at MEDIUM severity.

# Why this matters
See RB-1: How AI answer engines read pages. Without a sitemap, crawlers must discover URLs purely by following links, so weakly-linked or deep pages may never be found and therefore never cited by AI engines. A sitemap is the most reliable way to ensure your full content set is visible to the indexes that feed answer engines.

# How Astova detects it
In `_sitemap_checks`, when `sitemap_status != 200` or the XML is blank, it emits `tech.sitemap.missing` as `Status.WARN`, `Severity.MEDIUM`, `value=status`, recommending publishing one at `/sitemap.xml` or referencing it in robots.txt. VERIFIED from the fetched response. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=404` when `/sitemap.xml` is not served.

# How to fix it
Generate and publish an XML sitemap listing your canonical, indexable URLs, then reference it from robots.txt. Use a generator that updates automatically as content changes rather than a hand-maintained file that drifts.

# Framework Examples
See RB-4: Framework root files. Next.js (App Router): `app/sitemap.ts` returning the URL set, or `next-sitemap`. Astro: the `@astrojs/sitemap` integration in `astro.config`. WordPress: an SEO plugin (Yoast, Rank Math) that generates one automatically. Static HTML: a build-time sitemap generator or a maintained `sitemap.xml`. The mechanism is framework-specific, so generation is not one universal patch.

# Can Astova generate the fix?
No - sitemap generation is framework-dependent (each stack has its own generator and URL source), so Astova does not emit a one-size fix; it can recommend the right per-framework approach.

# Can an AI coding agent safely automate this?
Usually. Wiring up the framework's sitemap mechanism is a well-trodden, safe task. The care needed is to include only canonical, indexable URLs and to keep noindex pages out (otherwise it creates tech.index_conflict).

# How should an AI coding agent approach this?
Detect the framework and use its native sitemap path: add `app/sitemap.ts` (Next.js), enable `@astrojs/sitemap` (Astro), confirm/enable the SEO plugin's sitemap (WordPress), or add a build step (static). See RB-4: Framework root files. Source URLs from the real route/content set, exclude noindex and non-canonical pages, and then declare the sitemap in robots.txt. Do NOT hand-write a static list that will go stale, and do NOT include draft, noindex, or duplicate URLs.

# Verification
See RB-6: Verification model. Re-scan; a valid served sitemap flips this to tech.sitemap.

# Related Findings
tech.sitemap, tech.sitemap.invalid, tech.robots.sitemap, tech.index_conflict.

# Future Improvements
Probe common alternate locations (sitemap_index.xml) and the robots.txt-declared URL before reporting missing.

---

# tech.sitemap.invalid
# Name
XML sitemap invalid

# Summary
A sitemap was served but is not valid XML, or lacks a `<urlset>`/`<sitemapindex>` root. This is a FAIL.

# Why this matters
See RB-1: How AI answer engines read pages. An invalid sitemap is silently ignored by crawlers, so it provides zero discovery benefit while giving the false impression that a sitemap exists. The pages it was meant to advertise may go undiscovered and uncited. A malformed sitemap is effectively no sitemap, but harder to notice.

# How Astova detects it
`parse_sitemap` attempts `ET.fromstring`. On an XML parse error, or when the root local-name is neither `urlset` nor `sitemapindex`, it returns `kind="invalid"`. `_sitemap_checks` then emits `tech.sitemap.invalid` as `Status.FAIL`, `Severity.MEDIUM`, recommending a valid `<urlset>`/`<sitemapindex>` root. VERIFIED by attempting a real parse. See RB-2: Why findings are VERIFIED.

# Evidence Example
A response that is HTML or truncated XML, or whose root element is not `urlset`/`sitemapindex` (e.g. a stray wrapper element), yields `tech.sitemap.invalid` FAIL.

# How to fix it
Regenerate the sitemap so it is well-formed XML with a proper `<urlset>` (for a list of URLs) or `<sitemapindex>` (for a set of sitemaps) root and the standard namespace. Common causes: serving an HTML error page at the sitemap URL, a BOM or leading whitespace breaking the parse, or a custom template emitting the wrong root element.

# Framework Examples
See RB-4: Framework root files. Prefer the framework's native generator over a hand-rolled template: Next.js `app/sitemap.ts`, Astro `@astrojs/sitemap`, WordPress SEO plugin, or a vetted static generator. If a custom template produced the invalid output, fix the root element, namespace, and any content served before the XML declaration. Framework-dependent.

# Can Astova generate the fix?
No - producing a valid sitemap depends on the framework's generator and URL source, so Astova recommends the per-framework fix rather than emitting one.

# Can an AI coding agent safely automate this?
Usually. Replacing a broken hand-rolled sitemap with the framework's standard generator is safe. Care is needed if the invalid response is actually an error page (the real problem may be a failing route, not the template).

# How should an AI coding agent approach this?
First determine why it is invalid: fetch the raw bytes and check whether it is an HTML error page, has leading whitespace/BOM, or has the wrong root. If it is a custom template, fix the root element and namespace and ensure nothing is printed before `<?xml`. Prefer switching to the framework's native sitemap generator. See RB-4: Framework root files. Do NOT just wrap broken output, and confirm the URL stops returning an error page.

# Verification
See RB-6: Verification model. Re-scan; a parseable urlset/sitemapindex flips this to tech.sitemap.

# Related Findings
tech.sitemap, tech.sitemap.missing, tech.sitemap.freshness.

# Future Improvements
Report the specific parse error (malformed XML vs wrong root element) to speed diagnosis.

---

# tech.sitemap.freshness
# Name
Sitemap freshness

# Summary
Checks the newest `<lastmod>` in the sitemap. Older than 180 days is a WARN (stale); otherwise PASS.

# Why this matters
See RB-1: How AI answer engines read pages. `<lastmod>` tells crawlers how recently content changed; AI engines favor fresh, current sources and use freshness to prioritize recrawls. A sitemap whose newest `<lastmod>` is over six months old signals a stale or unmaintained site, lowering recrawl priority and the perceived currency of your content, which matters for being cited on time-sensitive questions.

# How Astova detects it
When `parse_sitemap` finds a `latest_lastmod` (the max `<lastmod>` across entries), `_days_since` computes its age in whole days (parsing ISO date or datetime, defaulting to UTC). If `age > SITEMAP_STALE_DAYS` (180): `tech.sitemap.freshness`, `Status.WARN`, `Severity.LOW`, evidence "newest <lastmod> is N days old". Otherwise PASS with the newest lastmod in evidence. VERIFIED by parsing dates from the sitemap. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=214`, evidence `newest <lastmod> is 214 days old (2025-11-27)`.

# How to fix it
Ensure the sitemap's `<lastmod>` values reflect real content-change dates and regenerate it whenever content changes. If the site genuinely has not changed, the warning is accurate; the fix is to publish or update content and let the sitemap reflect it. Do not fake `<lastmod>` dates.

# Framework Examples
See RB-4: Framework root files. Use a generator that derives `<lastmod>` from real modification times: Next.js `app/sitemap.ts` (set `lastModified` from content dates), Astro `@astrojs/sitemap`, WordPress SEO plugin (automatic), static build generator. Framework-dependent, since it depends on how each pipeline sources modification dates.

# Can Astova generate the fix?
No - freshness depends on real content-update dates flowing through the framework's sitemap generator; Astova cannot fabricate accurate `<lastmod>` values.

# Can an AI coding agent safely automate this?
Sometimes. The agent can fix a generator that omits or hardcodes `<lastmod>` so it uses real modification times. It must NOT fabricate recent dates to silence the warning; that is misleading and the underlying content is still stale.

# How should an AI coding agent approach this?
Inspect the sitemap generator and check where `<lastmod>` comes from. If it is hardcoded, missing, or set to build time rather than content-change time, wire it to the real content modification dates. See RB-4: Framework root files. Do NOT set `<lastmod>` to "now" for all URLs to game freshness; that destroys the signal's value and can hurt recrawl scheduling. If the content truly is old, the right answer is a content update, which is outside a mechanical patch.

# Verification
See RB-6: Verification model. Re-scan; once accurate recent `<lastmod>` values are present, age drops below 180 days and the finding passes.

# Related Findings
tech.sitemap, tech.sitemap.missing; geo content-freshness findings (cross-pillar).

# Future Improvements
Report the distribution of `<lastmod>` ages, not just the newest, to catch partially-stale sitemaps.

---

# tech.index_conflict
# Name
Indexability conflict

# Summary
The page is set to `noindex` (via meta robots/googlebot or the X-Robots-Tag header) yet is listed in the XML sitemap. Contradictory signals: FAIL.

# Why this matters
See RB-1: How AI answer engines read pages. A sitemap says "index this," while `noindex` says "do not." Crawlers receiving both waste crawl budget and may distrust the site's signals. For AI engines, the noindex wins, so the page will not be cited, yet it keeps consuming crawl attention. The conflict usually means either the noindex or the sitemap inclusion is a mistake.

# How Astova detects it
`_index_conflict` sets `noindex=True` if `x-robots-tag` header contains `noindex`, or any `<meta name="robots">`/`<meta name="googlebot">` content contains `noindex`. If noindex is true, it parses the sitemap's `<loc>` URLs (urlset only), normalizes them (`_norm_url`: lowercased host, trailing slash stripped), and if the page's normalized final URL is in that set, emits `tech.index_conflict`, `Status.FAIL`, `Severity.MEDIUM`, evidence "page is set to noindex but is listed in the XML sitemap". VERIFIED by comparing parsed directives against parsed sitemap locs. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value={"noindex": True, "in_sitemap": True}`, evidence `page is set to noindex but is listed in the XML sitemap`.

# How to fix it
Decide the page's intended status. If it should rank and be cited: remove the `noindex` (from the meta tag and/or the X-Robots-Tag header). If it should not: remove it from the sitemap. Never leave both signals contradicting each other.

# Framework Examples
The fix touches two places depending on the decision. To remove noindex: see RB-3: Framework head injection patterns for the meta tag (Next.js `robots` metadata, Astro layout head, WP theme/plugin), or the response-header config for X-Robots-Tag (`next.config.mjs` headers, `vercel.json`, `.htaccess`, nginx). To remove from the sitemap: adjust the sitemap generator (see RB-4: Framework root files) to exclude the URL. Which side to change is a content decision.

# Can Astova generate the fix?
No - resolving the conflict requires a human decision about whether the page should be indexed; the correct side to edit is not deterministic.

# Can an AI coding agent safely automate this?
Sometimes. The agent can apply the fix once the intended state is decided, but it must not guess. Removing a noindex on a page that was deliberately hidden (a thank-you page, a staging route) would wrongly expose it; removing the wrong sitemap entry could drop a page that should rank.

# How should an AI coding agent approach this?
Identify both signals first: locate the `noindex` source (meta `robots`/`googlebot` tag, or the X-Robots-Tag header in `next.config.mjs`/`vercel.json`/`.htaccess`/nginx) and the sitemap entry. Determine intent from context (is this a real content page or a utility/private page?). Then change exactly one side: clear the noindex for pages that should rank, or exclude from the sitemap for pages that should not. See RB-3 and RB-4. Do NOT remove a deliberate noindex just to satisfy the sitemap, and do NOT leave both in place.

# Verification
See RB-6: Verification model. Re-scan; the conflict clears once the page is either fully indexable or absent from the sitemap.

# Related Findings
tech.x_robots_tag, tech.sitemap; on-page robots-meta findings.

# Future Improvements
Detect the inverse (canonical pointing elsewhere yet self-listed in sitemap) and conflicting canonical/noindex pairs.

---

# tech.resource_hints
# Name
Resource hints & script loading

# Summary
Looks at whether the page head uses resource hints and whether scripts are render-blocking. No hints plus render-blocking scripts is a WARN.

# Why this matters
See RB-1: How AI answer engines read pages. Render-blocking scripts delay first render, which matters when a headless renderer (the "what the bot saw" path) has a time budget; a slow first render can mean the bot reads an incomplete page. Resource hints (preload/preconnect/dns-prefetch) speed up critical resource delivery. Faster, less-blocked rendering improves the chance the full content is captured and extractable.

# How Astova detects it
`_delivery_checks(soup)` counts `<link rel=...>` hints whose rel is in `preload, preconnect, dns-prefetch, prefetch, modulepreload`. It counts render-blocking scripts: `<script src>` with neither `async` nor `defer` and `type` not `module`. `ok = hints > 0 or not blocking` (passes if there is at least one hint OR no blocking scripts). PASS or `Status.WARN`, `Severity.LOW`, with `value={resource_hints, blocking_scripts, scripts}` and evidence "N resource hint(s); M render-blocking script(s)". VERIFIED by DOM inspection. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value={"resource_hints": 0, "blocking_scripts": 3, "scripts": 5}`, evidence `0 resource hint(s); 3 render-blocking script(s)`.

# How to fix it
Add `defer` (or `async` where order does not matter) to non-critical `<script src>` tags so they stop blocking first render, and/or add resource hints (`preconnect`/`dns-prefetch` for third-party origins, `preload` for critical assets). Either reducing blocking scripts or adding a hint satisfies the check, but both is better.

# Framework Examples
See RB-3: Framework head injection patterns. Next.js: use `next/script` with the right `strategy` and `next/font`/`<link rel=preconnect>` in the layout; the framework already defers most scripts. Astro: Astro defers module scripts by default; add hints in the base layout. WordPress: enqueue scripts with `defer`/`async` strategy or a performance plugin; add preconnect in `header.php`. Static HTML: add `defer` to script tags and `<link rel=preconnect/preload>` in the head. Content edits, framework-agnostic in spirit.

# Can Astova generate the fix?
No (AI assisted at best) - which scripts are safe to defer and which origins/assets deserve hints is page-specific judgment, not a deterministic transform.

# Can an AI coding agent safely automate this?
Sometimes. Adding `defer` can change execution order and break scripts that expect synchronous execution or run before DOMContentLoaded. Adding `preconnect`/`dns-prefetch` is low-risk. The agent must reason about each script before deferring it.

# How should an AI coding agent approach this?
Inspect each render-blocking `<script src>` and decide: `defer` for scripts that can wait for the DOM (most), keep critical inline bootstrapping synchronous. Add `preconnect`/`dns-prefetch` for third-party origins the page contacts, and `preload` only for truly critical assets. See RB-3: Framework head injection patterns. Do NOT blanket-`async` scripts that depend on load order (that causes race conditions), and do NOT over-preload (too many preloads compete and hurt the very thing they aim to help).

# Verification
See RB-6: Verification model. Re-scan; the check passes once there is at least one hint or zero render-blocking scripts.

# Related Findings
tech.compression, tech.viewport; performance pillar findings (when added).

# Future Improvements
Distinguish first-party from third-party blocking scripts and weight severity by count.

---

# tech.x_robots_tag
# Name
X-Robots-Tag

# Summary
Inspects the `X-Robots-Tag` response header. A header containing `noindex`/`none` is a FAIL; any other value is recorded as INFO.

# Why this matters
See RB-1: How AI answer engines read pages. A header-level `noindex` silently de-indexes a page with no visible sign in the HTML, so it is easy to ship by accident (often a leftover from staging or a blanket server rule). A page blocked this way will not be indexed or cited by AI engines no matter how good its content is, and nothing in the markup reveals why.

# How Astova detects it
`_header_checks` reads `x-robots-tag` (lowercased). If non-empty: when it contains `noindex` or `none`, `tech.x_robots_tag`, `Status.FAIL`, `Severity.HIGH`, `value=header`, evidence `X-Robots-Tag: <value>`. Otherwise `Status.INFO` recording the value. Runs only on live fetches with headers. VERIFIED from the response header. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value="noindex, nofollow"`, evidence `X-Robots-Tag: noindex, nofollow`.

# How to fix it
If the page should be indexed, remove the `noindex`/`none` from the X-Robots-Tag header for this path. The header is usually set by a server rule, CDN/edge config, or framework header config rather than the page itself, so find and scope or remove that rule.

# Framework Examples
This is a response-header fix. Next.js: a `headers()` rule in `next.config.mjs`, a `vercel.json` `headers` entry, or `robots` metadata that emits the header; remove or scope it. Astro: host header config (`netlify.toml`, `vercel.json`). WordPress: a server rule or SEO plugin setting the header; an `.htaccess` `Header set X-Robots-Tag` directive. Static HTML / nginx: an `add_header X-Robots-Tag` in the server block. Often a too-broad rule catching more paths than intended.

# Can Astova generate the fix?
No - the header is set in server/host/framework config and removing it is a policy decision about which paths should be indexed; not a deterministic generator.

# Can an AI coding agent safely automate this?
Sometimes. Removing an accidental `noindex` header is the right fix when the page should rank, but the agent must confirm the page is meant to be public; some `noindex` headers are deliberate (staging, internal tools). A too-broad rule may also be protecting other paths.

# How should an AI coding agent approach this?
Find where the header is set: search `next.config.mjs` (`headers()`), `vercel.json`, `netlify.toml`, `.htaccess`, and `nginx.conf` for `x-robots-tag`. Determine the path scope of the rule and whether the noindex is intentional. Remove or narrow the rule only for paths that should be indexed. Do NOT delete a rule that deliberately hides staging/admin/private paths, and check the rule's path matcher so you do not accidentally expose other routes. Note this header can override or conflict with the HTML meta robots (see tech.index_conflict).

# Verification
See RB-6: Verification model. Re-scan; the FAIL clears when the response no longer carries `noindex`/`none`.

# Related Findings
tech.index_conflict, tech.robots.ai, tech.status.

# Future Improvements
Parse per-bot directives (`googlebot: noindex`) and `unavailable_after` dates.

---

# tech.compression
# Name
Compression

# Summary
Checks the `Content-Encoding` response header for a compression algorithm. Missing compression is a WARN.

# Why this matters
See RB-1: How AI answer engines read pages. Compression (gzip, Brotli, deflate, zstd) shrinks transfer size, so crawlers, including AI crawlers on a time/byte budget, download the page faster and are more likely to fully read it before any timeout. Uncompressed HTML is slower to fetch and render, which can mean the bot captures less of the page.

# How Astova detects it
`_header_checks` reads `content-encoding` (lowercased) and sets `compressed` if it contains any of `gzip`, `br`, `deflate`, `zstd`. PASS if compressed, else `tech.compression`, `Status.WARN`, `Severity.LOW`, `value=encoding or None`, evidence `Content-Encoding: <enc>` or "no Content-Encoding header". Runs on live fetches with headers. VERIFIED from the header. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=None`, evidence `no Content-Encoding header` (WARN); or `value="br"`, evidence `Content-Encoding: br` (PASS).

# How to fix it
Enable gzip or Brotli compression for text responses (HTML, CSS, JS, JSON) at the web server, CDN, or edge. This is a server/CDN setting, not page content.

# Framework Examples
Compression is configured at the server/host/CDN layer, not in framework code. Vercel/Netlify/Cloudflare compress automatically, so a missing header there points to a config or proxy issue rather than a code fix. Self-hosted nginx: `gzip on;` / the Brotli module in the server config. Apache: `mod_deflate` / `mod_brotli` in `.htaccess` or vhost. WordPress/Static HTML behind such a server inherit it. No application-code patch enables this.

# Can Astova generate the fix?
No - compression is server/CDN infrastructure configuration, not generable application code.

# Can an AI coding agent safely automate this?
Never (for the real fix). Compression lives in server/CDN config the agent typically cannot safely change from the app repo. The agent can edit a self-hosted nginx/Apache config if that config is in the repo, but enabling compression at a managed CDN is a dashboard/infra action.

# How should an AI coding agent approach this?
Diagnose where responses are served. On a managed host, compression is usually automatic, so a missing header likely means a misconfigured proxy or a `Content-Encoding`-stripping layer; report that rather than patching app code. If a server config (`nginx.conf`, `.htaccess`) is in the repo, enabling gzip/Brotli for text MIME types there is a reasonable, scoped change. Do NOT attempt to compress responses in application middleware as a workaround without understanding the serving stack, and do NOT compress already-compressed binary types. Treat the core fix as infrastructure.

# Verification
See RB-6: Verification model. Re-scan and confirm a `Content-Encoding` of gzip/br/deflate/zstd on text responses.

# Related Findings
tech.resource_hints, tech.https; performance pillar findings (when added).

# Future Improvements
Compare compressed vs uncompressed size and prefer Brotli over gzip in guidance.

---

# tech.security_headers
# Name
Security headers

# Summary
Checks for five standard security headers. Fewer than three present is a WARN.

# Why this matters
See RB-1: How AI answer engines read pages. Security headers signal a well-maintained, trustworthy origin, which contributes to how favorably automated audits and some ranking/quality signals treat the site. They also harden the page (clickjacking, MIME-sniffing, referrer leakage). For GEO this is best-practice hardening that lifts the site's overall quality profile rather than a direct citation lever.

# How Astova detects it
`_header_checks` checks `_SECURITY_HEADERS`: `content-security-policy` (CSP), `x-content-type-options`, `x-frame-options`, `referrer-policy`, `permissions-policy`. It lists present and missing labels; `ok = len(present) >= 3`. PASS if at least 3 present, else `tech.security_headers`, `Status.WARN`, `Severity.LOW`, `value={present, count}`, evidence listing present and missing, with the missing ones named in the recommendation. Runs on live fetches with headers. VERIFIED from the headers. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value={"present": ["X-Content-Type-Options"], "count": 1}`, evidence `present: X-Content-Type-Options; missing: CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy`.

# How to fix it
Add the missing security headers to responses. Safe defaults: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN` (or a CSP `frame-ancestors`), `Referrer-Policy: strict-origin-when-cross-origin`, a scoped `Permissions-Policy`, and a `Content-Security-Policy`. CSP is the one that needs care, since a wrong policy can break the page.

# Framework Examples
Response-header configuration. Next.js: a `headers()` block in `next.config.mjs`, or `vercel.json` `headers`. Astro: host header config (`netlify.toml` `[[headers]]`, `vercel.json`). WordPress: a security plugin or server rule. Static HTML / nginx: `add_header` directives; Apache: `Header set` in `.htaccess`. The non-CSP headers are near-universal safe defaults; CSP must be tailored per site, so this is framework-and-site-dependent.

# Can Astova generate the fix?
No (the non-CSP headers are close to boilerplate, but) - the full set is framework-dependent and CSP must be authored against the site's actual resources, so Astova does not deterministically generate a safe complete policy.

# Can an AI coding agent safely automate this?
Usually for the simple headers, Sometimes for CSP. `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a conservative `Permissions-Policy` are safe near-defaults. A `Content-Security-Policy` is high-risk: a too-strict policy blocks the site's own scripts/styles and breaks the page, so it needs testing in report-only mode first.

# How should an AI coding agent approach this?
Add the four low-risk headers (`nosniff`, frame options, referrer policy, a minimal permissions policy) in the framework's header config (`next.config.mjs` `headers()`, `vercel.json`, `netlify.toml`, `nginx.conf`, `.htaccess`). For CSP, do NOT ship a tight policy blind: inventory the site's script/style/img/connect origins first and roll out via `Content-Security-Policy-Report-Only` before enforcing. Do NOT set `X-Frame-Options: DENY` on a site that is legitimately embedded, and do NOT add a CSP that omits origins the app actually uses. Crossing from 2 to 3 present headers already clears the check, but add the full safe set where possible.

# Verification
See RB-6: Verification model. Re-scan and confirm at least three (ideally all five) headers are present, and that CSP did not break rendering.

# Related Findings
tech.hsts (a sixth security header, checked separately), tech.https, tech.mixed_content (CSP can mitigate).

# Future Improvements
Validate header values (not just presence): weak CSP, missing `frame-ancestors`, overly permissive `Permissions-Policy`.

---

# tech.llms_txt
# Name
llms.txt

# Summary
Checks for an `llms.txt` file declaring guidance for AI crawlers. Present is PASS; absent is INFO (deliberately low-impact).

# Why this matters
See RB-1: How AI answer engines read pages. `llms.txt` is a proposed convention for giving AI crawlers a curated map and usage guidance for a site. Today few engines actually fetch it, so Astova scores it deliberately low: it is cheap to add and forward-looking, but its absence is not a real visibility problem. Treat it as an optional, low-cost hedge, not a priority fix.

# How Astova detects it
`_llms_check(status, text)` runs when `llms_status` is not None. `present = status == 200 and bool(text.strip())`. If present: `tech.llms_txt`, `Status.PASS`, `Severity.INFO`, evidence "N bytes". If absent: `Status.INFO` (still INFO severity), evidence "not found", with an optional-publish recommendation. Intentionally never escalates above INFO. VERIFIED from the fetched response. See RB-2: Why findings are VERIFIED.

# Evidence Example
`value=True`, evidence `1240 bytes` (PASS); or `value=False`, evidence `not found` (INFO).

# How to fix it
Optionally publish an `llms.txt` at the site root: a short Markdown-style document linking to your most important pages and stating any guidance for AI crawlers. Keep it accurate and concise. This is low priority.

# Framework Examples
See RB-4: Framework root files. Next.js: a static `public/llms.txt` (or an `app/llms.txt/route.ts` handler). Astro: `public/llms.txt`. WordPress: a file at web root or a plugin. Static HTML: a root `llms.txt` file. Plain text/Markdown content.

# Can Astova generate the fix?
Yes (deterministic) - Astova has a deterministic llms.txt generator that builds a starter file from the site's key pages and metadata for the team to refine.

# Can an AI coding agent safely automate this?
Always (it is additive and low-risk). Creating a root `llms.txt` cannot break the running app; the only care is making its content accurate. Given the low impact, the agent should not prioritize it over real findings.

# How should an AI coding agent approach this?
Place the file at the correct root path for the framework (`public/llms.txt` for Next.js/Astro, web root otherwise). See RB-4: Framework root files. Populate it with links to genuinely important pages and concise guidance, not boilerplate. Do NOT spend effort here ahead of higher-impact technical findings, and do NOT contradict robots.txt (do not "guide" AI crawlers to paths you disallow). Keep it small and truthful.

# Verification
See RB-6: Verification model. Re-scan; a served non-empty 200 `llms.txt` flips this to PASS.

# Related Findings
tech.robots.ai, tech.robots.sitemap, tech.sitemap.

# Future Improvements
Validate llms.txt structure and that linked URLs resolve and are indexable.

---

I read the full engine module at `/Users/joshuawalsh/Desktop/Sites/damask/engine/astova_engine/modules/technical.py` and wrote Knowledge Cards for all 24 technical finding IDs across the 14 requested families, separated by `---` in the exact verbatim card structure.

Key accuracy points pulled straight from the code:
- Exact thresholds: redirect chain `hops > 2`; sitemap stale `> 180` days (`SITEMAP_STALE_DAYS`); TLS expiry warn `<= 14` days (`CERT_EXPIRY_WARN_DAYS`), expired when `days < 0`; security headers pass at `>= 3` of 5; resource hints pass when `hints > 0 OR no blocking scripts`.
- Exact finding IDs, statuses, severities, and `value`/`evidence` shapes (e.g. `tech.mixed_content` records count + first insecure URL; `tech.index_conflict` value `{"noindex": True, "in_sitemap": True}`).
- The fixed `AI_CRAWLERS` list (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, OAI-SearchBot) and the five `_SECURITY_HEADERS` (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy).
- Behavioral nuances baked into cards: mixed-content deliberately excludes `<a href>`/canonical; `tech.mixed_content.ok` only emits on HTTPS pages; `tech.llms_txt` intentionally never exceeds INFO; X-Robots-Tag matches `noindex` or `none`; sitemap `urlset` vs `sitemapindex` labelling.

Per the rules I referenced shared blocks RB-1 through RB-6 by name without rewriting them, framed everything around AI answer engines (not SEO), used plain hyphens only, and was explicit that HTTPS/TLS/compression/redirects/HSTS are infrastructure rather than code patches. The "Can Astova generate the fix?" lines follow the real generator reality: deterministic Yes for `tech.viewport`, `tech.robots.missing`, `tech.robots.ai`, `tech.robots.sitemap`, and `tech.llms_txt`; No for the framework-dependent (sitemap, security headers) and infra (https, tls, status, compression, redirects) findings.

The cards are returned above as clean markdown; no files were created.agentId: ab6bf1330f0b5c10e (use SendMessage with to: 'ab6bf1330f0b5c10e' to continue this agent)
<usage>subagent_tokens: 54116
tool_uses: 1
duration_ms: 323965</usage>

## GEO readiness, trust, performance & local findings

---

# Finding ID
`geo.no_content`

# Name
No readable content

# Summary
The page HTML contains almost no visible text; with fewer than 10 visible words the page is treated as effectively empty and all granular content checks collapse into this single critical finding. Almost always a client-rendered SPA whose content never reaches the initial HTML.

# Why this matters
See RB-1. Many AI crawlers do not execute JavaScript. If the headline, product description and body copy only exist after a JS framework hydrates in the browser, those crawlers see a blank shell: nothing to read, chunk, or cite. This is the root cause behind a cascade of downstream symptoms (missing H1, no answer block, thin content), so the engine reports it once rather than as ten confusing alarms.

# How Astova detects it
See RB-2. The module splits visible page text into words; if `total < NO_CONTENT_WORDS` (10) it emits `geo.no_content` (FAIL, CRITICAL) and short-circuits the rest of content analysis. With a render delta it notes when `rendered_words > raw_words + 20`. VERIFIED: the word count is read straight from parsed HTML.

# Evidence Example
`only 4 visible word(s) in the page HTML`

# How to fix it
Get the real content into the HTML the server returns, before JavaScript runs. If this is a JS app, switch the page to server-side rendering, static generation, or prerendering so the headline, key description and main body are in the initial response. This single fix usually clears most other empty-content findings.

# Framework Examples
- Next.js: use a Server Component or `getStaticProps`/`generateStaticParams`; avoid `'use client'` on the main content tree and avoid fetching body copy only in `useEffect`.
- Astro: keep content in `.astro`/`.md`/`.mdx`, not inside a `client:only` island.
- WordPress: usually server-rendered; a headless/JS theme or client-side block is the culprit.
- Static HTML: put the copy in the `.html` file, not injected via script.

# Can Astova generate the fix?
No. This is an architecture/rendering problem, not a copy problem; no deterministic generator and not `ai_draftable`.

# Can an AI coding agent safely automate this?
Sometimes. Converting a route to SSR/SSG is a real change with build and data implications; an agent can often do it but must verify the build and data availability. Never blindly flip rendering modes on a page with client-only data dependencies.

# How should an AI coding agent approach this?
With full codebase access, confirm the rendering strategy: find the route/component, check whether it is a client component, an SPA entry, or fetches main content in a browser-only effect. The fix is structural, not textual; do not invent body copy to fill the page. Move the existing content source (MDX/markdown/CMS query/props) into a server-rendered path. Search for `'use client'`, `useEffect` data fetches, `client:only`, root `<div id="root">`. Do not change the visible copy. See RB-5.

# Verification
Re-fetch without JS execution; confirm the visible word count clears 10 and substantive content is present. With `--render`, confirm the raw-vs-rendered gap closed. See RB-6.

# Related Findings
`geo.js_rendered`, `geo.frontload`, `geo.aeo`, `geo.thin_content`, missing-H1 / missing-meta (all symptoms of this root cause).

# Future Improvements
Detect the framework from build artifacts for a targeted SSR/SSG recipe; distinguish "empty shell" from "paywalled/auth-gated".

---

# Finding ID
`geo.aeo`, `geo.frontload`, `geo.intro_quality` (one knowledge family: the page must lead with a direct, complete, non-promotional answer)

# Name
Up-front answer block (AEO core) - front-loading and intro clarity

# Summary
Three complementary checks judge whether the page opens by answering. `geo.frontload`: do the first ~150 words contain a complete declarative sentence. `geo.aeo`: the document-order offset of the first self-contained answer paragraph, graded by how high it appears. `geo.intro_quality`: flags an opening that sells rather than answers.

# Why this matters
See RB-1. AI engines weight the top of the page heavily and lift the first self-contained, declarative sentence or two. If the opening is a heading, tagline, nav fragment, or marketing pitch, there is no clean answer chunk to extract and the engine cites a competitor who led with the answer. The `geo.aeo` snippet is exposed deliberately as the "answer preview": it is what an AI engine will probably cite.

# How Astova detects it
See RB-2.
- `geo.frontload` (HIGH): first 150 words, find spans ending in `.!?`; pass if any span has `>= 12` words. A run of headings/menu items (no full stops) cannot masquerade as a sentence.
- `geo.aeo` (HIGH): `_first_answer_offset` walks the body in document order counting visible words until a self-contained answer block (`<p>`/`<li>`/`blockquote`/`dd`, or text-only `<div>`/`<section>`) with `>= 12` words and `.!?`. Offset `>= 350` or none -> FAIL; `> 220` -> WARN; else PASS.
- `geo.intro_quality` (MEDIUM): first 80 words; promotional if `>= 2` PROMO_MARKERS, or `>= 1` marker + `>= 1` "!", or `>= 2` "!".
All VERIFIED.

# Evidence Example
- `geo.frontload`: `opens with: "Astova is a deterministic GEO and SEO scanning engine that produces..."`
- `geo.aeo`: `first answer ~270 words in: "..."` (WARN) or `No self-contained answer paragraph in the first 350 visible words.` (FAIL)
- `geo.intro_quality`: `promotional language in the intro: "world-class", "award-winning"; 2 exclamation mark(s)`

# How to fix it
Open with a direct, complete answer sentence to the question the page exists to answer, in the first ~150 words and ideally before 220 words. Make it a real `<p>`, at least 12 words, ending in a full stop. Strip marketing language and exclamation marks from the opening. State the fact first; sell later.

# Framework Examples
- Next.js / Astro: edit the page's MDX/markdown source or the hero/intro component's text prop.
- WordPress: edit the post/page body or the ACF/Gutenberg block holding the opening paragraph.
- Static HTML: edit the first `<p>` after the `<h1>`.
Note: the intro is human-authored copy in MDX/CMS/components, not a config file.

# Can Astova generate the fix?
Partly. `geo.aeo`, `geo.frontload`, `geo.definitive` are `ai_draftable`: Astova can AI-draft a front-loaded answer for human review. Not deterministic; a drafted sentence must be fact-checked. `geo.intro_quality` is guidance, not a generator.

# Can an AI coding agent safely automate this?
Sometimes. This edits the most visible copy, so faithfulness risk is high. An agent may rewrite the opening to front-load an answer only when the answer is already stated elsewhere and can be moved or paraphrased without inventing facts. Propose drafts for review.

# How should an AI coding agent approach this?
With full codebase access, locate where the intro is authored (MDX/markdown body, CMS field, or component prop). Read the whole page first so you know the real answer, then move or paraphrase that answer into the opening, preserving meaning and voice. Avoid: inventing a fact for a punchy lead; changing the meaning of the existing claim; breaking layout by adding a `<p>` where the design expects a heading. Demote marketing copy below the answer rather than deleting it. See RB-5.

# Verification
Re-scan: `geo.frontload` PASS, `geo.aeo` offset drops below 220 (PASS), `geo.intro_quality` no longer flags promo markers. The `geo.aeo` snippet should read as the answer you intend AI to cite. See RB-6.

# Related Findings
`geo.definitive` (the lead should also be confident), `geo.summary_bullets`, `geo.no_content`.

# Future Improvements
Score answer completeness (does the lead actually answer the page's implied question), and detect promotional language beyond the fixed marker list.

---

# Finding ID
`geo.definitive`

# Name
Definitive language

# Summary
Measures how much hedging language ("might", "usually", "arguably") appears. Confident, direct prose is favoured for extraction; hedged prose reads as uncertain and gets passed over.

# Why this matters
See RB-1. A sentence laced with "might", "possibly", "generally" is a weak answer: it signals the source is unsure, so the engine prefers a competitor stating the same thing plainly. Definitive language is roughly twice as likely to be cited.

# How Astova detects it
See RB-2. Counts words whose lowercased, punctuation-stripped form is in `HEDGE_WORDS` (might, maybe, perhaps, possibly, could, sometimes, generally, usually, often, arguably, seemingly, presumably, likely, probably, somewhat, relatively, fairly, tends/tend). `ratio = hedges / total_words`; PASS if `< 0.02`. MEDIUM. VERIFIED.

# Evidence Example
`value: {"hedge_words": 14, "ratio": 0.0312}`

# How to fix it
Rewrite hedged sentences to state the claim directly where it is in fact certain. "This usually improves load time" -> "This reduces load time by X". Keep hedges only where genuine uncertainty exists; do not overclaim. Target under 2% hedge density, not zero.

# Framework Examples
- Next.js / Astro: edit the MDX/markdown body or component text.
- WordPress: edit the post/page body or block content.
- Static HTML: edit the relevant `<p>` elements.

# Can Astova generate the fix?
`geo.definitive` is `ai_draftable`: Astova can AI-draft firmer phrasings for review. Not deterministic; the rewrite must not add confidence where the claim is genuinely uncertain.

# Can an AI coding agent safely automate this?
Sometimes. Removing hedges changes claim strength (a meaning change). Tighten filler hedges where true; never assert certainty the author deliberately avoided. High faithfulness risk; propose for review.

# How should an AI coding agent approach this?
Search body copy for the HEDGE_WORDS terms. For each, judge filler vs load-bearing. Remove filler; leave genuine uncertainty intact. Avoid: turning a cautious accurate statement into an overclaim; stripping hedges from legal/medical/safety copy; changing meaning. See RB-5.

# Verification
Re-scan: `geo.definitive` ratio under 0.02 (PASS). Spot-check no rewritten sentence now overstates. See RB-6.

# Related Findings
`geo.aeo`/`geo.frontload`, `geo.intro_quality`.

# Future Improvements
Per-sentence flagging of the highest-impact hedges (in the lead answer or near data); a domain allowlist where hedging is appropriate.

---

# Finding ID
`geo.structure`, `geo.summary_bullets`

# Name
Extractable structure (lists/tables) and summary bullets near top

# Summary
`geo.structure`: the page has at least one real content list or table (nav excluded). `geo.summary_bullets`: a non-navigation list high on the page (within the first 350 visible words). Both reward scannable, liftable structure near the answer.

# Why this matters
See RB-1. AI Overviews disproportionately favour list/table formatting because a bullet set or table row is already a clean, self-contained unit to quote. An all-prose page, or one whose only lists are menus, gives nothing pre-chunked. A summary list near the top is the most quotable shape in the most-read region.

# How Astova detects it
See RB-2.
- `geo.structure` (MEDIUM): collects `<ul>`/`<ol>`/`<table>`, filters lists via `_is_nav_list`, passes if `(content_lists + tables) > 0`; distinct "navigation only" evidence otherwise. `_is_nav_list` flags lists inside `nav`/`header`/`footer`/`role=navigation`, or where `>= 70%` of items are short (`<= 4` words) link-only.
- `geo.summary_bullets`: top-level lists with offset `< 350`. Non-nav near top -> PASS; only nav near top -> WARN; none -> WARN.
Both VERIFIED.

# Evidence Example
- `geo.structure`: `only navigation menus found - no content lists or tables`
- `geo.summary_bullets`: `the only list in the first 350 words (~120 in) is navigation`

# How to fix it
Add a genuine content list or table near the answer: a short bulleted summary, a comparison table, or a steps list (more than four words per item, not just links). For `geo.summary_bullets`, place a concise summary list within the first ~350 words.

# Framework Examples
- Next.js / Astro: add a markdown/MDX list or a `<Table>`/`<ul>` near the intro.
- WordPress: insert a List/Table block early in the post.
- Static HTML: add a `<ul>`/`<table>` after the opening paragraph.

# Can Astova generate the fix?
Not as a deterministic generator and not in the `ai_draftable` set. An AI assist could draft candidate bullets from existing prose, but content must come from what the page already says.

# Can an AI coding agent safely automate this?
Sometimes. Converting existing prose into a bullet summary is lower risk than inventing claims, but it reshapes copy and can change emphasis. Safe when bullets faithfully restate points already in the body; propose for review.

# How should an AI coding agent approach this?
Find where body content is authored. For `geo.summary_bullets`, extract 3-5 existing key points into a short list right after the intro. For `geo.structure`, mark up naturally tabular/enumerable content (specs, steps, comparisons) as a real list/table. Avoid: turning a nav menu into a "content list"; inventing items; breaking responsive layout with a wide table. See RB-5.

# Verification
Re-scan: `geo.structure` PASS (content list/table counted), `geo.summary_bullets` PASS (non-nav list before offset 350). Confirm the new list is not classified as navigation. See RB-6.

# Related Findings
`geo.chunking`, `geo.aeo`, `geo.qa_headings`/`geo.faq`.

# Future Improvements
Distinguish decorative from substantive lists beyond the link-ratio heuristic; reward tables with header rows separately.

---

# Finding ID
`geo.faq`, `geo.qa_headings`

# Name
FAQ section and question-style headings

# Summary
`geo.qa_headings`: `<h2>`/`<h3>` phrased as questions. `geo.faq`: a real FAQ structure - `FAQPage` JSON-LD, or `>= 2` question headings each followed by a substantive answer. Both align the page with how people prompt AI engines.

# Why this matters
See RB-1. People ask AI engines questions, and engines look for matching Q&A pairs they can lift almost verbatim. A heading mirroring the real prompt followed by a direct answer is the cleanest possible chunk, and `FAQPage` schema spells the pairs out machine-readably.

# How Astova detects it
See RB-2.
- `geo.qa_headings` (LOW): `<h2>`/`<h3>` containing "?". PASS if any, else INFO.
- `geo.faq` (LOW): `FAQPage` in JSON-LD; OR for each `<h2>`/`<h3>`/`<h4>` with "?", walk up to 3 following siblings (stop at next heading) and count a pair when a sibling has `>= 8` words. PASS if schema present OR `pairs >= 2`; else INFO (absence is informational, not a penalty).
Both VERIFIED.

# Evidence Example
- `geo.qa_headings`: `How does GEO scoring work?; What is llms.txt?`
- `geo.faq`: `FAQPage schema, 3 Q&A pair(s)` (PASS) or `no FAQ structure found` (INFO)

# How to fix it
Where appropriate, add an FAQ: phrase H2/H3 headings as the real questions, each immediately followed by a direct answer (>= 8 words). Add `FAQPage` JSON-LD whose questions/answers match the visible copy exactly.

# Framework Examples
- Next.js / Astro: author Q&A in MDX/markdown; add `FAQPage` JSON-LD via a `<script type="application/ld+json">` (RB-3).
- WordPress: an FAQ block/plugin, or schema via the SEO plugin.
- Static HTML: question `<h2>`s with answer `<p>`s plus a JSON-LD block.

# Can Astova generate the fix?
Partly. Visible Q&A copy is not auto-generated. But `geo.faq` has a deterministic `FAQPage` schema generator: given existing on-page question headings and answers, it emits matching JSON-LD. The schema must mirror visible content.

# Can an AI coding agent safely automate this?
Usually for the schema, sometimes for the copy. Generating `FAQPage` JSON-LD from existing visible Q&A is deterministic and low-risk (rule: schema must match visible text). Writing new answers is high faithfulness risk; treat as human-review draft.

# How should an AI coding agent approach this?
First check whether visible Q&A already exists. If so, the safe task is `FAQPage` JSON-LD mirroring it exactly - do not invent or paraphrase answers in the schema. If authoring new FAQs, draw every answer from content already on the page/codebase. Avoid: schema that does not match visible text (a policy violation); inventing answers; an FAQ that does not belong on this page type. See RB-5.

# Verification
Re-scan: `geo.faq` PASS (schema detected and/or `pairs >= 2`), `geo.qa_headings` PASS. Validate the JSON-LD parses and matches the rendered Q&A. See RB-6.

# Related Findings
`geo.aeo`, `geo.structure`, structured-data findings (`FAQPage` is JSON-LD).

# Future Improvements
Validate each `FAQPage` entry has a corresponding visible answer (catch schema/visible mismatch); detect `<details>`/accordion FAQ patterns.

---

# Finding ID
`geo.thin_content`, `geo.depth`

# Name
Content depth

# Summary
A word-count gate. Under 300 visible words -> `geo.thin_content` (WARN); at/above 300 -> `geo.depth` (PASS). Depth and coverage correlate with being cited.

# Why this matters
See RB-1. AI engines prefer sources that cover a topic thoroughly enough to answer follow-ups and supply context around the extracted chunk. A very short page rarely has the substance to be the cited authority.

# How Astova detects it
See RB-2. After the `geo.no_content` 10-word floor, if `total < 300` -> `geo.thin_content` (WARN, MEDIUM) with the count; else `geo.depth` (PASS, INFO). VERIFIED: a deterministic word count.

# Evidence Example
`geo.thin_content`, `value: 180`

# How to fix it
Expand with substantive, accurate coverage: definitions, how/why explanations, examples, supporting data, answers to likely follow-ups. Aim well past 300 words, but only with real content - padding hurts every other GEO signal.

# Framework Examples
- Next.js / Astro: expand the MDX/markdown body or component content.
- WordPress: add sections to the post/page body.
- Static HTML: add content sections.

# Can Astova generate the fix?
`geo.thin_content` is `ai_draftable`: Astova can AI-draft expanded content for review. Not deterministic; any expansion must be fact-checked - adding length is where fabrication risk is highest.

# Can an AI coding agent safely automate this?
Sometimes, with the most caution of any GEO finding. Generating net-new prose to hit a count is the biggest faithfulness risk. An agent should only expand using information that exists elsewhere in the codebase/site or that the human supplies, and surface drafts for review.

# How should an AI coding agent approach this?
Do not pad. First gather real material: related pages, docs, product data, the CMS. Expand from that, answering the topic and likely follow-ups, structured as extractable chunks with subheadings. Avoid: inventing statistics/claims to add length; repeating the same point; drowning the front-loaded answer. See RB-5.

# Verification
Re-scan: `geo.depth` PASS (>= 300 words); confirm additions did not regress `geo.aeo`/`geo.chunking`/`geo.data_density` and contain no invented facts. See RB-6.

# Related Findings
`geo.no_content`, `geo.chunking`, `geo.data_density`, `geo.aeo`.

# Future Improvements
Replace the flat 300-word gate with topic-relative depth (compare against already-cited pages on the same query).

---

# Finding ID
`geo.chunking`

# Name
Extractable chunks

# Summary
Whether the body is broken into discrete, self-contained text blocks rather than walls of text. Counts paragraph-level blocks, how many are substantive, and how many are oversized walls.

# Why this matters
See RB-1. AI engines lift self-contained chunks (a paragraph or list item that stands alone). Clean ~20-80 word paragraphs give many ready-to-quote units; a single 600-word block forces the engine to quote too much or guess boundaries, so a well-chunked competitor wins.

# How Astova detects it
See RB-2. `_chunking` collects word counts of answer blocks (`_is_answer_block`). `substantive` = `>= 15` words; `walls` = `> 150` words. PASS requires `len(substantive) >= 3` AND `len(walls) <= max(1, substantive // 4)`. No blocks -> WARN (LOW); else WARN (MEDIUM). VERIFIED.

# Evidence Example
`4 substantive paragraph(s), 3 wall(s) (>150 words)`

# How to fix it
Split walls into discrete ~20-80 word paragraphs, each making one self-contained point, separated by subheadings where topics change. Use real `<p>`/`<li>`. Keep >= 3 substantive paragraphs; avoid oversized blocks.

# Framework Examples
- Next.js / Astro: in MDX/markdown, separate paragraphs and add `##`/`###` subheadings.
- WordPress: separate paragraph blocks; split long blocks.
- Static HTML: break a long `<p>` into several with headings.

# Can Astova generate the fix?
Not a deterministic generator and not in the `ai_draftable` copy set. Re-paragraphing is mechanical; best treated as structural editing rather than generation.

# Can an AI coding agent safely automate this?
Usually, when purely structural (inserting paragraph breaks and subheadings without altering words) - low faithfulness risk. Becomes "sometimes" if splitting requires new connective/transition or subheading text.

# How should an AI coding agent approach this?
Find the body source (MDX/markdown/component). Insert boundaries at natural topic shifts; add subheadings that accurately label each chunk. Do not change wording. Avoid: splitting mid-thought so a chunk no longer stands alone; inventing subheading text that overstates; breaking markdown/MDX/list nesting. See RB-5.

# Verification
Re-scan: `geo.chunking` PASS (`substantive >= 3`, walls within the `substantive // 4` allowance). Confirm no sentences altered. See RB-6.

# Related Findings
`geo.structure`/`geo.summary_bullets`, `geo.aeo`, `geo.thin_content`.

# Future Improvements
Detect over-fragmented single-sentence spam; account for subheading density, not just paragraph size.

---

# Finding ID
`geo.data_density`

# Name
Quotable data

# Summary
Density of concrete, verifiable figures: percentages, currency, years, measurements, big numbers. Data-rich pages are cited far more; a substantial page making claims with no figures is flagged.

# Why this matters
See RB-1. AI engines disproportionately cite pages with hard, verifiable data because a specific number is exactly the quotable, checkable fact an answer needs. Vague prose with no figures gives nothing concrete to lift.

# How Astova detects it
See RB-2. `_data_density` runs five regexes (`percent`, `currency`, `year`, `measure`, `big_number`), sums matches as `data_points`, computes `per_100_words`. PASS (INFO) if `data_points >= 5` OR `per_100_words >= 1.5`; WARN (MEDIUM) if `words >= 300` but `< 2` figures; else INFO. VERIFIED. (Known weakness: the `year` regex matches any 1900-2099 number.)

# Evidence Example
`only 1 concrete figure(s) across ~540 words` (WARN) or `7 concrete data point(s) (1.8 per 100 words)` (PASS).

# How to fix it
Add real statistics, numbers, dates, prices, measurements supporting the page's claims. Replace vague quantifiers ("a lot faster") with specific figures ("3x faster") wherever you have the data. Only true numbers.

# Framework Examples
- Next.js / Astro: add figures into MDX/markdown or pull from data files/CMS.
- WordPress: add stats into the body or a data block.
- Static HTML: add figures into the content.

# Can Astova generate the fix?
No. No generator and not `ai_draftable`. Numbers are precisely the content an AI must never invent; Astova flags the gap and asks a human for real figures.

# Can an AI coding agent safely automate this?
Never autonomously. Adding numbers is the highest-fabrication-risk edit. An agent may only insert figures sourced verbatim from the codebase, a linked dataset, or human input, and should surface them for confirmation.

# How should an AI coding agent approach this?
Treat as "surface existing data", never "generate data". Search the repo, data files, CMS, and linked sources for real figures already tied to the page's claims; weave only those in with the source noted. Avoid: inventing a plausible statistic; copying a number from an unrelated context; changing a real figure. See RB-5.

# Verification
Re-scan: `geo.data_density` PASS (>= 5 points or >= 1.5 per 100 words). Independently verify every added figure against its source. See RB-6.

# Related Findings
`geo.definitive`, `geo.thin_content`, `geo.aeo`.

# Future Improvements
Weight figures by proximity to the answer block; detect unsourced/suspicious numbers to discourage fabrication; fix the year-regex false positive.

---

# Finding ID
`geo.trust`

# Name
Trust & E-E-A-T signals

# Summary
Whether the page carries the credibility markers AI engines lean on when deciding whether a source is trustworthy enough to cite: a visible author byline, a published/updated date, About and Contact links, and Organization/Person schema with `sameAs`.

# Why this matters
See RB-1. AI engines decide which sources are safe to repeat as fact. Pages with clear authorship, dating and entity identity are weighted as higher-confidence sources and cited more often. An anonymous, undated page reads as low-trust and gets skipped for a competitor that signals accountability.

# How Astova detects it
See RB-2. Counts four signals: (1) author byline (meta author / rel=author / itemprop / JSON-LD author / author-class with short name text); (2) published/updated date (`<time datetime>` / article:published|modified_time / itemprop date / JSON-LD date; a bare `<time>` without `datetime` does not count); (3) About AND Contact links; (4) Organization/Person JSON-LD with a `sameAs` array. PASS at `>= 3` of 4, else WARN. VERIFIED.

# Evidence Example
`present: published/updated date, about & contact links; missing: author byline, entity schema with sameAs`

# How to fix it
Add the missing signals to reach >= 3 of 4: a real author byline near the top; a visible published/last-updated date mirrored in `datePublished`/`dateModified`; About and Contact links; Organization/Person JSON-LD with `sameAs`. Every value must be true.

# Framework Examples
- Next.js: author/date in the article template; JSON-LD via head injection (RB-3).
- Astro: frontmatter (`author`, `pubDate`) rendered into layout + JSON-LD.
- WordPress: theme outputs byline/date; SEO plugin emits Article/Organization schema; add About/Contact to the menu.
- Static HTML: hand-add `<time datetime>`, a byline, footer About/Contact, and Organization JSON-LD.

# Can Astova generate the fix?
No. No deterministic generator; not `ai_draftable`. The author name, date and entity identity are facts only the owner knows.

# Can an AI coding agent safely automate this?
Never automate the values. An agent must never invent an author, date or `sameAs` URL. It can wire real, human-supplied values into the template, but the values are an identity decision.

# How should an AI coding agent approach this?
Identify the article template and where bylines/dates/head metadata render. Ask the human explicitly for the author name, true publish/update date, About/Contact URLs, and official profile links - do not guess. Wire real values in and emit the schema. If a value cannot be supplied, leave that signal out and report it. See RB-5.

# Verification
Re-scan; `geo.trust` reports the new count and PASSes at 3+ of 4. See RB-6.

# Related Findings
`geo.freshness` (date), `geo.entity` (sameAs), `local.gbp`.

# Future Improvements
Distinguish "author exists" from "author is a recognised expert"; validate the `sameAs` profiles resolve to live, matching identities.

---

# Finding ID
`geo.freshness`

# Name
Content freshness

# Summary
Whether the page exposes a real published/updated date and, if so, whether the latest date is recent. Content older than ~18 months reads as stale; a page with no machine-readable date gives no freshness signal.

# Why this matters
See RB-1. AI engines preferentially retrieve and cite content they can confirm is current (prices, statistics, "best X in 2026", how-tos). An undated page forces a guess at recency; a stale page is demoted for a fresher competitor.

# How Astova detects it
See RB-2. Collects dates from JSON-LD `dateModified`/`datePublished`, article meta times, and `<time datetime>`; parses ISO `YYYY-MM-DD`. No date -> INFO; latest within `FRESH_STALE_DAYS` (540, ~18mo) -> PASS; older -> WARN. VERIFIED.

# Evidence Example
`last dated 2023-01-04 (909 days ago)` (WARN), or `no published/updated date found` (INFO).

# How to fix it
Add a visible published/last-updated date mirrored in schema. If the content is genuinely old, refresh it, then update the date to the real revision. Do not bump the date without updating the content - a false freshness signal is dishonest.

# Framework Examples
- Next.js: surface a `lastUpdated` field in the template and emit `dateModified` (RB-3).
- Astro: content-collection frontmatter (`pubDate`, `updatedDate`) rendered visibly + in schema.
- WordPress: display the modified date; SEO plugin emits `dateModified`.
- Static HTML: add `<time datetime>` and `dateModified` JSON-LD.

# Can Astova generate the fix?
No. No generator; not `ai_draftable`. Astova cannot know the true revision date or whether content was refreshed.

# Can an AI coding agent safely automate this?
Never automate the date value. Emitting `dateModified` of "today" without a real update fabricates freshness. An agent can wire a real, human-supplied date in, never invent one or auto-stamp `now()`.

# How should an AI coding agent approach this?
Find where dates render and schema is emitted. Ask the human for the true publish/last-revised dates or whether content actually changed in this edit. If it genuinely changed, set `dateModified` to the real date; if not, do not touch it. Never auto-stamp the current date - flag it.

# Verification
Re-scan; `geo.freshness` reports the new latest date and PASSes if within 540 days. See RB-6.

# Related Findings
`geo.trust` (date is one of its signals), `geo.entity`.

# Future Improvements
Per-content-type freshness windows; detect "updated" dates that move without real content change.

---

# Finding ID
`geo.entity`

# Name
Entity grounding (sameAs)

# Summary
Whether the page carries Organization/Person JSON-LD with `sameAs` links grounding the brand/author as a recognised entity - ideally to a knowledge base (Wikipedia/Wikidata) or several authoritative profiles. This is how a model disambiguates "which Acme" and connects the page to an entity it knows.

# Why this matters
See RB-1. LLMs reason over entities, not strings. `sameAs` to Wikipedia/Wikidata or authoritative profiles ties your page to a node the model recognises and trusts, making correct attribution and citation far more likely. Without grounding, a generative engine may confuse you with a similarly named entity or skip you.

# How Astova detects it
See RB-2. Finds JSON-LD nodes whose `@type` includes Organization/Person. No node -> INFO. Else collects `sameAs`; PASS if linked to a knowledge base (`wikipedia.org`/`wikidata.org`) OR `>= 2` authoritative profiles (linkedin/crunchbase/twitter/x/facebook/instagram/youtube/github). Entity present but weak `sameAs` -> INFO. VERIFIED.

# Evidence Example
`linked to a knowledge base (Wikipedia/Wikidata)` (PASS), or `entity schema present but weak sameAs` (INFO).

# How to fix it
Add/extend Organization/Person JSON-LD with a `sameAs` array of your real, official profiles (and Wikipedia/Wikidata if an entry exists). Use the actual URLs that belong to the entity - linking to the wrong or fabricated profile breaks the grounding.

# Framework Examples
- Next.js: emit Organization JSON-LD in a shared layout so it is on every page (RB-3).
- Astro: entity schema in the base layout.
- WordPress: knowledge-graph settings in the SEO plugin emit `sameAs`.
- Static HTML: hand-write Organization JSON-LD with the `sameAs` array.

# Can Astova generate the fix?
No. No generator; not `ai_draftable`. Astova does not know the entity's real profile URLs and must not guess.

# Can an AI coding agent safely automate this?
Never automate the values. The `sameAs` URLs are identity claims - never invent profile links or assert a Wikipedia entry exists. An agent can scaffold the schema once given real URLs.

# How should an AI coding agent approach this?
Locate where Organization/Person schema is (or should be) emitted. Ask the human for the entity's real official profile URLs and whether a Wikipedia/Wikidata entry exists - never fabricate `sameAs` targets. Add the schema with verified URLs; if none can be supplied, report the gap.

# Verification
Re-scan; `geo.entity` PASSes once a knowledge-base link or `>= 2` authoritative profiles are present. See RB-6.

# Related Findings
`geo.trust`, `local.gbp`/`local.business_schema`.

# Future Improvements
Verify each `sameAs` resolves and references the same named entity; reward a confirmed Wikidata QID.

---

# Finding ID
`geo.js_rendered`

# Name
JavaScript-dependent content

# Summary
Compares the raw HTML the server sends with the fully rendered DOM and flags how much content only appears post-render. AI crawlers that do not execute JavaScript see only raw HTML; if most content is injected client-side they see an empty shell. Runs only when Astova captured a render.

# Why this matters
See RB-1. Several AI crawlers fetch raw HTML and do not run JS. If your headline, body, H1 or structured data only exist after a client render, those engines retrieve a near-empty page and you become invisible to them. The fix is architectural: get content into the initial HTML.

# How Astova detects it
See RB-2. From the render delta (`raw_words` vs `rendered_words`), `render_only = (rendered - raw) / max(rendered, 1)`. `JS_RENDER_WARN = 0.15` (>=15% -> WARN); `JS_RENDER_FAIL = 0.50` (>50% -> FAIL; also FAIL if raw `< 50` words and render-only `>= 0.15`); below 15% -> PASS. Calls out `h1_js_only`/`schema_js_only`. VERIFIED.

# Evidence Example
`raw HTML: 38 words; rendered DOM: 612 words (94% only after JS). Note: structured data (JSON-LD) and the H1 appear only after rendering.`

# How to fix it
Serve the key content in the initial HTML rather than client-side. Move to SSR, SSG, or prerendering so the headline, body and schema are present before JavaScript runs.

# Framework Examples
- Next.js: Server Components / `getStaticProps`/`generateStaticParams` / App Router server rendering. Avoid pushing primary content into `useEffect`-fetched client components. Watch hydration: server markup must match the client tree.
- Astro: static-first; ship content as `.astro` (SSG); reserve `client:*` islands for real interactivity, not body copy.
- WordPress: classic PHP themes server-render; the risk is JS page builders / headless setups - render content server-side.
- Static HTML: content is already in the HTML; no action.

# Can Astova generate the fix?
No. No generator; not `ai_draftable`. This is an architectural rendering change, not a snippet.

# Can an AI coding agent safely automate this?
Sometimes. Moving client-only rendering to SSR/SSG can break hydration, data fetching and interactivity, so it needs care and verification - not a blind transform.

# How should an AI coding agent approach this?
Identify client-only rendering (content fetched in `useEffect`/`onMounted`, `client:only`, data loaded after mount). Move that content to a server-rendered path so it is in the initial HTML. Preserve hydration: server markup must match the client tree, or you get hydration mismatches; keep genuinely interactive pieces as islands/client components. Move fetches to the server boundary, do not duplicate. Verify the H1 and JSON-LD now appear in raw HTML.

# Verification
Re-scan with `--render`; render-only share drops below 15% (PASS) and `h1_js_only`/`schema_js_only` clear. Confirm with a raw `curl` that content is in the initial HTML. See RB-6.

# Related Findings
`geo.no_content`, `geo.bot_access` (different axis: blocked vs cannot-run-JS), `geo.trust`/`geo.entity`.

# Future Improvements
Per-section render-delta; detect hydration mismatches; distinguish prerender-friendly SPAs from hard client-only apps.

---

# Finding ID
`geo.bot_access`

# Name
AI crawler access (blocking / cloaking)

# Summary
Fetches the page as an AI crawler (e.g. GPTBot) and compares with what a normal browser is served. Catches hard blocks (refused/errored) and soft blocks/cloaking (served far less content - a challenge page, consent wall, or near-empty body). This is the layer robots.txt parsing alone cannot see: WAF/CDN rules.

# Why this matters
See RB-1. If an AI crawler cannot fetch your page, it cannot cite you. Many sites unknowingly block GPTBot/ClaudeBot/PerplexityBot at the CDN/WAF (Cloudflare "Block AI bots" / Bot Fight Mode, or a UA firewall rule) while serving humans normally; others serve crawlers a consent/JS wall with none of the real content. Either way you are invisible to the answer engines. This is the most upstream AI-visibility check.

# How Astova detects it
See RB-2. Compares a normal fetch (status + word count) against the AI-crawler fetch: hard block (bot errored, OR `>= 400` while normal `< 400`) -> FAIL (CRITICAL, `blocked: true`); soft block/cloaking (normal `>= 40` words AND bot served `< 0.5` of normal) -> WARN (HIGH); served the same -> PASS. Offline (no bot fetch) -> emits nothing. VERIFIED.

# Evidence Example
`Fetched as GPTBot: HTTP 403, while a normal browser gets HTTP 200.` (FAIL), or `Fetched as GPTBot: HTTP 200, 41 words - but a normal browser gets 880.` (WARN).

# How to fix it
Allow the AI crawlers you want to be cited by - GPTBot (OpenAI), ClaudeBot and anthropic-ai (Anthropic), PerplexityBot, Google-Extended, OAI-SearchBot - in BOTH robots.txt AND at your CDN/WAF. On Cloudflare that is the "Block AI bots" / Bot Fight Mode setting; elsewhere a UA firewall rule. For soft blocks, exempt the AI agents from consent/JS interstitials.

# Framework Examples
- Next.js / Astro / Static HTML: usually not in app code - check Vercel/Netlify/Cloudflare bot settings and any edge middleware that branches on user agent; add allow rules; ensure robots.txt does not disallow them.
- WordPress: check security plugins (Wordfence etc.) and CDN bot-blocking; these often block AI UAs by default.

# Can Astova generate the fix?
No. No generator; not `ai_draftable`. The fix lives in CDN/WAF/host config outside the codebase.

# Can an AI coding agent safely automate this?
Sometimes, only for the in-repo parts (robots.txt, app middleware). It generally cannot change CDN/WAF dashboard settings, and security teams may have blocked bots deliberately - so the WAF side is a human decision.

# How should an AI coding agent approach this?
Determine whether the block is in-repo (robots.txt, edge middleware, server config) or at the CDN/WAF. For in-repo: ensure robots.txt does not disallow the AI UAs and no middleware blocks/challenges them. For CDN/WAF: report it clearly with the exact setting (e.g. Cloudflare "Block AI bots"); confirm the human wants these crawlers allowed before advising the change. Never spoof or weaken security beyond allowing the named AI crawlers.

# Verification
Re-scan as the bot; `geo.bot_access` PASSes with matching status and word counts. See RB-6.

# Related Findings
`geo.js_rendered` (reaches the page but cannot run JS - different axis), `geo.no_content`, technical robots.txt checks.

# Future Improvements
Test each major AI UA separately; correlate with server-log evidence of real crawler visits; distinguish rate-limiting from outright block.

---

# Finding ID
`perf.score`, `perf.lcp`, `perf.cls`, `perf.tbt`, `perf.fcp`, `perf.si`, `perf.field`

# Name
Performance (Core Web Vitals)

# Summary
Pulls Core Web Vitals and the overall Lighthouse score from Google PageSpeed Insights and surfaces both lab metrics (Lighthouse) and real-user field data (CrUX) as separate findings. Covers `perf.score`, LCP, CLS, TBT, FCP, Speed Index, and the CrUX category (`perf.field`).

# Why this matters
See RB-1. Speed is a retrieval and experience factor. Crawlers operate under time/resource budgets - a slow, shifting page is slower to fetch and parse, and where engines drive referral traffic a poor experience undercuts the click. Not the primary GEO lever (extractability and crawler access matter more), but a genuine signal and a real cost.

# How Astova detects it
See RB-2 (an authoritative API counts as VERIFIED). `perf.score`: Lighthouse 0-100 - >=90 PASS, >=50 WARN, <50 FAIL. Metric good_max/poor_min: LCP 2500/4000ms; CLS 0.1/0.25; TBT 200/600ms; FCP 1800/3000ms; SI 3400/5800ms (<=good PASS, >=poor FAIL, between WARN). `perf.field`: CrUX `overall_category` (FAST/GOOD->PASS, AVERAGE/NEEDS_IMPROVEMENT->WARN, SLOW/POOR->FAIL), present only with enough Chrome traffic. Lab and field kept separate.

# Evidence Example
`Lighthouse 47/100 (mobile)`; LCP `5.1 s` (FAIL); `Chrome real-user data: poor` (perf.field FAIL).

# How to fix it
Fix the specific failing metric. LCP: speed up the largest above-the-fold element (preload, compress/resize images, cut render-blocking CSS/JS). CLS: reserve space for images/ads/embeds (width/height), avoid inserting content above existing. TBT: break up long JS tasks, defer non-critical scripts. FCP/SI: reduce server response time and render-blocking resources.

# Framework Examples
Stack-specific.
- Next.js: `next/image`, `next/font`, dynamic imports for heavy client JS, SSR/SSG to cut TBT.
- Astro: zero-JS-by-default; minimise hydrated islands; image integration for sizing.
- WordPress: caching plugin, image optimisation, prune render-blocking plugin CSS/JS.
- Static HTML: explicit image dimensions, preload the LCP image, defer/async non-critical scripts, inline critical CSS.

# Can Astova generate the fix?
No. No generator; not `ai_draftable`. Fixes depend on specific assets, framework and hosting.

# Can an AI coding agent safely automate this?
Sometimes, stack-specific. Some changes are safe and mechanical (image width/height for CLS, lazy-loading below-the-fold, deferring a clearly non-critical script). Others (re-architecting the critical render path, changing bundling) carry regression risk and need measurement.

# How should an AI coding agent approach this?
Read the finding to see which metric failed - do not optimise blindly. Search for the cause: un-sized/large images for CLS/LCP; render-blocking `<script>`/`<link rel=stylesheet>` in head for FCP/LCP; heavy synchronous JS for TBT. Apply targeted changes (dimensions, lazy-load, defer/async, preload the LCP asset). Do NOT blindly remove scripts, change bundlers, or strip CSS - measure before/after and re-run PageSpeed.

# Verification
Re-run the scan (PageSpeed pull); the failing metric and `perf.score`/`perf.field` move toward PASS. Field data lags (real-user) - confirm lab first. See RB-6.

# Related Findings
`geo.js_rendered` (heavy client JS overlaps TBT and crawler visibility), technical load checks.

# Future Improvements
Per-audit opportunity extraction from Lighthouse (specific files); INP field metric; explicit desktop vs mobile split.

---

# Finding ID
`local.business_schema`, `local.nap`, `local.hours`, `local.geo`, `local.gbp`

# Name
Local business (NAP, LocalBusiness schema, hours, geo, GBP)

# Summary
For pages showing local-business signals, checks the structured data and contact details AI engines rely on for "near me" and local queries: LocalBusiness JSON-LD, consistent NAP, opening hours, geo coordinates/map, and a Google Business Profile link. Conditional - emits nothing unless the page actually looks like a local business.

# Why this matters
See RB-1. For local/"near me" questions, AI engines assemble answers from structured business data - they need a machine-readable address, phone, hours and coordinates to say "open now" or "2 miles away." Complete, consistent LocalBusiness schema is what engines can confidently turn into a local answer.

# How Astova detects it
See RB-2. First decides the page is local (a `tel:` link, a postal address in schema, a LocalBusiness JSON-LD type, or a Maps iframe); else silent. When local: `local.business_schema` PASS if a LocalBusiness (sub)type JSON-LD is present, WARN if local signals but no LocalBusiness JSON-LD; `local.nap` PASS if both a phone (tel/`telephone`) AND a postal address (`streetAddress`/`postalCode` or a 3+ word address) present, WARN listing what is missing; `local.hours` PASS if `openingHours`/`openingHoursSpecification`, else INFO; `local.geo` PASS if `geo` lat/long or a maps embed, else INFO; `local.gbp` PASS if a GBP link (`sameAs` or a visible `g.page`/`business.google`/`google.com/maps`/`maps.app.goo.gl`), else INFO. VERIFIED.

# Evidence Example
`LocalBusiness schema present (dentist).` (PASS); `missing: phone` (local.nap WARN); `no opening hours found` (local.hours INFO).

# How to fix it
Add LocalBusiness (or the right subtype) JSON-LD with the real name, full postal address, telephone, `geo` coordinates and `openingHours`, and show consistent NAP on the page. Add a GBP link. Every value must match the real business and be consistent across the page, schema and the actual Google listing - engines cross-check, and a mismatch is worse than an omission.

# Framework Examples
Real business data required - none of this can be templated with placeholder values.
- Next.js: emit LocalBusiness JSON-LD from the location template (RB-3), fed by real address/phone/hours from CMS/config.
- Astro: schema in the location layout, from frontmatter holding real details.
- WordPress: a local-SEO plugin emits LocalBusiness schema - fill in genuine NAP/hours/map.
- Static HTML: hand-write LocalBusiness JSON-LD with real values.

# Can Astova generate the fix?
Partly. `local.business_schema` has a deterministic PLACEHOLDER generator - it scaffolds a valid LocalBusiness JSON-LD skeleton - but the real values must be filled by a human; the placeholder is not publishable. The other local findings have no generator. None are `ai_draftable`.

# Can an AI coding agent safely automate this?
Never automate the values. Address, phone, hours, coordinates and GBP URL are business facts; an agent must not invent or guess them, and a wrong value actively harms (engines cross-check against the real listing). An agent can scaffold the schema structure; the human supplies every value.

# How should an AI coding agent approach this?
Find the location template and where schema is emitted; scaffold the LocalBusiness JSON-LD shape. Gather real data from the human - exact business name, full postal address, phone, opening hours, lat/long and GBP URL. Never fabricate. Fill the schema with verified values; ensure the visible NAP matches exactly; cross-check page text, schema and the real Google listing agree. Leave any unconfirmed value blank and flag it.

# Verification
Re-scan the local page; `local.business_schema` and `local.nap` PASS and the optional findings clear once real hours/geo/GBP are present. See RB-6.

# Related Findings
`geo.entity` (entity identity overlap), `geo.trust`, structured-data validity.

# Future Improvements
Validate NAP consistency across the site; verify the GBP link resolves to a live matching profile; flag address/phone mismatches between visible text and JSON-LD.

---

## Coverage map (every finding -> its card)

| Card | Finding IDs covered |
|---|---|
| Title | title.missing, title.length |
| Meta description | meta.description.missing, meta.description.length |
| Headings & H1 | h1.missing, h1.multiple, h1.ok, headings.structure, onpage.heading_order |
| Canonical | canonical |
| Indexability signals | robots.noindex, robots.indexable, onpage.snippet_directives |
| Structured data (JSON-LD) | schema.jsonld, schema.missing, schema.validation |
| Open Graph / social meta | opengraph |
| hreflang | onpage.hreflang |
| Image alt text | images.alt |
| Image dimensions | onpage.images.dims |
| Links & anchors | onpage.links, onpage.outbound, onpage.link_attrs, onpage.crawlable_anchors, onpage.jump_links |
| HTML lang | onpage.lang |
| Form labels | onpage.form_labels |
| URL structure | onpage.url |
| HTTPS | tech.https |
| HTTP status | tech.status |
| Redirects | tech.redirect, tech.redirect.chain |
| HSTS | tech.hsts |
| TLS certificate | tech.tls |
| Mixed content | tech.mixed_content, tech.mixed_content.ok |
| Viewport | tech.viewport |
| robots.txt & AI crawler directives | tech.robots.missing, tech.robots.ok, tech.robots.ai, tech.robots.sitemap |
| XML sitemap | tech.sitemap, tech.sitemap.missing, tech.sitemap.invalid, tech.sitemap.freshness |
| Index conflict | tech.index_conflict |
| Resource hints | tech.resource_hints |
| X-Robots-Tag | tech.x_robots_tag |
| Compression | tech.compression |
| Security headers | tech.security_headers |
| llms.txt | tech.llms_txt |
| No readable content | geo.no_content |
| Up-front answer (AEO core) | geo.aeo, geo.frontload, geo.intro_quality |
| Definitive language | geo.definitive |
| Extractable structure & summary bullets | geo.structure, geo.summary_bullets |
| FAQ & Q&A | geo.faq, geo.qa_headings |
| Content depth | geo.thin_content, geo.depth |
| Extractable chunks | geo.chunking |
| Quotable data | geo.data_density |
| Trust & E-E-A-T | geo.trust |
| Content freshness | geo.freshness |
| Entity grounding | geo.entity |
| JavaScript-dependent content | geo.js_rendered |
| AI crawler access | geo.bot_access |
| Performance (Core Web Vitals) | perf.score, perf.lcp, perf.cls, perf.tbt, perf.fcp, perf.si, perf.field |
| Local business | local.business_schema, local.nap, local.hours, local.geo, local.gbp |

**44 Knowledge Cards cover roughly 80 raw finding IDs.** The gap is the point: the engine's finding
taxonomy is heavily inflated by pass/fail/length/`.ok` variants of the same underlying check, so the
amount of *distinct knowledge* is far smaller than the finding count suggests.

---

## Analysis (the five questions)

### 1. How many unique Knowledge Cards are required?
**44.** They cover ~80 finding IDs. The 2:1 collapse is a signal in itself (see Challenge, below):
the engine emits separate IDs for `title.missing` vs `title.length`, `h1.missing`/`multiple`/`ok`,
`tech.mixed_content` vs `tech.mixed_content.ok`, etc., but each pair/triple is one piece of knowledge.

### 2. Which 10 provide the highest customer value?
The ones that decide whether an AI engine can see, extract, and trust you at all:
1. **AI crawler access** (geo.bot_access) - if the crawler is blocked, nothing else matters.
2. **JavaScript-dependent content** (geo.js_rendered) - invisible content to non-JS crawlers.
3. **Up-front answer / AEO** (geo.aeo + family) - the chunk that actually gets cited.
4. **Structured data** (schema) - machine extraction and entity grounding.
5. **No readable content** (geo.no_content) - the empty-shell root cause.
6. **Extractable structure & summary bullets** - the most quotable shapes.
7. **FAQ & Q&A** - matches how users prompt engines.
8. **Trust & E-E-A-T** - whether you are a safe source to repeat.
9. **Definitive language** - confident claims get cited ~2x more.
10. **Content depth / chunking** - enough substance, cleanly liftable.
These are the GEO core plus the two access/visibility gates. Everything technical and on-page is table
stakes beneath them.

### 3. Which 10 would create the biggest improvement if they became deterministic fixes?
These are already deterministically generatable; the leverage is **auto-apply** (the missing layer):
1. Structured data (schema.missing) 2. Canonical 3. robots.txt / AI-crawler allow 4. llms.txt
5. Security headers (framework-deterministic) 6. XML sitemap (framework-deterministic) 7. Viewport
8. FAQPage schema (geo.faq) 9. Open Graph meta 10. hreflang.
The win is not "can Astova write the fix" - it can - it is "Astova opens a PR / one-clicks it." These
are all head-injection or root-file patches with low risk and clear verification, so they are the right
first target for an apply layer.

### 4. Which findings should never become automatic?
Anything that fabricates facts or identity, or that could break the site or lock out crawlers without a
human decision:
- **Business/identity facts:** all of local.* values (NAP, hours, geo, GBP), geo.trust author/dates,
  geo.entity `sameAs`, geo.freshness date.
- **Quotable data:** geo.data_density figures - inventing a statistic is the worst possible outcome.
- **Editorial judgement:** geo.intro_quality / geo.definitive / geo.thin_content rewrites must be
  human-reviewed drafts, never silent commits; onpage.outbound source choices.
- **Infrastructure / security:** the CDN/WAF side of geo.bot_access, tech.https/tls/hsts,
  security-policy changes - confirm intent first; a block may be deliberate.

### 5. Which findings are weak or poorly defined and should probably be removed or simplified?
Honest list:
- **onpage.url** - URL structure usually cannot be changed post-hoc, the check allows one issue, and it
  is a weak AI-readiness signal. Candidate to drop.
- **onpage.jump_links** and **onpage.snippet_directives** - niche, low-signal. Merge into one
  "indexability hygiene" card or drop.
- **tech.resource_hints, tech.compression, onpage.images.dims** - these are performance-adjacent and
  overlap the Performance pillar. Fold them under Performance rather than scattering them across pillars.
- **onpage.heading_order** - false-positives on valid HTML5 sectioning (`<section>`-scoped h1->h3). Tighten
  or downgrade.
- **geo.data_density** - the `year` regex matches any 1900-2099 number (phone fragments, pixel sizes),
  inflating density. Fix the regex, do not remove the finding.
- **The `*.ok` / pass-only findings** (h1.ok, robots.indexable, tech.mixed_content.ok, ...) - useful
  internally but they clutter the taxonomy; they are statuses, not separate findings.

---

## Challenge to the current implementation, and simplifications

1. **Collapse the finding taxonomy.** ~80 IDs reducing to 44 knowledge concepts is the clearest evidence
   that the engine over-models. A check should have **one stable id and a status**, not separate ids for
   `missing` / `length` / `ok`. This simplifies the engine, the 20-row scorecard mapping, the diff logic,
   and this knowledge base in one move - and it matches the platform principle of fewer concepts.
2. **One pillar per concern.** Move the performance-adjacent technical checks (compression, resource
   hints, image dimensions) under Performance. Stop emitting local findings under the GEO pillar while a
   dead `Pillar.LOCAL` weight sits unused (see NEXT_DECISIONS #6).
3. **Prune low-signal checks** (url, jump_links, snippet_directives) so every finding earns its place. A
   tighter, calibrated finding set is more credible than a long one.
4. **The knowledge, not the patch, is the asset.** This document - the "why it matters for AI engines",
   the "how an agent should approach it", the "what never to automate" - is what makes Astova the source
   of truth. The patch is downstream of the card. Keep this maintained as production code: when a check
   changes, its card changes in the same commit.
