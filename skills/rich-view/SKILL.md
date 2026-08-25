---
name: rich-view
description: Publish query results as an expiring rich HTML page
version: 1.0.0
metadata:
  hermes:
    tags: [ui, reports, tables, business]
    category: business
    config:
      - key: rich_view.ttl_seconds
        description: "Presigned link lifetime (env RICH_VIEW_TTL_SECONDS)"
        default: "600"
---
# Rich View

Turns tabular query results (leads lists, task digests, expense reports) into
an interactive HTML page — sortable table (Tabulator, MIT) plus an optional
bar/pie chart (Apache ECharts) — uploads it to S3-compatible storage
(Cloudflare R2 free tier, or self-hosted MinIO), and returns a **unique
presigned URL that expires after ~10 minutes**. The chat message carries the
link; the page dies on schedule.

## When to Use
- A query result has more than ~8 rows or the user asks to "show as a
  table/page/report/chart".
- Monthly expense reports and weekly lead summaries.
- NOT for one-liner answers — never publish a page for two rows.

## Procedure
1. Build the spec JSON: `columns` (field/title), `rows`, optional `chart`
   (type bar|pie, labels, values) and `note`. Data comes from the skill
   queries (crm-leads `query.py`, pm-tasks `report`, flow-expense `report`)
   — never hand-typed numbers.
2. Render: `python scripts/render_view.py --input spec.json` → HTML file.
3. Publish: `python scripts/publish_view.py --file <html>` → JSON with `url`
   and `expires_in_seconds`.
4. Send the link with a one-line summary AND the expiry notice, e.g.
   "📊 12 leads · link valid ~10 min: <url>".
5. If `RICH_VIEW_S3_*` env is not configured, the publish script fails
   cleanly — fall back to a plain monospace table in the chat message.

## Server setup (one-time, documented for the operator)

**Cloudflare R2 (recommended, free):** create a bucket (keep it PRIVATE — no
public access needed, presigned URLs do the work) → create an R2 API token
(Object Read & Write, scoped to the bucket) → add a lifecycle rule deleting
objects after 1 day (defense in depth; links die in 10 min regardless) → set:

```bash
RICH_VIEW_S3_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
RICH_VIEW_S3_BUCKET=agent-reports
RICH_VIEW_S3_KEY_ID=...      RICH_VIEW_S3_SECRET=...
RICH_VIEW_S3_REGION=auto     RICH_VIEW_TTL_SECONDS=600
```

**Self-hosted alternative:** MinIO works with the same code path
(`RICH_VIEW_S3_REGION=us-east-1`). Note from our due diligence: pastebin-type
tools (rustypaste, PrivateBin) deliberately hard-code HTML to be served as
`text/plain` for XSS safety — they cannot host rendering pages; S3 semantics
(stored Content-Type served verbatim) are the right primitive here.

## Pitfalls
- The URL is unguessable but **unauthenticated** — anyone holding the link can
  view it until expiry. Do not publish data the user did not just ask for;
  never raise the TTL above one hour.
- Numbers on the page must come from re-runnable queries, never model
  arithmetic (same rule as flow-expense reports).
- CDN note: the page loads Tabulator/ECharts from jsdelivr; for
  China-mainland-only viewers switch the CDN constants in `render_view.py`
  to a domestic mirror.
- In-channel alternative: on channels with rich cards (Feishu card tables) a
  small result can go straight into the card; the page is for anything a chat
  card cannot hold. (Future path: the A2UI protocol — a2ui.org, Apache-2.0 —
  is natively supported by OpenClaw canvas for desktop surfaces.)

## Verification
`publish_view.py --self-test` must pass (validates the SigV4 signer against
the official AWS test vector). After publishing, fetch the URL once (HTTP 200,
content-type text/html) before sending it to the user.
