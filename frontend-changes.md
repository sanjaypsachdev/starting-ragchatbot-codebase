# Frontend Changes: Dark/Light Theme Toggle

## Summary

Added a dark/light theme toggle button to the RAG chatbot UI, allowing users to switch between the existing dark theme and a new light theme. The selected theme persists across page reloads via `localStorage`.

---

## Files Modified

### `frontend/index.html`

- Added a `<button id="themeToggle" class="theme-toggle">` element just before the closing `</body>` tag (above the script tags).
- The button contains two inline SVG icons: a **moon** (shown in dark mode) and a **sun** (shown in light mode). Visibility is controlled by CSS.
- The button has `aria-label="Toggle theme"` and `title="Toggle dark/light theme"` for accessibility.

### `frontend/style.css`

**Light theme variables** — added a `[data-theme="light"]` block with:
| Variable | Dark (default) | Light |
|---|---|---|
| `--background` | `#0f172a` | `#f8fafc` |
| `--surface` | `#1e293b` | `#ffffff` |
| `--surface-hover` | `#334155` | `#f1f5f9` |
| `--text-primary` | `#f1f5f9` | `#0f172a` |
| `--text-secondary` | `#94a3b8` | `#64748b` |
| `--border-color` | `#334155` | `#e2e8f0` |
| `--shadow` | `rgba(0,0,0,0.3)` | `rgba(0,0,0,0.1)` |
| `--welcome-bg` | `#1e3a5f` | `#eff6ff` |

Primary/focus-ring colors remain the same in both themes for brand consistency.

**Body transition** — added `transition: background-color 0.3s ease, color 0.3s ease` to `body` so theme switches animate smoothly.

**Smooth transitions** — added `transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease` to the sidebar, chat surfaces, input, message bubbles, and other themed elements.

**Theme toggle button styles** (`.theme-toggle`):
- Fixed position, `top: 1rem; right: 1rem; z-index: 1000`
- 44×44 px circle with `border-radius: 50%`
- Uses `--surface`, `--border-color`, and `--shadow` variables so it adapts to the active theme
- Hover: primary-color border, slight upward translate, blue glow
- Focus: `box-shadow: 0 0 0 3px var(--focus-ring)` (keyboard accessible)
- Active: returns to baseline (no translate)

**Icon switching** — CSS rules show `.icon-moon` in dark mode and `.icon-sun` in light mode:
```css
[data-theme="light"] .theme-toggle .icon-sun  { display: block; }
[data-theme="light"] .theme-toggle .icon-moon { display: none; }
```

### `frontend/script.js`

Added two functions and one event listener:

**`initTheme()`** — called on `DOMContentLoaded`, reads `localStorage.getItem('theme')` and applies `data-theme="light"` to `document.body` if the saved value is `'light'`. Default (no saved value) stays dark.

**`toggleTheme()`** — reads the current `data-theme` attribute on `body`. If `'light'`, removes the attribute (back to dark) and saves `'dark'` to `localStorage`. Otherwise, sets `data-theme="light"` and saves `'light'`.

**Event listener** — wired in `setupEventListeners()`:
```js
document.getElementById('themeToggle').addEventListener('click', toggleTheme);
```

---

## Design Decisions

- **`data-theme` on `body`** — the standard approach; CSS variable overrides cascade naturally from there.
- **CSS variables only** — no class toggling or JS color manipulation; all color logic stays in CSS.
- **`localStorage` persistence** — theme choice survives page reloads and browser restarts without a backend.
- **Icon strategy** — both SVG icons are always in the DOM; CSS `display` switches which one is visible. This avoids any JS DOM manipulation for the icon and keeps the toggle instant.
- **Accessible** — `aria-label`, keyboard focus ring, and semantic `<button>` element ensure screen-reader and keyboard compatibility.
