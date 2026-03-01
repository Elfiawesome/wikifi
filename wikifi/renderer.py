"""
wikifi/renderer.py
Renders wiki pages, folder pages, and index.html to HTML.

Path model
----------
All output lives inside wiki/:
  wiki/welcome.html
  wiki/characters/elara.html
  wiki/characters/index.html   ← folder page

User assets are copied to wiki/asset/ during build.

depth = # of dir levels INSIDE wiki/
  "welcome"          → depth 0
  "characters/elara" → depth 1
  "a/b/c"            → depth 2

Folder pages sit at "characters/index.html" → their key depth equals
the folder key depth (same as a page at the same level as index.html).
"""

import json
from pathlib import Path
from jinja2 import Environment, BaseLoader

_env = Environment(loader=BaseLoader(), autoescape=False)
_env.filters['jsonify'] = lambda v: json.dumps(v, ensure_ascii=False)

# ─── Depth / prefix helpers ───────────────────────────────────────────────────

def _depth(key: str) -> int:
    """Folder levels inside wiki/ for a PAGE key. 'welcome'→0, 'chars/elara'→1"""
    return len(Path(key).parts) - 1

def _folder_depth(fkey: str) -> int:
    """Folder page (index.html) sits one level deeper than the folder key.
    folder 'characters' → file wiki/characters/index.html → depth 1"""
    return len(Path(fkey).parts)

def _wpfx(depth: int) -> str:
    return '../' * depth

def _rpfx(depth: int) -> str:
    return '../' * (depth + 1)

# ─── Infobox ──────────────────────────────────────────────────────────────────

def _fmtk(k): return str(k).replace('-',' ').replace('_',' ').title()
def _fmtv(v):
    if v is None: return '<span class="infobox__empty">—</span>'
    if isinstance(v, list): return '<br>'.join(_fmts(x) for x in v)
    return _fmts(v)
def _fmts(v):
    if v is None: return '—'
    return str(v)

def render_infobox(infocard: dict, page_data: dict, wp: str) -> str:
    if not infocard: return ''
    title = page_data.get('title','')
    color = (page_data.get('keyword') or {}).get('color','#c4a96b')
    images = infocard.get('image',[])
    if isinstance(images, str): images = [images]
    imgs_html = ''
    for img in images:
        src = img if img.startswith('http') else f"{wp}asset/{img}"
        imgs_html += f'<img class="infobox__img" src="{src}" alt="{title}">\n'
    rows = ''
    for key, val in infocard.items():
        if key == 'image': continue
        if isinstance(val, dict):
            rows += f'<tr class="infobox__cat-row"><th colspan="2">{_fmtk(key)}</th></tr>\n'
            for pk,pv in val.items():
                rows += f'<tr><th>{_fmtk(pk)}</th><td>{_fmtv(pv)}</td></tr>\n'
        else:
            rows += f'<tr><th>{_fmtk(key)}</th><td>{_fmtv(val)}</td></tr>\n'
    return (f'<aside class="infobox" style="--infobox-color:{color}">'
            f'<div class="infobox__header" style="background:{color}">{title}</div>'
            f'<div class="infobox__imgs">{imgs_html}</div>'
            f'<table class="infobox__table"><tbody>{rows}</tbody></table></aside>')

def render_gallery(images: list, wp: str) -> str:
    if not images: return ''
    items = ''
    for img in images:
        src = img if img.startswith('http') else f"{wp}asset/{img}"
        items += f'<div class="gallery__item"><img src="{src}" alt=""></div>\n'
    return f'<div class="wiki-gallery">{items}</div>'

# ─── Hero image resolution ────────────────────────────────────────────────────

def _hero_img_src(page_data: dict, wp: str) -> str:
    """Return the best image URL to use as the page hero background."""
    # 1. First infocard image
    infocard = page_data.get('infocard', {})
    if infocard:
        imgs = infocard.get('image', [])
        if isinstance(imgs, str): imgs = [imgs]
        if imgs:
            img = imgs[0]
            return img if img.startswith('http') else f"{wp}asset/{img}"
    # 2. First gallery image
    gallery = page_data.get('gallery', [])
    if gallery:
        img = gallery[0]
        return img if img.startswith('http') else f"{wp}asset/{img}"
    # 3. keyword icon
    icon = (page_data.get('keyword') or {}).get('icon','')
    if icon:
        return icon if icon.startswith('http') else f"{wp}asset/{icon}"
    return ''

