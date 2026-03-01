#!/usr/bin/env python3
"""
wikifi - Static Wiki Generator
Generates a Wikipedia/Fandom-style static wiki from markdown files.
"""

import argparse
import sys
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog='wikifi',
        description='wikifi - Static Wiki Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python wikifi.py ./my-wiki          Build wiki from project folder
  python wikifi.py ./my-wiki --serve  Build and serve locally on port 8080
  python wikifi.py ./my-wiki --port 3000 --serve

Project folder structure:
  /config.json        Site configuration
  /data/*/content.md  Wiki page content
  /asset/             Static assets (images, etc.)
        """
    )
    parser.add_argument(
        'project',
        nargs='?',
        default='.',
        help='Path to the wiki project folder (default: current directory)'
    )
    parser.add_argument(
        '--serve',
        action='store_true',
        help='Serve the wiki locally after building'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Port for local server (default: 8080)'
    )
    parser.add_argument(
        '--no-build',
        action='store_true',
        help='Only serve, do not rebuild (requires existing build)'
    )

    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    if not project_path.exists():
        print(f"Error: Project folder '{project_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if not args.no_build:
        try:
            from wikifi.generator import WikiGenerator
            gen = WikiGenerator(project_path)
            gen.build()
        except Exception as e:
            print(f"Build failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)

    if args.serve:
        import http.server
        import socketserver
        import threading
        import webbrowser

        os.chdir(project_path)

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *fargs):
                pass  # Suppress default logging

        print(f"\n  Serving wiki at http://localhost:{args.port}")
        print(f"  Press Ctrl+C to stop\n")

        with socketserver.TCPServer(("", args.port), Handler) as httpd:
            try:
                webbrowser.open(f"http://localhost:{args.port}")
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped.")


if __name__ == '__main__':
    main()
