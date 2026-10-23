# Releasing mcphee

Releases are published by the `Publish` GitHub Actions workflow (`.github/workflows/publish.yml`) using
PyPI Trusted Publishing (OIDC), so no API tokens are stored anywhere.

## Release steps

1. Bump `version` in `pyproject.toml`, run `uv lock`, and move the `[Unreleased]` notes in
   `CHANGELOG.md` under a dated `[X.Y.Z]` heading. PyPI never accepts the same version twice.
2. Optional dry run: **Actions → Publish → Run workflow → target `testpypi`**, then install from TestPyPI:

   ```bash
   uv tool install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ mcphee
   ```

3. Publish: create a GitHub Release tagged `vX.Y.Z` from `main`. The workflow uploads it to PyPI.
4. Verify: `uv tool install --refresh mcphee && mcphee --version`.

To build locally without publishing, run `uv build`. It writes `dist/mcphee-*.whl` and `dist/mcphee-*.tar.gz`.

## Trusted publisher configuration

This is already configured for `mcphee` on PyPI. It only needs repeating for a new index, such as
TestPyPI for the dry run. Use **Account → Publishing → Add a pending publisher**:

| Field | Value |
|---|---|
| PyPI Project Name | `mcphee` |
| Owner | `dgwartney` |
| Repository name | `mcphee` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` (use `testpypi` on TestPyPI) |
