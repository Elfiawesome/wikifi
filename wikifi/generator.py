"""
wikifi/generator.py
Main build orchestrator.
"""

import json
import shutil
from pathlib import Path


class WikiGenerator:
    def __init__(self, project_path: Path):
        self.root      = Path(project_path).resolve()
        self.data_dir  = self.root / 'data'
        self.asset_dir = self.root / 'asset'
        self.wiki_dir  = self.root / 'wiki'
        self.config    = self._load_config()
        self.pages:   dict = {}
        self.folders: dict = {}

    def _load_config(self) -> dict:
        config_path = self.root / 'config.json'
        if config_path.exists():
            with open(config_path, encoding='utf-8') as f:
                return json.load(f)
        print("  Warning: config.json not found, using defaults.")
        return {'site': {'title': 'My Wiki', 'description': ''}, 'nav': []}

    def build(self):
        print(f"\n  wikifi — building: {self.root}\n")
        self._reset_output()
        self._collect_pages()
        self._discover_folders()
        self._copy_wiki_assets()
        self._copy_user_assets()
        self._render_pages()
        self._render_folder_pages()
        self._render_all_pages()
        self._build_search_index()
        self._render_index()
        total   = len(self.pages)
        folders = len(self.folders)
        print(f"\n  Done  {total} page{'s' if total!=1 else ''}, "
              f"{folders} folder{'s' if folders!=1 else ''} generated.\n")

    def _reset_output(self):
        print("  Resetting output...")
        if self.wiki_dir.exists():
            shutil.rmtree(self.wiki_dir)
        self.wiki_dir.mkdir(parents=True)
        idx = self.root / 'index.html'
        if idx.exists():
            idx.unlink()

    def _collect_pages(self):
        print("  Collecting pages...")
        if not self.data_dir.exists():
            print("  Warning: /data directory not found.")
            return
        from .parser import parse_page
        for content_file in sorted(self.data_dir.rglob('content.md')):
            rel = content_file.parent.relative_to(self.data_dir)
            page_key = rel.as_posix()
            page_data = parse_page(content_file)
            page_data['_path'] = page_key
            self.pages[page_key] = page_data
            print(f"     page    {page_key}")

    def _discover_folders(self):
        print("  Discovering folders...")
        if not self.data_dir.exists():
            return
        from .parser import parse_page

        folder_keys = set()
        for page_key in self.pages:
            parts = page_key.split('/')
            for depth in range(1, len(parts)):
                folder_keys.add('/'.join(parts[:depth]))

        for root_file in sorted(self.data_dir.rglob('.root.md')):
            rel_dir = root_file.parent.relative_to(self.data_dir)
            if rel_dir.as_posix() != '.':
                folder_keys.add(rel_dir.as_posix())

        for fkey in sorted(folder_keys):
            root_md = self.data_dir / fkey / '.root.md'
            if root_md.exists():
                fd = parse_page(root_md)
                fd['_path'] = fkey
                fd['_is_folder'] = True
                print(f"     folder  {fkey}  (.root.md)")
            else:
                name = fkey.split('/')[-1].replace('-', ' ').title()
                fd = {
                    '_path': fkey, '_is_folder': True,
                    '_raw_body': '', '_excerpt': '',
                    'type': 'none', 'title': name,
                    'keyword': {'name': name, 'color': '#6b7080', 'icon': ''},
                }
                print(f"     folder  {fkey}")
            self.folders[fkey] = fd

    def _copy_wiki_assets(self):
        src = Path(__file__).parent / 'assets'
        dst = self.wiki_dir / 'assets'
        if src.exists():
            shutil.copytree(src, dst)

    def _copy_user_assets(self):
        if self.asset_dir.exists():
            shutil.copytree(self.asset_dir, self.wiki_dir / 'asset')
        else:
            (self.wiki_dir / 'asset').mkdir(exist_ok=True)

    def _render_pages(self):
        print("  Rendering pages...")
        from .renderer import render_page
        for page_key, page_data in self.pages.items():
            html = render_page(page_data, self.pages, self.folders, self.config)
            out_path = self.wiki_dir / f"{page_key}.html"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding='utf-8')

    def _render_folder_pages(self):
        print("  Rendering folder pages...")
        from .renderer import render_folder_page
        for fkey, fd in self.folders.items():
            child_pages = {
                k: v for k, v in self.pages.items()
                if k.startswith(fkey + '/') and '/' not in k[len(fkey)+1:]
            }
            child_folders = {
                k: v for k, v in self.folders.items()
                if k.startswith(fkey + '/') and '/' not in k[len(fkey)+1:]
            }
            html = render_folder_page(fd, child_pages, child_folders,
                                      self.pages, self.config)
            out_path = self.wiki_dir / fkey / 'index.html'
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding='utf-8')

    def _render_all_pages(self):
        from .renderer import render_all_pages
        html = render_all_pages(self.pages, self.folders, self.config)
        (self.wiki_dir / 'all-pages.html').write_text(html, encoding='utf-8')

    def _build_search_index(self):
        print("  Building search index...")
        index = []
        for page_key, page_data in self.pages.items():
            kw = page_data.get('keyword', {})
            index.append({
                'key': page_key, 'url': f'{page_key}.html',
                'title': page_data.get('title', ''),
                'name': kw.get('name') or page_data.get('title') or page_key.split('/')[-1],
                'color': kw.get('color', '#6b7080'),
                'icon': kw.get('icon', ''),
                'excerpt': page_data.get('_excerpt', ''),
                'type': 'page',
            })
        for fkey, fd in self.folders.items():
            kw = fd.get('keyword', {})
            index.append({
                'key': fkey, 'url': f'{fkey}/index.html',
                'title': fd.get('title', ''),
                'name': kw.get('name') or fd.get('title') or fkey.split('/')[-1].title(),
                'color': kw.get('color', '#6b7080'),
                'icon': kw.get('icon', ''),
                'excerpt': fd.get('_excerpt', ''),
                'type': 'folder',
            })
        self.wiki_dir.joinpath('search_index.json').write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
        self.wiki_dir.joinpath('pages.json').write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')

    def _render_index(self):
        print("  Rendering index.html...")
        from .renderer import render_index
        html = render_index(self.pages, self.folders, self.config)
        (self.root / 'index.html').write_text(html, encoding='utf-8')
