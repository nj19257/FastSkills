#!/usr/bin/env bash
# FastSkills — one-click setup script
# Usage: curl -sSL https://raw.githubusercontent.com/nj19257/FastSkills/main/install.sh | bash
set -euo pipefail

REPO_URL="https://github.com/nj19257/FastSkills.git"
INSTALL_DIR="fastskills"

echo "=== FastSkills Setup ==="
echo

# ------------------------------------------------------------------
# 1. Ensure uv is available
# ------------------------------------------------------------------
if ! command -v uv &>/dev/null; then
    echo "Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "uv installed."
else
    echo "uv found: $(uv --version)"
fi

# ------------------------------------------------------------------
# 2. Clone or update repo
# ------------------------------------------------------------------
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory '$INSTALL_DIR' already exists — updating."
    cd "$INSTALL_DIR"
    git pull --ff-only 2>/dev/null || true
else
    echo "Cloning FastSkills..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ------------------------------------------------------------------
# 3. Install dependencies
# ------------------------------------------------------------------
echo "Installing Python dependencies..."
uv sync --extra cli

# ------------------------------------------------------------------
# 4. Create launcher
# ------------------------------------------------------------------
create_launcher() {
    local launcher="$PWD/fastskills_cli"
    local install_dir="$PWD"

    cat > "$launcher" <<'LAUNCHER'
#!/usr/bin/env bash
# FastSkills CLI launcher — resolves symlinks to find the repo
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
cd "$DIR"
exec uv run python -m fastskills_cli "$@"
LAUNCHER
    chmod +x "$launcher"

    # Try to symlink into PATH
    if [ -w /usr/local/bin ]; then
        ln -sf "$launcher" /usr/local/bin/fastskills_cli
        echo "Launcher installed: /usr/local/bin/fastskills_cli"
    elif [ -d /usr/local/bin ]; then
        sudo ln -sf "$launcher" /usr/local/bin/fastskills_cli && \
            echo "Launcher installed: /usr/local/bin/fastskills_cli (via sudo)"
    else
        local dir="$HOME/.local/bin"
        mkdir -p "$dir"
        ln -sf "$launcher" "$dir/fastskills_cli"
        # Ensure ~/.local/bin is on PATH
        if [[ ":$PATH:" != *":$dir:"* ]]; then
            local shell_rc="$HOME/.bashrc"
            [ -f "$HOME/.zshrc" ] && shell_rc="$HOME/.zshrc"
            echo "export PATH=\"$dir:\$PATH\"" >> "$shell_rc"
            export PATH="$dir:$PATH"
            echo "Added $dir to PATH in $(basename "$shell_rc")"
        fi
        echo "Launcher installed: $dir/fastskills_cli"
    fi
    hash -r 2>/dev/null || true
}

create_launcher

# ------------------------------------------------------------------
# 5. Done
# ------------------------------------------------------------------
echo
echo "=== Setup complete ==="
echo
echo "Start the TUI:"
echo "  fastskills_cli"
echo
echo "On first launch you'll be prompted for your OpenRouter API key and model."
echo
