# wikifi

A modern, minimalistic static wiki generator.

## Features

- **MediaWiki-style design** — sidebar navigation, infoboxes, breadcrumbs
- **Grid background** — subtle dot-grid aesthetic, clean and professional  
- **Keyword links** — `[[path/to/page]]` syntax with colour, icon & name overrides
- **Two page types** — standard content pages and rich infobox pages
- **Client-side search** — instant fuzzy search powered by a JSON index
- **Gallery & lightbox** — image galleries with click-to-zoom
- **GitHub Pages ready** — fully static, no server required

---

## Installation

```bash
pip install -r requirements.txt
```

**Dependencies:** `markdown`, `pyyaml`, `jinja2`

---

## Usage

```bash
# Build wiki
python wikifi.py ./my-wiki

# Build and serve locally at http://localhost:8080
python wikifi.py ./my-wiki --serve

# Custom port
python wikifi.py ./my-wiki --serve --port 3000

# Serve existing build without rebuilding
python wikifi.py ./my-wiki --serve --no-build
```

---

## Project Structure

```
my-wiki/
├── config.json            ← Site configuration
├── data/                  ← Wiki pages
│   ├── people/
│   │   └── john/
│   │       └── content.md
│   └── places/
│       └── city/
│           └── content.md
├── asset/                 ← Images and static files
│   ├── logo.png
│   └── icons/
│       └── person.png
└── wiki/                  ← ✦ Generated output (do not edit)
    ├── assets/
    │   ├── style.css
    │   └── wiki.js
    ├── people/
    │   └── john.html
    ├── search_index.json
    └── pages.json
```

---

## config.json

```json
{
  "site": {
    "title": "My Wiki",
    "description": "A wiki about things",
    "logo": "asset/logo.png",
    "favicon": "favicon.ico",
    "home": "data/home/content",
    "hero_bg": "asset/hero.jpg"
  },
  "nav": [
    { "name": "Home",   "link": "index.html" },
    { "name": "People", "link": "wiki/people/index.html" },
    { "name": "Places", "link": "wiki/places/index.html" }
  ]
}
```

| Field | Description |
|---|---|
| `site.title` | Site name shown in header and `<title>` |
| `site.description` | Subtitle shown on the hero section |
| `site.logo` | Path to logo image (relative to project root) |
| `site.favicon` | Path to favicon |
| `site.home` | Path key of the home page content (optional) |
| `site.hero_bg` | Background image for the hero section |
| `nav` | Array of `{ name, link }` for header navigation |

---

## content.md — Standard Page

```markdown
---
type: none
title: 'John Smith'
keyword:
  name: 'John Smith'
  color: '#3b82f6'
  icon: 'icons/person.png'
gallery:
  - photos/john1.jpg
  - photos/john2.jpg
---

# About John

John is a man known for his work in [[places/city]].

He is friends with [[people/jane|color:#ec4899|name:Jane]].

[[photos/john-banner.jpg]]
```

### Frontmatter Fields

| Field | Required | Description |
|---|---|---|
| `type` | Yes | `none` or `infobox` |
| `title` | Yes | Page title shown as `<h1>` |
| `keyword.name` | Yes | Short display name used in keyword chips |
| `keyword.color` | Yes | Hex color for keyword chip accent |
| `keyword.icon` | No | Path to icon image (relative to `/asset/` or full URL) |
| `gallery` | No | List of image paths to show as a gallery strip |

---

## content.md — Infobox Page

```markdown
---
type: infobox
title: 'John Smith'
keyword:
  name: 'John Smith'
  color: '#3b82f6'
  icon: 'icons/person.png'
infocard:
  image:
    - photos/john.jpg
  uncategorized-property: Some value
  personal-info:
    age: 17
    origin: Lives in [[places/city]]
    status:
      - Active
      - Field Agent
  appearance:
    hair: Brown
    eyes: Blue
---

# John Smith

John is a man who lives in [[places/city]].
```

The `infocard` dict can contain:
- `image`: path(s) to profile images
- **Flat key/value pairs** — rendered as uncategorized rows
- **Nested dicts** — the dict key becomes a category header row
- **List values** — rendered one per line
- **Keyword syntax** — `[[path/to/page]]` is resolved in infocard values

---

## Keyword Syntax

```
[[path/to/page]]                              Basic link
[[path/to/page|name:New Name]]                Override display name
[[path/to/page|color:#FF6B6B]]                Override chip color
[[path/to/page|icon:icons/other.png]]         Override icon
[[path/to/page|color:#F59E0B|name:Override]] Multiple overrides

[[photos/image.jpg]]                          Inline image embed
```

The `path` is relative to the `/data/` directory, e.g. `people/john` maps to `data/people/john/content.md`.

---

## GitHub Pages Deployment

1. Build your wiki: `python wikifi.py ./my-wiki`
2. Push the entire project folder to a GitHub repository
3. In **Settings → Pages**, set source to the root of your main branch
4. GitHub Pages will serve `index.html` automatically

---

## Customisation

### Colours & fonts

Edit `wikifi/assets/style.css` and change the CSS variables in `:root`:

```css
:root {
  --accent: #2563eb;       /* Link & accent colour */
  --grid-color: rgba(0,0,0,.045);  /* Background grid intensity */
  --grid-size: 24px;       /* Background grid spacing */
  --sidebar-w: 220px;      /* Sidebar width */
  --content-max: 860px;    /* Max content width */
}
```

### Per-wiki themes

You can add a `theme` field to `config.json` and extend the generator to swap out the stylesheet file or inject custom CSS variables.


---

## Folder Pages

Any folder path like `wiki/characters/` automatically gets an `index.html` page that lists all its contents.

### Optional .root.md

Create a `.root.md` file inside a data folder to add a description at the top of the folder index page:

```
data/
├── characters/
│   ├── .root.md          ← Custom folder page content
│   ├── elara/
│   │   └── content.md
│   └── kade/
│       └── content.md
```

The `.root.md` file uses the same format as `content.md` (YAML frontmatter + markdown body), but **without `type: infobox`**. The folder name, color, and icon are set in the `keyword` block.

```markdown
---
type: none
title: 'Characters'
keyword:
  name: 'Characters'
  color: '#8b5cf6'
  icon: 'icons/characters.png'
---

These are the people who shape the world of Lume.

Browse all characters below.
```

### Linking nav to folder pages

In `config.json`, use `wiki/foldername/index.html` to link to a folder page:

```json
{
  "nav": [
    { "name": "Characters", "link": "wiki/characters/index.html" },
    { "name": "World",      "link": "wiki/world/index.html" }
  ]
}
```

---

## Design

wikifi uses a **dark professional** theme with:

- Near-black background (`#0c0d0f`) with a subtle crosshatch grid
- Gold accent colour (`#c4a96b`) 
- Sharp edges — no rounded corners
- **Grandiose page hero** — each page gets a full-bleed banner that uses its infocard/gallery/icon image as a heavily blurred, darkened background
- **Keyword chips** — square-bracket style tags with a coloured left border, no underline
- Sidebar navigation with gold active-indicator

### Customising colours

Edit `:root` in `wikifi/assets/style.css`:

```css
:root {
  --accent:     #c4a96b;   /* Main accent colour */
  --bg:         #0c0d0f;   /* Page background */
  --grid-size:  28px;      /* Background grid spacing */
  --grid-color: rgba(255,255,255,0.025); /* Grid line opacity */
}
```
