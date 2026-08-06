# Release process

This document walks through cutting a release end-to-end: version bump, changelog, tag, PyPI publish, GitHub Release, and what to do when something goes wrong.

## Overview

The release is **tag-driven**. There is no local release script. Pushing a tag matching `v*` to `origin` triggers `.github/workflows/release.yml`, which runs three jobs:

1. **`build`** — runs `python -m build`, producing sdist and wheel, uploaded as a workflow artifact.
2. **`publish-pypi`** — downloads the artifact and publishes to PyPI via `pypa/gh-action-pypi-publish`. Requires the `PYPI_TOKEN` secret to be configured on the repository.
3. **`github-release`** — attaches the sdist and wheel to a GitHub Release. **Only runs on tag push** — `workflow_dispatch` skips it. The release itself is created out-of-band, by hand.

The pipeline:

```
local checkout ──▶ git tag ──▶ git push origin vX.Y.Z ──▶ GitHub Actions
                                                              │
                                                              ├──▶ PyPI (immutable)
                                                              └──▶ GitHub Release (mutable)
```

## Before the tag

### 1. Pick the new version

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). While the major version is `0`, the minor slot is treated as the "breaking changes" slot:

| Change kind | Bump |
|---|---|
| Bug fix that does not change the public API | patch (`0.3.1 → 0.3.2`) |
| Backwards-compatible new API | minor (`0.3.x → 0.4.0`) |
| Any change that breaks an existing public API or removes a deprecated symbol | minor (`0.3.x → 0.4.0`) during the `0.y` line |

Adding a new public function (e.g. `read_document_detailed`) is a minor bump under this convention. `read_document`, `read_pdf`, `clean_line`, and `clean_text` remain untouched.

### 2. Bump the version in three places

The version string appears in three files. They must all agree.

| File | Line | What to change |
|---|---|---|
| `pyproject.toml` | `version = "0.3.1"` | Bump the `version` field under `[project]`. |
| `ocr_extractor/__init__.py` | `__version__ = "0.3.1"` | Bump the `__version__` string. |
| `README.md` | `__version__` — string, e.g. \`"0.3.1"\`` | Bump the example in the public-API list. |

The `pyproject.toml` value is the source of truth — it is what `python -m build` reads into the wheel filename and the `Version` metadata. The other two are read by `ocr_extractor.__version__` and the README's API summary respectively.

### 3. Update `CHANGELOG.md`

Add an entry at the top under `## [Unreleased]`. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/):

```markdown
## [0.X.Y] - YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Removed
- ...
```

Replace the `[Unreleased]` heading with a versioned one and a date. If the `[Unreleased]` section was empty, drop it; otherwise leave it in place for the next release.

### 4. Run the tests locally

```bash
pip install -e ".[dev]"
pytest
```

End-to-end tests that hit a real Tesseract are skipped if `tesseract` is not on `PATH`. That is fine for the PR review but you should at least make sure the unit tests pass on every supported Python.

### 5. Confirm `main` is clean and current

```bash
git checkout main
git pull --ff-only
git status   # should report "nothing to commit, working tree clean"
```

### 6. Commit the bump

```bash
git add pyproject.toml ocr_extractor/__init__.py README.md CHANGELOG.md
git commit -m "chore: bump version to 0.X.Y"
git push origin main
```

## Cutting the release

### 7. Create an annotated tag

```bash
git tag -a v0.X.Y -m "Release 0.X.Y"
```

Annotated tags (`-a`) carry their own author and message and are the form GitHub surfaces in the Releases UI. Use `-s` instead of `-a` to additionally GPG-sign the tag if your repo requires it.

### 8. Push the tag

```bash
git push origin v0.X.Y
```

**This is the point of no return.** Pushing the tag starts the workflow and the `publish-pypi` job will upload to PyPI as soon as the artifact is built. PyPI uploads of an existing version are immutable — once a version is published it cannot be replaced or removed.

### 9. Create the GitHub Release

The `github-release` workflow job **attaches** the built artifacts to a Release, but it does not create one. Create the Release before or shortly after pushing the tag:

1. Open `https://github.com/roilanrodriguez55/ocr-extractor/releases/new`.
2. Choose the tag you just pushed (`v0.X.Y`).
3. Title: `v0.X.Y`.
4. Description: paste the `CHANGELOG.md` entry for this version.
5. Click **Publish release** (not "Save draft" — the attach job skips drafts).

