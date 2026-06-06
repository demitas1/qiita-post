#!/bin/bash
set -e
CONFIG_FILE="$HOME/.config/qiita_post/config.json"
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "エラー: 設定ファイルが見つかりません: $CONFIG_FILE" >&2
    echo "  mkdir -p ~/.config/qiita_post && cp config.json ~/.config/qiita_post/" >&2
    exit 1
fi

exec "$PROJ_DIR/venv/bin/python" "$PROJ_DIR/qiita_post.py" --config "$CONFIG_FILE" "$@"