# ─── Nav helpers ─────────────────────────────────────────────────────────────

def _resolve_nav(raw_nav: list, wp: str, rp: str) -> list:
    result = []
    for item in raw_nav:
        lnk = item.get('link','')
        if lnk == 'index.html':
            url = rp + 'index.html'
        elif lnk.startswith('wiki/'):
            url = wp + lnk[5:]
        else:
            url = wp + lnk
        result.append({'name': item['name'], 'url': url})
    return result

def _resolve_nav_root(raw_nav: list) -> list:
    return [{'name': i['name'], 'url': i.get('link','')} for i in raw_nav]

# ─── Page list helpers ────────────────────────────────────────────────────────

def _pages_meta(pages: dict) -> list:
    result = []
    for key, data in sorted(pages.items()):
        kw = data.get('keyword', {})
        icon = kw.get('icon','')
        if icon.startswith('http'): icon = ''
        result.append({
            'key': key,
            'name': kw.get('name') or data.get('title') or key.split('/')[-1].replace('-',' ').title(),
            'color': kw.get('color','#6b7080'),
            'icon': icon,
            'excerpt': data.get('_excerpt',''),
        })
    return result

def _card_list(pages_dict: dict, url_fn) -> list:
    result = []
    for key, data in sorted(pages_dict.items()):
        kw = data.get('keyword',{})
        icon = kw.get('icon','')
        if icon.startswith('http'): icon = ''
        result.append({
            'url':     url_fn(key),
            'name':    kw.get('name') or data.get('title') or key.split('/')[-1].replace('-',' ').title(),
            'color':   kw.get('color','#6b7080'),
            'icon':    icon,
            'excerpt': data.get('_excerpt',''),
            'is_folder': data.get('_is_folder', False),
        })
    return result

def _build_breadcrumbs(key: str, wp: str, rp: str, is_folder=False) -> list:
    parts = key.split('/')
    crumbs = [{'name': 'Home', 'url': rp + 'index.html'}]
    # Intermediate folder segments
    for i in range(len(parts)-1):
        seg_key = '/'.join(parts[:i+1])
        seg_depth = _folder_depth(seg_key)
        seg_wp = _wpfx(seg_depth)
        crumbs.append({'name': parts[i].replace('-',' ').title(),
                        'url': f"{'../' * (len(parts)-i-1)}index.html" if is_folder or i < len(parts)-2
                               else '#'})
    crumbs.append({'name': parts[-1].replace('-',' ').title(), 'url': ''})
    return crumbs

# ─── Infocard keyword preprocessing ──────────────────────────────────────────

def _process_infocard_keywords(infocard: dict, pages: dict, depth: int) -> dict:
    from .parser import KEYWORD_PATTERN, parse_keyword_parts, resolve_keyword_html
    def proc(val):
        if isinstance(val, str):
            return KEYWORD_PATTERN.sub(
                lambda m: resolve_keyword_html(
                    *parse_keyword_parts(m.group(0)[2:-2]), pages, depth),
                val)
        if isinstance(val, list): return [proc(v) for v in val]
        if isinstance(val, dict): return {k: proc(v) for k,v in val.items()}
        return val
    return {k: proc(v) for k,v in infocard.items()}

# ─── Shared chrome template (header + sidebar + footer) ──────────────────────
# We use a single macro-style approach: CHROME_TEMPLATE is a reusable snippet.

_CARDS_MACRO = """
{% macro page_cards(items) %}
<div class="wiki-page-grid__items">
  {% for p in items %}
  <a class="wiki-page-card" href="{{ p.url }}" style="--card-color:{{ p.color }}">
    {% if p.icon %}
    <img class="wiki-page-card__icon" src="{{ asset_pfx }}asset/{{ p.icon }}" alt="">
    {% else %}
    <div class="wiki-page-card__icon wiki-page-card__icon--placeholder">
      {% if p.is_folder %}
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
      {% else %}
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      {% endif %}
    </div>
    {% endif %}
    <div class="wiki-page-card__body">
      <span class="wiki-page-card__name">{{ p.name }}</span>
      {% if p.excerpt %}<span class="wiki-page-card__excerpt">{{ p.excerpt }}</span>{% endif %}
    </div>
  </a>
  {% endfor %}
</div>
{% endmacro %}
"""

