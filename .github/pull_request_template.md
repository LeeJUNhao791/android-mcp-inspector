## Summary

<!-- Describe the problem and the resulting behavior. Link a related issue if available. -->

## Validation

<!-- List exact commands and results. Mark checks not run and explain why. See CONTRIBUTING.md for setup. -->

- MCP stdio tests:
- Bundled checker CLI tests:
- Input: synthetic fixture / redistributable real APK. Include the build or revision when relevant.
- Inspection result: `exit_code`, `report.status` and the relevant library entry. For response changes, compare MCP and direct CLI results.

<!-- Static APK inspection does not verify installation, launch or runtime on a device. Record any device checks separately. -->

## Checklist

- [ ] The change is focused, with regression coverage for changed behavior where applicable.
- [ ] Setup or tool usage changes are reflected in both README files.
- [ ] Shared inputs are synthetic or redistributable; private paths, credentials and customer APKs/AARs are excluded.
