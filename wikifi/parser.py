"""
wikifi/parser.py
Parses wiki markdown content files, extracting YAML frontmatter,
resolving [[keyword]] syntax, and converting to HTML.
"""

import re
import yaml
import markdown
from pathlib import Path
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension


# ─── Frontmatter ──────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Extract YAML frontmatter block from the top of a markdown file.
    Returns (meta_dict, body_text).
    """
    pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = pattern.match(text)
    if match:
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as e:
            print(f"  Warning: YAML parse error: {e}")
            meta = {}
        body = text[match.end():]
        return meta, body
    return {}, text


# ─── Keyword Extension ─────────────────────────────────────────────────────────

KEYWORD_PATTERN = re.compile(
    r'\[\[([^\]|]+?)(?:\|([^\]]*))?\]\]'
)

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}


def parse_keyword_parts(raw: str) -> tuple[str, dict]:
    """
    Parse [[path/to/content|color:#EEE|icon:path.png|name:New Name]]
    Returns (path, overrides_dict)
    """
    parts = raw.split('|')
    path = parts[0].strip()
    overrides = {}
    for part in parts[1:]:
        if ':' in part:
            key, _, val = part.partition(':')
            overrides[key.strip()] = val.strip()
    return path, overrides


def is_image_path(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def resolve_keyword_html(path: str, overrides: dict, pages: dict, depth: int = 0) -> str:
    """
    Convert a [[keyword]] into HTML.
    - If path is an image → render <img>
    - Otherwise → render a styled link chip
    """
    # Image embed
    if is_image_path(path):
        # Resolve asset path relative to wiki root
        img_src = _asset_url(path, depth)
        return f'<img class="wiki-inline-img" src="{img_src}" alt="{Path(path).name}">'

    # Page link
    page_data = pages.get(path) or pages.get(path.rstrip('/'))
    keyword_meta = {}
    if page_data:
        keyword_meta = page_data.get('keyword') or {}

    name    = overrides.get('name')  or keyword_meta.get('name')  or path.split('/')[-1].replace('-', ' ').title()
    color   = overrides.get('color') or keyword_meta.get('color') or '#6c757d'
    icon    = overrides.get('icon')  or keyword_meta.get('icon')  or ''

    page_url = _page_url(path, depth)
    exists_class = 'wiki-kw' if page_data else 'wiki-kw wiki-kw--broken'

    icon_html = ''
    if icon:
        icon_src = icon if icon.startswith('http') else _asset_url(icon, depth)
        icon_html = f'<img class="wiki-kw__icon" src="{icon_src}" alt="">'

    return (
        f'<a href="{page_url}" class="{exists_class}" '
        f'style="--kw-color:{color}" title="{name}">'
        f'{icon_html}<span class="wiki-kw__label">{name}</span>'
        f'</a>'
    )


def _asset_url(path: str, depth: int) -> str:
    """Compute relative URL to a user asset from the current context.
    depth=-1  → index.html (root): assets at wiki/asset/
    depth=0   → wiki/page.html:    assets at asset/
    depth=1   → wiki/sub/page.html: assets at ../asset/
    """
    if depth < 0:
        return f"wiki/asset/{path}"
    prefix = '../' * depth
    return f"{prefix}asset/{path}"


def _page_url(path: str, depth: int) -> str:
    """Compute relative URL to a wiki page from the current context."""
    if depth < 0:
        return f"wiki/{path}.html"
    prefix = '../' * depth
    return f"{prefix}{path}.html"


# ─── Markdown processing ───────────────────────────────────────────────────────

class KeywordPreprocessor(Preprocessor):
    """Replaces [[keyword]] syntax before markdown processing."""

    def __init__(self, md, pages, depth):
        super().__init__(md)
        self.pages = pages
        self.depth = depth

    def run(self, lines):
        new_lines = []
        for line in lines:
            new_lines.append(self._replace_keywords(line))
        return new_lines

    def _replace_keywords(self, text):
        def replacer(m):
            path, overrides = parse_keyword_parts(m.group(0)[2:-2])
            return resolve_keyword_html(path, overrides, self.pages, self.depth)
        return KEYWORD_PATTERN.sub(replacer, text)


class KeywordExtension(Extension):
    def __init__(self, pages=None, depth=0):
        self.pages = pages or {}
        self.depth = depth
        super().__init__()

    def extendMarkdown(self, md):
        md.preprocessors.register(
            KeywordPreprocessor(md, self.pages, self.depth),
            'wiki_keywords',
            175  # Run before most other preprocessors
        )


# ─── Full page parse ───────────────────────────────────────────────────────────

def parse_page(filepath: Path) -> dict:
    """
    Parse a content.md file.
    Returns a dict with all frontmatter fields plus:
      _raw_body  - raw markdown body
      _excerpt   - plain-text excerpt (first ~200 chars)
    """
    text = filepath.read_text(encoding='utf-8')
    meta, body = parse_frontmatter(text)

    # Build excerpt — replace [[keywords]] with display names
    def _kw_name(m):
        inner = m.group(0)[2:-2]
        parts = inner.split('|')
        path = parts[0].strip()
        for part in parts[1:]:
            if part.strip().startswith('name:'):
                return part.strip()[5:]
        return path.split('/')[-1].replace('-', ' ').title()

    plain = re.sub(r'#.*?\n', '', body)
    plain = re.sub(r'\[\[.*?\]\]', _kw_name, plain)
    plain = re.sub(r'[*_`]+', '', plain).strip()
    plain = re.sub(r'\s+', ' ', plain).strip()
    excerpt = plain[:200].strip()
    if len(plain) > 200:
        excerpt += '…' 

    meta['_raw_body'] = body
    meta['_excerpt'] = excerpt

    # Normalise fields
    meta.setdefault('type', 'none')
    meta.setdefault('title', '')
    meta.setdefault('keyword', {})
    if isinstance(meta['keyword'], dict):
        meta['keyword'].setdefault('name', meta.get('title', ''))
        meta['keyword'].setdefault('color', '#6c757d')
        meta['keyword'].setdefault('icon', '')

    return meta


def render_body_html(raw_body: str, pages: dict, depth: int) -> str:
    """Convert raw markdown body to HTML, resolving keywords."""
    md = markdown.Markdown(
        extensions=[
            'extra',           # tables, fenced code, footnotes, etc.
            'toc',
            'nl2br',
            'sane_lists',
            KeywordExtension(pages=pages, depth=depth),
        ]
    )
    return md.convert(raw_body)