Within a minute or two, the `github-release` job attaches `dist/*.whl` and `dist/*.tar.gz` to the Release. If it does not, see [Troubleshooting](#troubleshooting).

### 10. Verify

| What | Where | Expected |
|---|---|---|
| GitHub Actions run | `https://github.com/roilanrodriguez55/ocr-extractor/actions` | All three jobs green. |
| PyPI upload | `https://pypi.org/project/ocr-extractor/0.X.Y/` | sdist and wheel present. |
| GitHub Release | `https://github.com/roilanrodriguez55/ocr-extractor/releases/tag/v0.X.Y` | Tag exists with the sdist and wheel attached. |
| CLI | `pip install --upgrade ocr-extractor && ocr-extractor --version` | Prints `0.X.Y`. |
| Library | `pip install --upgrade ocr-extractor && python -c "import ocr_extractor; print(ocr_extractor.__version__)"` | Prints `0.X.Y`. |

If `pip install --upgrade` does not pick up the new version, check the upload timestamp on PyPI — the package may take a minute to propagate to the simple index.

## After the release

- Announce on the channels the project uses (issue tracker, mailing list, etc.) if applicable.
- Move the changelog entry's `[Unreleased]` section back to the top, ready for the next set of changes.
- If the release was a minor bump that added a deprecated symbol, file a follow-up issue to track the removal in the next major.

## Troubleshooting

### `publish-pypi` fails with 403

The `PYPI_TOKEN` secret is missing, revoked, or lacks upload rights for the `ocr-extractor` project.

1. Generate a new token at `https://pypi.org/manage/account/token/` scoped to the `ocr-extractor` project (or the whole account if you want flexibility).
2. Add it as `PYPI_TOKEN` under `Settings → Secrets and variables → Actions` in the GitHub repository.
3. From the failed Actions run, click **Re-run jobs** on `publish-pypi`. Do **not** re-run `build` — the artifact is still valid.
4. The `publish-pypi` job is gated by the `pypi` environment. If the run cannot dispatch, the environment may not exist — create it under `Settings → Environments` with no required reviewers.

### `github-release` did not attach files

The job is gated by `if: github.event_name == 'push'`, so it only runs on tag pushes. If the Release was created before the workflow attached, or if the Release is a draft, the job silently skips. Trigger a re-run from the Actions tab after confirming the Release is published (not draft).

### PyPI rejects the upload with "filename already used"

PyPI filenames are immutable. The version number must be different from any previously uploaded version. Bump to the next patch / minor / major and start over at [step 2](#2-bump-the-version-in-three-places).

### Tag pushed but workflow did not run

The tag does not match the workflow's `tags:` filter (`v*`), or the workflow file is on a different branch. Check `https://github.com/roilanrodriguez55/ocr-extractor/actions` for any pending runs.

### A wheel built with the wrong version is uploaded

The `pyproject.toml` and `ocr_extractor/__init__.py` versions disagreed at build time. The wheel's metadata comes from `pyproject.toml`; the runtime `__version__` comes from `__init__.py`. Pick one as canonical, fix the drift, and cut a new version with the corrected value.

### Need to retract a release

PyPI does not allow removing an uploaded version, but you can [yank](https://docs.pypi.org/project-management/#yanking) it. Yanking hides the version from `pip install` resolution but leaves it accessible by exact pin. The corresponding GitHub Release can be deleted; the tag itself can be kept (and re-pointed at a new commit) or deleted with `git push origin :refs/tags/v0.X.Y`.

## Local dry-run (optional)

To check the build artefacts before pushing the tag, run `python -m build` locally and inspect `dist/`:

```bash
pip install build
python -m build
ls dist/
# ocr_extractor-0.X.Y-py3-none-any.whl
# ocr_extractor-0.X.Y.tar.gz
```

Upload to Test PyPI instead of the real index to verify the artifact is valid:

```bash
pip install twine
twine upload --repository testpypi dist/*
```

Then install from Test PyPI in a throwaway environment:

```bash
pip install --index-url https://test.pypi.org/simple/ ocr-extractor==0.X.Y
```

This catches most packaging issues before the real release. The GitHub Actions workflow only runs on tag push, so the local dry-run is the cheapest way to verify before going live.
