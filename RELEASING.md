# Releasing Yun Mao

Use GitHub Releases for HACS upgrade notes. HACS reads the release body, so publish a full GitHub release, not only a tag.

## Release steps

1. Update `custom_components/yunmao/manifest.json` `version`.
2. Commit the change.
3. Create and push a tag such as `v2.0.1`.
4. Draft a GitHub Release for that tag.
5. Enable `Generate release notes`, then prepend a short manual summary.
6. Publish the release after verifying the notes are accurate.

## Recommended release note structure

```md
## Compatibility
- Home Assistant: tested with 2026.x
- Migration: none

## What's Changed
- Short summary of the user-visible behavior change.
- Mention gateway protocol changes if any.

## Breaking Changes
- Describe entity, device, or configuration changes.
- Call out Node-RED impact if identifiers could change.

## Upgrade Notes
- Restart Home Assistant after updating from HACS.
- Reconfigure the integration only if explicitly required.
```

## Versioning

- Use semantic versioning where practical: `vMAJOR.MINOR.PATCH`.
- Bump `MAJOR` for breaking changes or migration risk.
- Bump `MINOR` for backward-compatible features.
- Bump `PATCH` for fixes and small maintenance updates.
