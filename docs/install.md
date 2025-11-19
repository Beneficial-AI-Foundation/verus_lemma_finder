# Installation Guide

## Quick Install

### Option A: Using uv (Recommended - Fastest)

```bash
cd ~/git_repos/baif/verus_lemma_finder

# Install uv if not already installed
# curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies (uv handles everything)
uv sync

# Verify installation
uv run lemma_search_tool.py --help
```

### Option B: Using pip with venv (Traditional)

```bash
cd ~/git_repos/baif/verus_lemma_finder

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -e .

# Verify installation
./lemma help
```

## Prerequisites

### Required

1. **Python 3.12+**
   ```bash
   python3 --version
   ```

2. **verus-analyzer** (from Verus installation)
   ```bash
   verus-analyzer --version
   ```

3. **scip CLI tool**
   - Download from: https://github.com/sourcegraph/scip/releases

### Optional (but Recommended)

- **uv** (fast Python package installer)
  ```bash
  # Install uv
  curl -LsSf https://astral.sh/uv/install.sh | sh
  
  # Verify installation
  uv --version
  ```

- **git** (for cloning vstd)
  ```bash
  git --version
  ```

## Step-by-Step Installation

Choose your preferred method:

### Method A: Using uv (Recommended)

#### 1. Navigate to Project

```bash
cd ~/git_repos/baif/verus_lemma_finder
```

#### 2. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 3. Sync Dependencies

```bash
uv sync
```

This will automatically:
- Create an isolated Python environment
- Install all required dependencies
- Download the `all-MiniLM-L6-v2` model (~500 MB on first run)

#### 4. Verify Installation

```bash
uv run lemma_search_tool.py --help
```

You should see the help message.

### Method B: Using pip with venv (Traditional)

#### 1. Navigate to Project

```bash
cd ~/git_repos/baif/verus_lemma_finder
```

#### 2. Create Virtual Environment

```bash
python3 -m venv .venv
```

This creates an isolated Python environment for the project dependencies.

#### 3. Activate Virtual Environment

**On Linux/macOS:**
```bash
source .venv/bin/activate
```

**On Windows:**
```cmd
.venv\Scripts\activate
```

You should see `(.venv)` in your terminal prompt.

#### 4. Install Dependencies

```bash
pip install -e .
```

This will install:
- `sentence-transformers` (for semantic search)
- `numpy` (for array operations)

**Note:** The first run will download the `all-MiniLM-L6-v2` model (~500 MB).

#### 5. Verify Installation

```bash
./lemma help
```

You should see the help message.

#### 6. Test Basic Functionality

```bash
# Should show version and usage info
python3 lemma_search_tool.py --help
```

## Adding to PATH (Optional)

To use `lemma` from anywhere:

### Temporary (current session only)

```bash
export PATH="$PATH:$HOME/git_repos/baif/verus_lemma_finder"
```

### Permanent (recommended)

**For bash:**
```bash
echo 'export PATH="$PATH:$HOME/git_repos/baif/verus_lemma_finder"' >> ~/.bashrc
source ~/.bashrc
```

**For zsh:**
```bash
echo 'export PATH="$PATH:$HOME/git_repos/baif/verus_lemma_finder"' >> ~/.zshrc
source ~/.zshrc
```

Now you can use `lemma` from any directory!

## Verification

Test the installation:

```bash
# Should work from any directory (if added to PATH)
lemma help

# Or with full path
~/git_repos/baif/verus_lemma_finder/lemma help
```

## Troubleshooting

### "Command not found: verus-analyzer"

**Solution:** Install Verus or add it to your PATH.

```bash
# Check if Verus is installed
which verus

# If installed, add to PATH (example)
export PATH="$PATH:/path/to/verus/source/target-verus/release"
```

### "ModuleNotFoundError: No module named 'sentence_transformers'"

**Solution:** Ensure you've activated the virtual environment and installed dependencies.

```bash
source .venv/bin/activate
pip install -e .
```

### "Virtual environment not found"

**Solution:** Create the virtual environment first.

```bash
cd ~/git_repos/baif/verus_lemma_finder
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage After Installation

See [README.md](README.md) for usage examples, or:

### Using uv

```bash
# Quick start
cd /path/to/your/verus/project

# Generate SCIP index
uv run lemma_search_tool.py generate-scip .

# Build searchable index
uv run lemma_search_tool.py index project_scip.json --embeddings

# Search!
uv run lemma_search_tool.py search "your query" lemma_index.json

# Interactive mode
uv run lemma_search_tool.py interactive lemma_index.json
```

### Using traditional method (with wrapper script)

```bash
# Quick start
cd /path/to/your/verus/project

# Generate SCIP index
lemma generate-scip .

# Build searchable index
lemma reindex project_scip.json

# Search!
lemma search "your query"

# Interactive mode
lemma interactive
```

## Uninstallation

To completely remove:

```bash
# Remove project directory
rm -rf ~/git_repos/baif/verus_lemma_finder

# Remove from PATH (edit ~/.bashrc or ~/.zshrc)
# Remove the line: export PATH="$PATH:$HOME/git_repos/baif/verus_lemma_finder"

# Reload shell config
source ~/.bashrc  # or source ~/.zshrc
```

## Updating

To update the tool (if using git):

### Using uv

```bash
cd ~/git_repos/baif/verus_lemma_finder
git pull

# Update dependencies if requirements changed
uv sync
```
