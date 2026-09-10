# Thai VTuber SNA website

The website has one entry point: `index.html`. Shared navigation selects a view:

- `?view=network` — interactive network (default)
- `?view=research` — analysis using the existing dashboard data
- `?view=report` — report prototype; research fields are still unconnected

Markup lives in inert templates inside `index.html`. `site.js` mounts only the
selected template and loads its CSS and scripts. Switching views performs a normal
navigation, so browser Back/Forward work and graph scripts do not run on report pages.
Report chapters can be linked directly, for example `?view=report#methodology`.

## Local preview

From the repository root:

```sh
python -m http.server 8000 --directory web
```

Open `http://localhost:8000/`. Use HTTP rather than opening files directly because
the visualizations fetch JSON.

## Deploy

Publish the entire `web` directory as the static site root. No build command,
backend, or SPA rewrite is required. Relative asset paths support hosting under a
subdirectory as well. Include all JSON files and the `research` and `data` folders.

The former `/research/` and `/research/index_v2.html` pages have been consolidated.
Update old bookmarks to `?view=research` and `?view=report`; if retaining external
links is necessary, configure those redirects in the chosen hosting provider.
