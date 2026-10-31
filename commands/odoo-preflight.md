---
name: odoo-preflight
description: Lint the current Odoo module for v19 breaking changes and list fixes
---

# Odoo preflight

1. Find the nearest folder containing __manifest__.py from the open file or the workspace root. If several exist, ask which one.
2. Read the module's .py, .xml and .csv files (skip static/) and call odoo_v19_lint with `files` as a JSON object of relative path to content.
3. Group findings by check id. For each, show file:line, the code, and the fix.
4. Mark likely false positives (for example form view <group string=...>) and say why.
5. Ask whether to apply the fixes. If yes, apply them and run the lint again.
6. Finish with the live install command from the odoo-v19-preflight skill.
