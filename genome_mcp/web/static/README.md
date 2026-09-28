# `web/static/`

| File | Purpose |
| --- | --- |
| `index.html` | Layout: disclaimer, sample picker, Ask box, QC tiles, findings, APOE, medicines, gene explorer, Claude Desktop config |
| `base.css` | Shared design tokens (light + dark) and components |
| `app.css` | Finding cards, ask box, tool-trace styles |
| `app.js` | API calls and one renderer per tool (the same renderers are used for Ask answers and the dashboard) |

No build step and no external CDN.
