Release a new version of the integration.

## Process

1. Pull the latest changes from remote: `git pull`

2. Determine the next version number based on the current version in `custom_components/gardena_smart_system/manifest.json` and the type of release requested (beta or stable).
   - Beta versions: `X.Y.Z-betaN` (increment N from the last beta, or start at beta1)
   - Stable versions: `X.Y.Z` (remove the beta suffix)
   - If `CHANGELOG.md` has a `### Breaking Changes` section under `[Unreleased]`, bump the major version.

3. Update the version in `custom_components/gardena_smart_system/manifest.json`.

4. Update `CHANGELOG.md`:
   - **Beta release:** Replace `## [Unreleased]` with `## [<version>] - YYYY-MM-DD` (today's date). Add a fresh empty `## [Unreleased]` section above it.
   - **Stable release:** A stable version supersedes all the beta versions that led up to it (e.g. `3.1.0` follows `3.1.0-beta1/2/3`). Merge the `[Unreleased]` section **and every `X.Y.Z-betaN` section since the last stable release** into a single `## [<version>] - YYYY-MM-DD` section:
     - Combine all entries under shared `### Added` / `### Changed` / `### Fixed` / `### Breaking Changes` headings (in that order), de-duplicating any entries that were carried across betas.
     - Remove the now-merged individual `-betaN` sections so the stable version is the single authoritative entry for the release.
     - Add a fresh empty `## [Unreleased]` section above it.

5. Commit with message: `chore: bump version to <version>`

6. Create a git tag matching the version exactly (e.g. `2.0.1-beta2` or `2.0.1`).

7. Push the commit and tag:
   ```
   git push && git push origin <tag>
   ```

8. Create the GitHub release with the content of the changelog section as body:
   - For beta releases:
     ```
     gh release create <tag> --generate-notes --prerelease --title "Release <tag>"
     ```
   - For stable releases:
     ```
     gh release create <tag> --notes "$(changelog section content)" --latest --title "Release <tag>"
     ```
     Use the changelog section for that version as release notes (formatted as markdown). Fall back to `--generate-notes` if the section is empty.

## Tag format

Tags use the bare version number without any prefix (no `v`):
- `2.0.1-beta2` (not `v2.0.1-beta2`)
- `2.0.1` (not `v2.0.1`)

9. Comment on referenced issues/PRs to notify users that the fix or feature is now available:
   - Parse the changelog section for issue references (e.g. `#351`, `#352`)
   - For each referenced issue, post a comment:
     ```
     gh issue comment <number> --repo py-smart-gardena/hass-gardena-smart-system --body "This has been addressed in release <version>. Update via HACS to get the fix."
     ```

## Notes

- Always check existing tags with `git tag --list` to confirm the next version number.
- The version in manifest.json and the git tag must match exactly.
- If `CHANGELOG.md` has no `[Unreleased]` section or it's empty, warn the user before proceeding.
