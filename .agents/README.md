# Antigravity workspace skills

Installed once in .agents/skills/<name>/SKILL.md, the documented workspace path.
After pulling, open the repository root and start a new conversation/reload the
workspace so discovery sees them. This is not a global installation on your PC.

| Skill | Source | When |
|---|---|---|
| frontend-design | Anthropic, pinned upstream | Visual direction and implementation |
| luxury-editorial-ui | Project-authored | Luxury Thai/English editorial execution |
| web-design-guidelines | Vercel, pinned upstream | Accessibility/UX review, NOT Vercel hosting |
| registry-pages | Project-authored | Data boundary and same-repo Pages publishing |

Read DESIGN.md and registry-pages first, then frontend-design/luxury-editorial-ui
for construction, web-design-guidelines for final review of web/src/ and web/index.html.
Load only what is relevant to the current step. Upstream WebFetch means the
available equivalent browsing tool; do not install another plugin for that name.
The project brief and explicit user choices override generic upstream defaults.

skills-lock.json records sources, revisions and checksums. Anthropic's skill keeps
its Apache-2.0 LICENSE.txt; Vercel declares MIT in its pinned README (see NOTICE).
Project-authored skills use the repository license. No third-party executable
scripts, install hooks, CLI installers or extra packages are included.
File checks do not prove automatic activation inside the owner's IDE.

Sources:
https://antigravity.google/docs/skills
https://github.com/anthropics/skills/tree/main/skills/frontend-design
https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines
