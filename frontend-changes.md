# Frontend Changes

## Code Quality Tooling

### Tools Added

**Prettier** — automatic formatter for JS, CSS, and HTML.
**ESLint** — static analysis and linting for JavaScript.

### New Files

| File | Purpose |
|------|---------|
| `frontend/package.json` | npm package with `prettier` and `eslint` as devDependencies; defines `format`, `format:check`, `lint`, and `quality` scripts |
| `frontend/.prettierrc` | Prettier config: 2-space indent, double quotes, trailing commas, 80-char print width |
| `frontend/eslint.config.js` | ESLint flat config: `eslint:recommended` + browser globals + `no-unused-vars` warning |
| `scripts/check-frontend.sh` | Runs `format:check` then `lint`; exits non-zero on any violation |
| `scripts/format-frontend.sh` | Runs `format` to auto-fix all JS/CSS/HTML files in `frontend/` |

### Reformatted Files

`frontend/script.js`, `frontend/style.css`, and `frontend/index.html` were reformatted to match Prettier's output:

- Indentation changed from 4 spaces to 2 spaces throughout
- JavaScript string literals changed to double quotes
- Trailing commas added in multi-line JS structures
- CSS selector groups and `@keyframes` stops each placed on their own line
- HTML attributes each on their own line for long elements

### Usage

```bash
# Install dependencies (first time only)
cd frontend && npm install

# Check formatting and linting without making changes
./scripts/check-frontend.sh

# Auto-format all frontend files
./scripts/format-frontend.sh

# Run individual npm scripts from the frontend directory
npm run format        # auto-format
npm run format:check  # check only (CI-safe)
npm run lint          # ESLint only
npm run quality       # format:check + lint combined
```

---

## Dark/Light Theme Toggle

### Summary

Added a dark/light theme toggle button to the RAG chatbot UI, allowing users to switch between the existing dark theme and a new light theme. The selected theme persists across page reloads via `localStorage`.

### Files Modified

#### `frontend/index.html`

- Added a `<button id="themeToggle" class="theme-toggle">` element just before the closing `</body>` tag (above the script tags).
- The button contains two inline SVG icons: a **moon** (shown in dark mode) and a **sun** (shown in light mode). Visibility is controlled by CSS.
- The button has `aria-label="Toggle theme"` and `title="Toggle dark/light theme"` for accessibility.

#### `frontend/style.css`

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

**Theme toggle button styles** (`.theme-toggle`):
- Fixed position, `top: 1rem; right: 1rem; z-index: 1000`
- 44×44 px circle with `border-radius: 50%`
- Uses `--surface`, `--border-color`, and `--shadow` variables so it adapts to the active theme

**Icon switching** — CSS rules show `.icon-moon` in dark mode and `.icon-sun` in light mode:
```css
[data-theme="light"] .theme-toggle .icon-sun  { display: block; }
[data-theme="light"] .theme-toggle .icon-moon { display: none; }
```

#### `frontend/script.js`

Added two functions and one event listener:

**`initTheme()`** — called on `DOMContentLoaded`, reads `localStorage.getItem('theme')` and applies `data-theme="light"` to `document.body` if the saved value is `'light'`. Default (no saved value) stays dark.

**`toggleTheme()`** — reads the current `data-theme` attribute on `body`. If `'light'`, removes the attribute (back to dark) and saves `'dark'` to `localStorage`. Otherwise, sets `data-theme="light"` and saves `'light'`.

**Event listener** — wired in `setupEventListeners()`:
```js
document.getElementById("themeToggle").addEventListener("click", toggleTheme);
```

### Design Decisions

- **`data-theme` on `body`** — the standard approach; CSS variable overrides cascade naturally from there.
- **CSS variables only** — no class toggling or JS color manipulation; all color logic stays in CSS.
- **`localStorage` persistence** — theme choice survives page reloads and browser restarts without a backend.
- **Icon strategy** — both SVG icons are always in the DOM; CSS `display` switches which one is visible. This avoids any JS DOM manipulation for the icon and keeps the toggle instant.
- **Accessible** — `aria-label`, keyboard focus ring, and semantic `<button>` element ensure screen-reader and keyboard compatibility.
