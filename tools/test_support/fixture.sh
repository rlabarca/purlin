#!/usr/bin/env bash
# tools/test_support/fixture.sh
#
# Consumer-facing fixture repo tool for test infrastructure.
# See features/test_fixture_repo.md for full specification.

set -euo pipefail

# --- Project root detection (submodule-safe) ---
resolve_project_root() {
    if [[ -n "${PURLIN_PROJECT_ROOT:-}" ]]; then
        echo "$PURLIN_PROJECT_ROOT"
        return
    fi
    # Climbing fallback: try submodule path (further) before standalone (nearer)
    local dir
    dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local candidate=""
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/features" ]]; then
            candidate="$dir"
        fi
        dir="$(dirname "$dir")"
    done
    if [[ -n "$candidate" ]]; then
        echo "$candidate"
        return
    fi
    echo "Error: Could not detect project root" >&2
    return 1
}

usage() {
    cat <<'USAGE'
Usage: fixture <subcommand> [args]

Subcommands:
  checkout <repo-url> <tag> [--dir <path>]  Clone fixture at tag
  cleanup <path>                             Remove fixture directory
  list <repo-url> [--ref <project-ref>]      List fixture tags
  prune <repo-url> [--ref <project-ref>]     Find orphan fixture tags
USAGE
    exit 1
}

cmd_checkout() {
    if [[ $# -lt 2 ]]; then
        echo "Error: checkout requires <repo-url> <tag>" >&2
        exit 1
    fi

    local repo_url="$1"
    local tag="$2"
    shift 2

    local target_dir=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dir)
                [[ $# -lt 2 ]] && { echo "Error: --dir requires a path" >&2; exit 1; }
                target_dir="$2"
                shift 2
                ;;
            *)
                echo "Error: Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done

    if [[ -z "$target_dir" ]]; then
        target_dir="$(mktemp -d)"
    else
        mkdir -p "$target_dir"
    fi

    git clone --depth 1 --branch "$tag" "$repo_url" "$target_dir" >/dev/null 2>&1
    echo "$target_dir"
}

cmd_cleanup() {
    if [[ $# -lt 1 ]]; then
        echo "Error: cleanup requires <path>" >&2
        exit 1
    fi

    local path="$1"

    # Safety guard: only allow paths under /tmp/ or system temp directory
    local sys_tmp
    sys_tmp="$(dirname "$(mktemp -u)")"

    if [[ "$path" != /tmp/* && "$path" != "${sys_tmp}"/* ]]; then
        echo "Error: Refusing to delete path outside temp directory: $path" >&2
        exit 1
    fi

    if [[ -d "$path" ]]; then
        rm -rf "$path"
    fi
}

cmd_list() {
    if [[ $# -lt 1 ]]; then
        echo "Error: list requires <repo-url>" >&2
        exit 1
    fi

    local repo_url="$1"
    shift

    local ref_filter=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --ref)
                [[ $# -lt 2 ]] && { echo "Error: --ref requires a value" >&2; exit 1; }
                ref_filter="$2"
                shift 2
                ;;
            *)
                echo "Error: Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done

    local tags
    tags="$(git ls-remote --tags "$repo_url" 2>/dev/null | awk '{print $2}' | sed 's|^refs/tags/||' | grep -v '\^{}$' | sort)" || true

    if [[ -z "$tags" ]]; then
        return 0
    fi

    if [[ -n "$ref_filter" ]]; then
        echo "$tags" | grep "^${ref_filter}/" || true
    else
        echo "$tags"
    fi
}

cmd_prune() {
    if [[ $# -lt 1 ]]; then
        echo "Error: prune requires <repo-url>" >&2
        exit 1
    fi

    local repo_url="$1"
    shift

    local ref_filter=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --ref)
                [[ $# -lt 2 ]] && { echo "Error: --ref requires a value" >&2; exit 1; }
                ref_filter="$2"
                shift 2
                ;;
            *)
                echo "Error: Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done

    local project_root
    project_root="$(resolve_project_root)"

    local tags
    tags="$(git ls-remote --tags "$repo_url" 2>/dev/null | awk '{print $2}' | sed 's|^refs/tags/||' | grep -v '\^{}$' | sort)" || true

    if [[ -z "$tags" ]]; then
        echo "No tags found in repository."
        return 0
    fi

    if [[ -n "$ref_filter" ]]; then
        tags="$(echo "$tags" | grep "^${ref_filter}/" || true)"
    fi

    if [[ -z "$tags" ]]; then
        echo "No tags found matching filter."
        return 0
    fi

    local orphans=()
    while IFS= read -r tag; do
        [[ -z "$tag" ]] && continue
        # Extract feature name: <project-ref>/<feature-name>/<scenario-slug>
        local feature_name
        feature_name="$(echo "$tag" | cut -d'/' -f2)"

        if [[ ! -f "$project_root/features/${feature_name}.md" ]] || \
           [[ -f "$project_root/features/tombstones/${feature_name}.md" ]]; then
            orphans+=("$tag")
        fi
    done <<< "$tags"

    if [[ ${#orphans[@]} -eq 0 ]]; then
        echo "No orphan tags found."
    else
        echo "Orphan tags:"
        for tag in "${orphans[@]}"; do
            echo "  $tag"
        done
    fi
}

# --- Main dispatch ---
if [[ $# -lt 1 ]]; then
    usage
fi

subcommand="$1"
shift

case "$subcommand" in
    checkout)
        cmd_checkout "$@"
        ;;
    cleanup)
        cmd_cleanup "$@"
        ;;
    list)
        cmd_list "$@"
        ;;
    prune)
        cmd_prune "$@"
        ;;
    *)
        echo "Error: Unknown subcommand: $subcommand" >&2
        usage
        ;;
esac
