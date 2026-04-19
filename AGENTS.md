# Repository Guidelines

## Project Structure & Module Organization
`custom_components/yunmao/` contains the full Home Assistant integration. Use `__init__.py` for config-entry setup, `config_flow.py` for onboarding and device registration, `light.py` and `cover.py` for entity behavior, and `yunmao_data.py` for polling and TCP server state. Keep shared constants in `const.py`. Integration metadata and UI text live in `manifest.json`, `strings.json`, and `translations/en.json`. The repo root only holds support files such as `hacs.json`, `README.md`, and `LICENSE`.

## Build, Test, and Development Commands
There is no dedicated build script in this repository. Use these lightweight checks during development:

- `python -m compileall custom_components/yunmao` checks Python syntax.
- `cp -R custom_components/yunmao /path/to/config/custom_components/` installs the integration into a local Home Assistant config directory.
- Restart Home Assistant, then add `Yun Mao` through Settings > Devices & Services to validate the config flow and entities.
- `git status` should stay clean before opening a PR.

## Coding Style & Naming Conventions
Follow the existing Home Assistant-style Python layout: 4-space indentation, `snake_case` for functions and variables, and `UPPER_CASE` for constants. Match current module boundaries instead of adding large mixed-purpose files. Keep entity-facing names descriptive and aligned with the existing device map. When UI text changes, update both `strings.json` and the relevant translation files.

## Testing Guidelines
No automated test suite is checked in today, so every change needs a manual smoke test in Home Assistant. At minimum, verify setup through the config flow, light on/off behavior, cover open/close/stop behavior, and gateway updates over ports `8888` and `21688`. If you add tests later, place them under `tests/` and use `test_<module>.py` naming.

## Commit & Pull Request Guidelines
Recent commits use short subjects such as `bug fix`, `server mode`, and `Optimize data pull`. Keep commit messages brief, imperative, and focused on one change, for example `fix cover stop state`. Pull requests should summarize the behavior change, mention any IP/MAC/port assumptions, and include Home Assistant screenshots or relevant log snippets when UI or connection behavior changes.

## Security & Configuration Tips
This codebase already contains real-looking local network values and device identifiers. Do not add more private environment data unless required, and prefer moving new settings into the config flow instead of hardcoding them. Scrub IPs, MACs, and device names from screenshots or logs before sharing externally.
