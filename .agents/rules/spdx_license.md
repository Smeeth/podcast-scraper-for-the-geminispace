<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# Rule: Mandatory SPDX License Headers

Every source code file, script, and configuration file in this repository must start with the valid SPDX GPL-3.0 header.

## Header Format

For Python, Bash, Dockerfile, TOML, INI, YAML:

```python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors
```

For JavaScript, CSS:

```javascript
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Podcast & Media Channel Researcher Contributors
```

For HTML, Markdown:

```markdown
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->
```

## Validation

Always verify compliance using:

```bash
python .github/scripts/verify_spdx_headers.py
```