# ─── Shared header + sidebar + footer fragment ────────────────────────────────

def _chrome(site_title, logo, favicon, nav, wp, rp, active_url='',
            sidebar_extra='', page_accent=''):
    """Return (header_html, sidebar_html, footer_html) as a tuple."""
    # Header nav
    nav_links = ''
    for item in nav:
        active = ' style="color:var(--accent)"' if item['url'] == active_url else ''
        nav_links += f'<a class="wiki-header__nav-link" href="{item["url"]}"{active}>{item["name"]}</a>'

    logo_html = ''
    if logo:
        logo_html = f'<img src="{wp}asset/{logo}" alt="{site_title}" class="wiki-header__logo-img">'
    favicon_html = f'<link rel="icon" href="{wp}asset/{favicon}">' if favicon else ''

    sidebar_nav = ''
    for item in nav:
        active_cls = ' wiki-sidebar__link--active' if item['url'] == active_url else ''
        sidebar_nav += f'<a class="wiki-sidebar__link{active_cls}" href="{item["url"]}">{item["name"]}</a>'

    header = f"""
  <link rel="stylesheet" href="{wp}assets/style.css">
  {favicon_html}
</head>
<body>

<header class="wiki-header">
  <div class="wiki-header__inner">
    <a class="wiki-header__logo" href="{rp}index.html">
      {logo_html}
      <span class="wiki-header__title">{site_title}</span>
    </a>
    <div class="wiki-header__sep"></div>
    <div class="wiki-header__search">
      <div class="search-box">
        <input type="text" id="search-input" class="search-box__input" placeholder="Search wiki…" autocomplete="off">
        <button class="search-box__btn" onclick="wikiSearch.toggle()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </button>
        <div class="search-box__results" id="search-results"></div>
      </div>
    </div>
    <nav class="wiki-header__nav">
      {nav_links}
    </nav>
  </div>
</header>

<div class="wiki-layout">

<aside class="wiki-sidebar">
  <div class="wiki-sidebar__inner">
    <div class="wiki-sidebar__section">
      <span class="wiki-sidebar__section-title">Navigation</span>
      {sidebar_nav}
    </div>
    <div class="wiki-sidebar__section">
      <span class="wiki-sidebar__section-title">Wiki</span>
      <a class="wiki-sidebar__link" href="{rp}index.html">Home</a>
      <a class="wiki-sidebar__link" href="{wp}all-pages.html">All Pages</a>
    </div>
    {sidebar_extra}
  </div>
</aside>

<main class="wiki-main">"""

    footer = f"""
</main>
</div>

<footer class="wiki-footer">
  <div class="wiki-footer__inner">
    {site_title} &mdash; powered by <a href="https://github.com/wikifi/wikifi" target="_blank">wikifi</a>
  </div>
</footer>

<script>
  window.WIKI_ASSETS = {json.dumps(wp)};
</script>
<script src="{wp}assets/wiki.js"></script>
</body>
</html>"""

    return header, footer


# ─── Page render ─────────────────────────────────────────────────────────────

