#!/bin/bash
set -e
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

cat > "$INSTALL_DIR/qiita_post" << EOF
#!/bin/bash
CONFIG_FILE="\$HOME/.config/qiita_post/config.json"
if [ ! -f "\$CONFIG_FILE" ]; then
    echo "エラー: 設定ファイルが見つかりません: \$CONFIG_FILE" >&2
    echo "  mkdir -p ~/.config/qiita_post && cp config.json ~/.config/qiita_post/" >&2
    exit 1
fi
exec "$PROJ_DIR/venv/bin/python" "$PROJ_DIR/qiita_post.py" --config "\$CONFIG_FILE" "\$@"
EOF

chmod +x "$INSTALL_DIR/qiita_post"

echo "インストール完了:"
echo "  $INSTALL_DIR/qiita_post  →  $PROJ_DIR/qiita_post.py"
echo ""
echo "設定ファイルの配置:"
echo "  mkdir -p ~/.config/qiita_post"
echo "  cp config.json ~/.config/qiita_post/"
