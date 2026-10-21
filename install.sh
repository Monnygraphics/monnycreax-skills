#!/usr/bin/env bash
# Installs MonnyCreaX skills into ~/.claude/skills.
#   ./install.sh reel-editor humanizer
#   ./install.sh --category video-editing
#   ./install.sh --all [--force]
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)/skills"
dest="$HOME/.claude/skills"
all=0; force=0; category=""; names=()

while [ $# -gt 0 ]; do
  case "$1" in
    --all) all=1 ;;
    --force) force=1 ;;
    --category) category="$2"; shift ;;
    --list) names=(); all=0; category="" ; break ;;
    *) names+=("$1") ;;
  esac
  shift
done

list() { for d in "$root"/*/*/; do d=${d%/}; printf '%-30s %s\n' "$(basename "$d")" "$(basename "$(dirname "$d")")"; done; }

if [ $all -eq 0 ] && [ -z "$category" ] && [ ${#names[@]} -eq 0 ]; then
  list; echo; echo "Usage: ./install.sh <name>... | --category <category> | --all   (add --force to overwrite)"; exit 0
fi

mkdir -p "$dest"
for d in "$root"/*/*/; do
  d=${d%/}; name=$(basename "$d"); cat=$(basename "$(dirname "$d")")
  want=0
  [ $all -eq 1 ] && want=1
  [ "$category" = "$cat" ] && want=1
  for n in "${names[@]+"${names[@]}"}"; do [ "$n" = "$name" ] && want=1; done
  [ $want -eq 1 ] || continue
  if [ -e "$dest/$name" ]; then
    if [ $force -eq 0 ]; then echo "skip      $name (already installed; use --force to replace)"; continue; fi
    rm -rf "$dest/$name"
  fi
  cp -R "$d" "$dest/$name"
  echo "installed $name"
done
for n in "${names[@]+"${names[@]}"}"; do
  ls -d "$root"/*/"$n" >/dev/null 2>&1 || echo "warning: no skill named '$n' (run ./install.sh to list)"
done
echo; echo "Done. Restart Claude Code to load the new skills."