def render_page(page_data: dict, pages: dict, folders: dict, config: dict) -> str:
    from .parser import render_body_html

    site       = config.get('site', {})
    site_title = site.get('title', 'Wiki')
    raw_nav    = config.get('nav', [])
    page_key   = page_data.get('_path', '')

    d   = _depth(page_key)
    wp  = _wpfx(d)
    rp  = _rpfx(d)

    content_html = render_body_html(page_data.get('_raw_body',''), pages, d)

    infobox_html = ''
    if page_data.get('type') == 'infobox':
        infocard = _process_infocard_keywords(page_data.get('infocard',{}), pages, d)
        infobox_html = render_infobox(infocard, page_data, wp)

    gallery_html = render_gallery(page_data.get('gallery',[]), wp)

    hero_img = _hero_img_src(page_data, wp)
    kw       = page_data.get('keyword', {})
    kw_color = kw.get('color','')
    kw_icon  = kw.get('icon','')
    title    = page_data.get('title') or page_key.split('/')[-1].replace('-',' ').title()

    nav = _resolve_nav(raw_nav, wp, rp)

    # Breadcrumbs
    bc_parts = page_key.split('/')
    breadcrumbs = [{'name':'Home','url': rp+'index.html'}]
    for i, seg in enumerate(bc_parts[:-1]):
        seg_key = '/'.join(bc_parts[:i+1])
        levels_up = len(bc_parts) - i - 1
        breadcrumbs.append({'name': seg.replace('-',' ').title(),
                             'url': '../'*levels_up + 'index.html'})
    breadcrumbs.append({'name': bc_parts[-1].replace('-',' ').title(), 'url':''})

    logo    = site.get('logo','').removeprefix('asset/')
    favicon = site.get('favicon','').removeprefix('asset/')

    header, footer = _chrome(site_title, logo, favicon, nav, wp, rp)

    # Hero section
    if hero_img:
        hero_bg_style = f'style="--hero-img:url({json.dumps(hero_img)})"'
        hero_cls = 'wiki-page-hero'
    else:
        hero_bg_style = ''
        hero_cls = 'wiki-page-hero wiki-page-hero--no-image'

    # Icon in title
    if kw_icon:
        icon_src = kw_icon if kw_icon.startswith('http') else f"{wp}asset/{kw_icon}"
        icon_html = f'<img class="wiki-page-title__icon" src="{icon_src}" alt="">'
    else:
        icon_html = ''

    bc_html = ''
    for crumb in breadcrumbs:
        if crumb['url']:
            bc_html += f'<a class="wiki-breadcrumb__item" href="{crumb["url"]}">{crumb["name"]}</a><span class="wiki-breadcrumb__sep">/</span>'
        else:
            bc_html += f'<span class="wiki-breadcrumb__item wiki-breadcrumb__item--active">{crumb["name"]}</span>'

    accent_style = f'style="--page-accent:{kw_color}"' if kw_color else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} &ndash; {site_title}</title>
  <meta name="description" content="{page_data.get('_excerpt','')[:160]}">
{header}

  <div class="{hero_cls}" {hero_bg_style}>
    {'<div class="wiki-page-hero__bg"></div>' if hero_img else ''}
    <div class="wiki-page-hero__content">
      <nav class="wiki-breadcrumb">{bc_html}</nav>
      <h1 class="wiki-page-title" {accent_style}>
        {icon_html}
        <span>
          {title}
          <span class="wiki-page-title__accent"></span>
        </span>
      </h1>
    </div>
  </div>

  <div class="wiki-main__inner">
    {infobox_html}
    {gallery_html}
    <div class="wiki-content">
      {content_html}
    </div>
  </div>

