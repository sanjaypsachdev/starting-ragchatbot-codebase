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
