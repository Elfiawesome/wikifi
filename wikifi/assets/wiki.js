/**
 * wikifi/wiki.js
 * Client-side search, lightbox, and utilities for the generated wiki.
 */

(function () {
  'use strict';

  const ASSETS = window.WIKI_ASSETS || '';
  const IS_HOME = window.WIKI_IS_HOME || false;

  // ─── Search ─────────────────────────────────────────────────────────────────

  const wikiSearch = {
    index: null,
    loading: false,

    async loadIndex() {
      if (this.index || this.loading) return;
      this.loading = true;
      try {
        const res = await fetch(ASSETS + 'search_index.json');
        this.index = await res.json();
      } catch (e) {
        console.warn('wikifi: could not load search index', e);
        this.index = [];
      }
      this.loading = false;
    },

    query(term) {
      if (!this.index) return [];
      term = term.toLowerCase().trim();
      if (!term) return [];
      return this.index
        .filter(p => {
          const name = (p.name || '').toLowerCase();
          const title = (p.title || '').toLowerCase();
          const excerpt = (p.excerpt || '').toLowerCase();
          const key = (p.key || '').toLowerCase();
          return name.includes(term) || title.includes(term) ||
                 excerpt.includes(term) || key.includes(term);
        })
        .slice(0, 10);
    },

    renderResults(results, container) {
      container.innerHTML = '';
      if (!results.length) {
        container.innerHTML = '<div class="search-no-results">No results found</div>';
        return;
      }
      results.forEach(p => {
        const a = document.createElement('a');
        a.className = 'search-result';
        a.href = ASSETS + p.url;

        const iconHtml = p.icon
          ? `<img class="search-result__icon" src="${ASSETS}asset/${p.icon}" alt="" onerror="this.style.display='none'">`
          : `<div class="search-result__icon-placeholder">
               <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                 <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
               </svg>
             </div>`;

        const dot = p.color
          ? `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px;vertical-align:middle;flex-shrink:0"></span>`
          : '';

        a.innerHTML = `
          ${iconHtml}
          <div class="search-result__info">
            <span class="search-result__name">${dot}${escHtml(p.name || p.title)}</span>
            ${p.excerpt ? `<span class="search-result__excerpt">${escHtml(p.excerpt)}</span>` : ''}
          </div>
          <span class="search-result__path">${escHtml(p.key || '')}</span>
        `;
        container.appendChild(a);
      });
    },

    bindInput(inputEl, resultsEl) {
      if (!inputEl || !resultsEl) return;

      let debounce = null;

      inputEl.addEventListener('focus', () => {
        this.loadIndex();
      });

      inputEl.addEventListener('input', () => {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
          const term = inputEl.value;
          if (!term.trim()) {
            resultsEl.classList.remove('is-open');
            return;
          }
          const results = this.query(term);
          this.renderResults(results, resultsEl);
          resultsEl.classList.add('is-open');
        }, 140);
      });

      inputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          resultsEl.classList.remove('is-open');
          inputEl.blur();
        }
        if (e.key === 'Enter') {
          const first = resultsEl.querySelector('.search-result');
          if (first) first.click();
        }
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          const items = resultsEl.querySelectorAll('.search-result');
          if (items.length) items[0].focus();
        }
      });

      document.addEventListener('click', (e) => {
        if (!inputEl.contains(e.target) && !resultsEl.contains(e.target)) {
          resultsEl.classList.remove('is-open');
        }
      });
    },

    toggle() {
      const input = document.getElementById('search-input');
      if (input) input.focus();
    },

    focusHero() {
      const input = document.getElementById('hero-search');
      if (input) input.focus();
    }
  };

  window.wikiSearch = wikiSearch;

  // ─── Init search inputs ──────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', () => {
    // Header search
    const headerInput   = document.getElementById('search-input');
    const headerResults = document.getElementById('search-results');
    wikiSearch.bindInput(headerInput, headerResults);

    // Hero search
    const heroInput   = document.getElementById('hero-search');
    const heroResults = document.getElementById('hero-search-results');
    wikiSearch.bindInput(heroInput, heroResults);

    // Keyboard shortcut: / to focus search
    document.addEventListener('keydown', (e) => {
      if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        const input = document.getElementById('hero-search') || document.getElementById('search-input');
        if (input) input.focus();
      }
    });

    // ─── Gallery lightbox ──────────────────────────────────────────────────────

    const lightbox = document.createElement('div');
    lightbox.className = 'wiki-lightbox';
    const lightboxImg = document.createElement('img');
    lightbox.appendChild(lightboxImg);
    document.body.appendChild(lightbox);

    function openLightbox(src) {
      lightboxImg.src = src;
      lightbox.classList.add('is-open');
      document.body.style.overflow = 'hidden';
    }

    function closeLightbox() {
      lightbox.classList.remove('is-open');
      document.body.style.overflow = '';
    }

    lightbox.addEventListener('click', closeLightbox);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeLightbox();
    });

    // Bind gallery items
    document.querySelectorAll('.gallery__item img, .infobox__img').forEach(img => {
      img.style.cursor = 'zoom-in';
      img.addEventListener('click', () => openLightbox(img.src));
    });

    // Bind inline images in content
    document.querySelectorAll('.wiki-content img, .wiki-inline-img').forEach(img => {
      img.style.cursor = 'zoom-in';
      img.addEventListener('click', () => openLightbox(img.src));
    });

    // ─── Active sidebar link ───────────────────────────────────────────────────

    const currentPath = location.pathname;
    document.querySelectorAll('.wiki-sidebar__link').forEach(link => {
      if (link.href && currentPath.endsWith(link.getAttribute('href'))) {
        link.classList.add('wiki-sidebar__link--active');
      }
    });

    // ─── Table of contents toggle (optional enhancement) ──────────────────────

    // Add smooth hover effects on keyword chips
    document.querySelectorAll('.wiki-kw').forEach(kw => {
      kw.addEventListener('mouseenter', () => {
        kw.style.transition = 'all .15s';
      });
    });
  });


  // ─── Utility ────────────────────────────────────────────────────────────────

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

})();