{footer}"""


# ─── Folder page render ───────────────────────────────────────────────────────

def render_folder_page(folder_data: dict, child_pages: dict, child_folders: dict,
                       all_pages: dict, config: dict) -> str:
    from .parser import render_body_html

    site       = config.get('site', {})
    site_title = site.get('title', 'Wiki')
    raw_nav    = config.get('nav', [])
    fkey       = folder_data.get('_path', '')

    d   = _folder_depth(fkey)    # wiki/chars/index.html → depth 1
    wp  = _wpfx(d)               # back to wiki/
    rp  = _rpfx(d)               # back to project root

    title   = folder_data.get('title') or fkey.split('/')[-1].replace('-',' ').title()
    kw      = folder_data.get('keyword', {})
    kw_color= kw.get('color','')
    kw_icon = kw.get('icon','')

    nav  = _resolve_nav(raw_nav, wp, rp)
    logo    = site.get('logo','').removeprefix('asset/')
    favicon = site.get('favicon','').removeprefix('asset/')
    header, footer = _chrome(site_title, logo, favicon, nav, wp, rp)

    # Body content from .root.md
    body_html = ''
    raw = folder_data.get('_raw_body','').strip()
    if raw:
        body_html = f'<div class="wiki-content wiki-folder-desc">{render_body_html(raw, all_pages, d)}</div>'

    # Hero
    hero_img = _hero_img_src(folder_data, wp)
    if hero_img:
        hero_bg_style = f'style="--hero-img:url({json.dumps(hero_img)})"'
        hero_cls = 'wiki-page-hero'
    else:
        hero_bg_style = ''
        hero_cls = 'wiki-page-hero wiki-page-hero--no-image'

    if kw_icon:
        icon_src = kw_icon if kw_icon.startswith('http') else f"{wp}asset/{kw_icon}"
        icon_html = f'<img class="wiki-page-title__icon" src="{icon_src}" alt="">'
    else:
        icon_html = f'''<div class="wiki-page-title__icon" style="width:36px;height:36px;display:flex;align-items:center;justify-content:center;color:var(--text-faint)">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg></div>'''

    # Breadcrumbs for folder page
    bc_parts = fkey.split('/')
    bc_html = f'<a class="wiki-breadcrumb__item" href="{rp}index.html">Home</a>'
    for i, seg in enumerate(bc_parts[:-1]):
        seg_key = '/'.join(bc_parts[:i+1])
        levels_up = len(bc_parts) - i - 1
        bc_html += f'<span class="wiki-breadcrumb__sep">/</span>'
        bc_html += f'<a class="wiki-breadcrumb__item" href="{"../"*levels_up}index.html">{seg.replace("-"," ").title()}</a>'
    bc_html += f'<span class="wiki-breadcrumb__sep">/</span>'
    bc_html += f'<span class="wiki-breadcrumb__item wiki-breadcrumb__item--active">{bc_parts[-1].replace("-"," ").title()}</span>'

    accent_style = f'style="--page-accent:{kw_color}"' if kw_color else ''

    # Cards for sub-folders first, then child pages
    def folder_url(k):
        depth_diff = len(k.split('/')) - len(fkey.split('/'))
        return '../' * (d - depth_diff - 1) + k.split('/')[-1] + '/index.html' if depth_diff == 0 else f"../{k.split('/')[-1]}/index.html"

    def page_url(k):
        return k.split('/')[-1] + '.html'

    folder_cards = _card_list(child_folders, lambda k: k.split('/')[-1] + '/index.html')
    page_cards   = _card_list(child_pages,   lambda k: k.split('/')[-1] + '.html')
    all_cards    = folder_cards + page_cards

    cards_html = ''
    if all_cards:
        items_html = ''
        for p in all_cards:
            icon_part = ''
            if p['icon']:
                icon_part = f'<img class="wiki-page-card__icon" src="{wp}asset/{p["icon"]}" alt="">'
            else:
                if p['is_folder']:
                    icon_svg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>'
                else:
                    icon_svg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>'
                icon_part = f'<div class="wiki-page-card__icon wiki-page-card__icon--placeholder">{icon_svg}</div>'
            excerpt_part = f'<span class="wiki-page-card__excerpt">{p["excerpt"]}</span>' if p['excerpt'] else ''
            items_html += f'''<a class="wiki-page-card" href="{p['url']}" style="--card-color:{p['color']}">
                {icon_part}
                <div class="wiki-page-card__body">
                  <span class="wiki-page-card__name">{p["name"]}</span>
                  {excerpt_part}
                </div>
              </a>'''

        cards_html = f'''<div class="wiki-folder-index">
          <div class="wiki-page-grid__title">Contents — {len(all_cards)} item{"s" if len(all_cards)!=1 else ""}</div>
          <div class="wiki-page-grid__items">{items_html}</div>
        </div>'''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} &ndash; {site_title}</title>
  <meta name="description" content="{folder_data.get('_excerpt','')[:160]}">
{header}

  <div class="{hero_cls}" {hero_bg_style}>
    {'<div class="wiki-page-hero__bg"></div>' if hero_img else ''}
    <div class="wiki-page-hero__content">
      <nav class="wiki-breadcrumb">{bc_html}</nav>
      <h1 class="wiki-page-title" {accent_style}>
        {icon_html}
        <span>
          {title}
          <span class="wiki-page-title__accent"></span>
        </span>
      </h1>
    </div>
  </div>

  <div class="wiki-main__inner">
    {body_html}
    {cards_html}
  </div>

{footer}"""


# ─── Index ────────────────────────────────────────────────────────────────────

