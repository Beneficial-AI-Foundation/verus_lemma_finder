# GitHub Actions Workflows

This directory contains GitHub Actions workflows for continuous integration, releases, and security scanning.

## Workflows

### 1. CI Workflow (`ci.yml`)

**Trigger:** Runs on push to main/master/develop branches and on pull requests

**Jobs:**
- **Test**: Runs tests across Python 3.12-3.13 and multiple operating systems (Ubuntu, macOS, Windows)
  - Builds Rust extension with maturin
  - Executes pytest suite
  - Generates coverage report (on Ubuntu with Python 3.12)
  - Uploads coverage to Codecov
  
- **Lint**: Checks Python code quality and formatting
  - Runs ruff check for linting (`src/`, `tests/`, `scripts/`, `demo/`)
  - Runs ruff format check
  
- **Type Check**: Static type checking
  - Runs mypy on the source code
  
- **Rust Lint**: Checks Rust code quality
  - Runs clippy on the Rust extension
  
- **Build**: Creates distribution packages
  - Builds wheel with maturin (includes Rust extension)
  - Validates with twine
  - Uploads artifacts

### 2. Release Workflow (`release.yml`)

**Trigger:** 
- Automatically on version tags (e.g., `v1.0.0`)
- Manually via workflow_dispatch

**Jobs:**
- **Build and Publish**: Creates release and publishes to PyPI
  - Builds wheel with maturin
  - Publishes to PyPI (requires `PYPI_API_TOKEN` secret)
  - Creates GitHub release with release notes
  
- **Test Publish**: Optional job for publishing to TestPyPI
  - Only runs on manual trigger
  - Requires `TEST_PYPI_API_TOKEN` secret

### 3. CodeQL Workflow (`codeql.yml`)

**Trigger:**
- Push to main/master
- Pull requests
- Weekly schedule (Monday at midnight)

**Purpose:** Security scanning and code quality analysis using GitHub's CodeQL

### 4. Dependabot Auto-merge (`dependabot-auto-merge.yml`)

**Trigger:** Pull requests from Dependabot

**Purpose:** Automatically merges patch and minor version updates from Dependabot

## Required Secrets

### For PyPI Publishing (Optional)

PyPI publishing is **optional**. If tokens are not configured, releases will still:
- Build the wheel with Rust extension
- Create a GitHub Release with downloadable artifacts

Users can then install from the GitHub release or from source.

**To enable PyPI publishing:**

1. **PYPI_API_TOKEN**: PyPI API token for publishing releases
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token
   - Add it to GitHub: Settings → Secrets and variables → Actions → New repository secret

2. **TEST_PYPI_API_TOKEN** (optional): TestPyPI token for testing releases
   - Go to https://test.pypi.org/manage/account/token/
   - Create a new API token
   - Add it to GitHub secrets

### For Codecov (optional):

If using Codecov, add a `CODECOV_TOKEN` secret or configure your repository on codecov.io.

## Usage

### Running CI

CI runs automatically on:
- Every push to main/master/develop
- Every pull request

### Creating a Release

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "1.0.1"
   ```

2. **Commit and push** the version change

3. **Create and push a tag**:
   ```bash
   git tag -a v1.0.1 -m "Release version 1.0.1"
   git push origin v1.0.1
   ```

4. The release workflow will automatically:
   - Build the wheel with Rust extension
   - Publish to PyPI
   - Create a GitHub release

### Manual Release (Testing)

You can manually trigger a release to TestPyPI:

1. Go to Actions → Release
2. Click "Run workflow"
3. Enter the version number
4. Click "Run workflow"

## Maintenance

### Updating Workflows

- Workflows use specific action versions (e.g., `@v4`, `@v5`)
- Dependabot will automatically create PRs to update action versions
- Review and merge these PRs to keep workflows secure and up-to-date

### Adding New Python Versions

To add support for a new Python version:

1. Update `pyproject.toml` classifiers:
   ```toml
   "Programming Language :: Python :: 3.14",
   ```

2. Update the CI workflow matrix in `ci.yml`:
   ```yaml
   python-version: ['3.12', '3.13', '3.14']
   ```

## Troubleshooting

**Tests failing?**
- Check the specific job logs in the Actions tab
- Run tests locally: `uv run pytest tests/ -v`
- Ensure Rust extension is built: `uv run maturin develop --release`

**Release failing?**
- Verify `PYPI_API_TOKEN` is set correctly
- Ensure version in `pyproject.toml` matches the git tag
- Check that the version doesn't already exist on PyPI

**Python linting errors?**
- Run locally: `uv run ruff check src/ tests/ scripts/ demo/`
- Auto-fix: `uv run ruff check --fix src/ tests/ scripts/ demo/`
- Format: `uv run ruff format src/ tests/ scripts/ demo/`

**Rust linting errors?**
- Run locally: `cd rust && cargo clippy`
- Auto-fix: `cd rust && cargo clippy --fix --allow-dirty`

**Build failing?**
- Ensure Rust toolchain is installed
- Check maturin can build: `maturin build --release`

## Best Practices

1. **Always run tests locally** before pushing
2. **Keep workflows updated** via Dependabot
3. **Use semantic versioning** for releases (MAJOR.MINOR.PATCH)
4. **Review Dependabot PRs** before auto-merging
5. **Monitor CodeQL alerts** and address security issues promptly
6. **Run both Python and Rust lints** before committing
