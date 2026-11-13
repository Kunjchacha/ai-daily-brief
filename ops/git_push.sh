#!/bin/sh
# Push main to GitHub using the fine-grained token in ~/.config/ai-daily-brief/token.
# The token is handed to git through GIT_ASKPASS: it is never written to .git/config, a remote URL, or the logs.
set -eu
TOKEN_FILE="$HOME/.config/ai-daily-brief/token"
[ -s "$TOKEN_FILE" ] || { echo "No token at $TOKEN_FILE" >&2; exit 1; }
ASK=$(mktemp)
trap 'rm -f "$ASK"' EXIT
cat > "$ASK" <<'EOS'
#!/bin/sh
case "$1" in
  Username*) echo x-access-token ;;
  *) cat "$HOME/.config/ai-daily-brief/token" ;;
esac
EOS
chmod 700 "$ASK"
GIT_ASKPASS="$ASK" GIT_TERMINAL_PROMPT=0 git -c credential.helper= push origin "${1:-main}"