def render_index(pages: dict, folders: dict, config: dict) -> str:
    from .parser import render_body_html

    site           = config.get('site', {})
    site_title     = site.get('title', 'Wiki')
    site_desc      = site.get('description', '')
    logo           = site.get('logo','').removeprefix('asset/')
    favicon        = site.get('favicon','').removeprefix('asset/')
    hero_bg_raw    = site.get('hero_bg','').removeprefix('asset/')
    raw_nav        = config.get('nav', [])
    home_path      = site.get('home','')

    nav = _resolve_nav_root(raw_nav)
    favicon_html = f'<link rel="icon" href="wiki/asset/{favicon}">' if favicon else ''
    nav_links = ''.join(f'<a class="wiki-header__nav-link" href="{i["url"]}">{i["name"]}</a>' for i in nav)
    sidebar_nav = ''.join(f'<a class="wiki-sidebar__link" href="{i["url"]}">{i["name"]}</a>' for i in nav)
    logo_html = f'<img src="wiki/asset/{logo}" alt="{site_title}" class="wiki-header__logo-img">' if logo else ''

    home_content = ''
    if home_path:
        hk = home_path.replace('data/','').replace('/content','').strip('/')
        hd = pages.get(hk)
        if hd:
            home_content = f'<div class="wiki-home-content wiki-content">{render_body_html(hd.get("_raw_body",""), pages, -1)}</div>'

    hero_bg_style = f'style="--hero-bg:url(\'wiki/asset/{hero_bg_raw}\')"' if hero_bg_raw else ''

    # Cards: top-level folders first, then top-level pages
    top_folders = {k:v for k,v in folders.items() if '/' not in k}
    top_pages   = {k:v for k,v in pages.items()   if '/' not in k}

    def mk_card(url, kw, data, is_folder=False):
        icon = kw.get('icon','')
        if icon.startswith('http'): icon = ''
        name    = kw.get('name') or data.get('title') or url
        color   = kw.get('color','#6b7080')
        excerpt = data.get('_excerpt','')
        if icon:
            icon_html = f'<img class="wiki-page-card__icon" src="wiki/asset/{icon}" alt="">'
        else:
            svg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>' if is_folder else '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>'
            icon_html = f'<div class="wiki-page-card__icon wiki-page-card__icon--placeholder">{svg}</div>'
        excerpt_html = f'<span class="wiki-page-card__excerpt">{excerpt}</span>' if excerpt else ''
        return f'<a class="wiki-page-card" href="{url}" style="--card-color:{color}">{icon_html}<div class="wiki-page-card__body"><span class="wiki-page-card__name">{name}</span>{excerpt_html}</div></a>'

    cards_html = ''
    for k,v in sorted(top_folders.items()):
        cards_html += mk_card(f'wiki/{k}/index.html', v.get('keyword',{}), v, True)
    for k,v in sorted(top_pages.items()):
        cards_html += mk_card(f'wiki/{k}.html', v.get('keyword',{}), v, False)
    # also show all non-top-level pages & folders in the grid
    for k,v in sorted(pages.items()):
        if '/' in k:
            cards_html += mk_card(f'wiki/{k}.html', v.get('keyword',{}), v, False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{site_title}</title>
  <link rel="stylesheet" href="wiki/assets/style.css">
  {favicon_html}
</head>
<body>

<header class="wiki-header">
  <div class="wiki-header__inner">
    <a class="wiki-header__logo" href="index.html">
      {logo_html}
      <span class="wiki-header__title">{site_title}</span>
    </a>
    <div class="wiki-header__sep"></div>
    <div class="wiki-header__search">
      <div class="search-box">
        <input type="text" id="search-input" class="search-box__input" placeholder="Search wiki…" autocomplete="off">
        <button class="search-box__btn" onclick="wikiSearch.toggle()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </button>
        <div class="search-box__results" id="search-results"></div>
      </div>
    </div>
    <nav class="wiki-header__nav">{nav_links}</nav>
  </div>
</header>

<div class="wiki-hero" {hero_bg_style}>
  <div class="wiki-hero__inner">
    {'<img src="wiki/asset/'+logo+'" alt="" class="wiki-hero__logo">' if logo else ''}
    <h1 class="wiki-hero__title">{site_title}</h1>
    <span class="wiki-hero__title-accent"></span>
    {'<p class="wiki-hero__desc">'+site_desc+'</p>' if site_desc else ''}
    <div class="wiki-hero__search">
      <div class="search-box search-box--hero">
        <input type="text" id="hero-search" class="search-box__input" placeholder="Search…" autocomplete="off">
        <button class="search-box__btn">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </button>
        <div class="search-box__results" id="hero-search-results"></div>
      </div>
    </div>
  </div>
</div>

<div class="wiki-index-body">
  <div class="wiki-index-body__inner">
    {home_content}
    <section>
      <div class="wiki-page-grid__title">All Pages</div>
      <div class="wiki-page-grid__items">
        {cards_html}
      </div>
    </section>
  </div>
</div>

<footer class="wiki-footer">
  <div class="wiki-footer__inner">
    {site_title} &mdash; powered by <a href="https://github.com/wikifi/wikifi" target="_blank">wikifi</a>
  </div>
</footer>

<script>
  window.WIKI_ASSETS = "wiki/";
  window.WIKI_IS_HOME = true;
</script>
<script src="wiki/assets/wiki.js"></script>
</body>
</html>"""


# ─── All-pages ────────────────────────────────────────────────────────────────

def render_all_pages(pages: dict, folders: dict, config: dict) -> str:
    site       = config.get('site', {})
    site_title = site.get('title', 'Wiki')
    raw_nav    = config.get('nav', [])
    logo       = site.get('logo','').removeprefix('asset/')
    favicon    = site.get('favicon','').removeprefix('asset/')

    # all-pages.html sits at wiki/all-pages.html → depth 0
    wp = ''
    rp = '../'
    nav = _resolve_nav(raw_nav, wp, rp)
    header, footer = _chrome(site_title, logo, favicon, nav, wp, rp)

    items_html = ''
    # folders first
    for k, v in sorted(folders.items()):
        kw = v.get('keyword',{})
        icon = kw.get('icon','')
        if icon.startswith('http'): icon = ''
        name = kw.get('name') or v.get('title') or k.split('/')[-1].title()
        color = kw.get('color','#6b7080')
        excerpt = v.get('_excerpt','')
        icon_html = f'<img class="wiki-page-card__icon" src="asset/{icon}" alt="">' if icon else '<div class="wiki-page-card__icon wiki-page-card__icon--placeholder"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg></div>'
        items_html += f'<a class="wiki-page-card" href="{k}/index.html" style="--card-color:{color}">{icon_html}<div class="wiki-page-card__body"><span class="wiki-page-card__name">{name}</span>{"<span class=wiki-page-card__excerpt>"+excerpt+"</span>" if excerpt else ""}</div></a>'

    for k, v in sorted(pages.items()):
        kw = v.get('keyword',{})
        icon = kw.get('icon','')
        if icon.startswith('http'): icon = ''
        name = kw.get('name') or v.get('title') or k.split('/')[-1].title()
        color = kw.get('color','#6b7080')
        excerpt = v.get('_excerpt','')
        icon_html = f'<img class="wiki-page-card__icon" src="asset/{icon}" alt="">' if icon else '<div class="wiki-page-card__icon wiki-page-card__icon--placeholder"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>'
        items_html += f'<a class="wiki-page-card" href="{k}.html" style="--card-color:{color}">{icon_html}<div class="wiki-page-card__body"><span class="wiki-page-card__name">{name}</span>{"<span class=wiki-page-card__excerpt>"+excerpt+"</span>" if excerpt else ""}</div></a>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>All Pages &ndash; {site_title}</title>
{header}

  <div class="wiki-page-hero wiki-page-hero--no-image">
    <div class="wiki-page-hero__content">
      <nav class="wiki-breadcrumb">
        <a class="wiki-breadcrumb__item" href="../index.html">Home</a>
        <span class="wiki-breadcrumb__sep">/</span>
        <span class="wiki-breadcrumb__item wiki-breadcrumb__item--active">All Pages</span>
      </nav>
      <h1 class="wiki-page-title"><span>All Pages<span class="wiki-page-title__accent"></span></span></h1>
    </div>
  </div>

  <div class="wiki-main__inner">
    <div class="wiki-page-grid__items">
      {items_html}
    </div>
  </div>

{footer}"""
