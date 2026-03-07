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
  init [--path <path>]                                Create bare fixture repo
  add-tag <tag> [--from-dir <path>] [--message <msg>] [--force]
                                                       Create tagged commit
  checkout <repo-url> <tag> [--dir <path>]             Clone fixture at tag
  cleanup <path>                                       Remove fixture directory
  list <repo-url> [--ref <project-ref>]                List fixture tags
  prune <repo-url> [--ref <project-ref>]               Find orphan fixture tags
USAGE
    exit 1
}

cmd_init() {
    local repo_path=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path)
                [[ $# -lt 2 ]] && { echo "Error: --path requires a value" >&2; exit 1; }
                repo_path="$2"
                shift 2
                ;;
            *)
                echo "Error: Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done

    # Default to convention path
    if [[ -z "$repo_path" ]]; then
        local project_root
        project_root="$(resolve_project_root)"
        repo_path="$project_root/.purlin/runtime/fixture-repo"
    fi

    # Idempotent: check if bare repo already exists
    if [[ -d "$repo_path" ]]; then
        local is_bare
        is_bare="$(git -C "$repo_path" rev-parse --is-bare-repository 2>/dev/null || echo "false")"
        if [[ "$is_bare" == "true" ]]; then
            echo "Fixture repo already exists at $repo_path" >&2
            echo "$repo_path"
            return 0
        fi
    fi

    mkdir -p "$(dirname "$repo_path")"
    git init --bare "$repo_path" >/dev/null 2>&1
    echo "$repo_path"
}

cmd_add_tag() {
    if [[ $# -lt 1 ]]; then
        echo "Error: add-tag requires <tag>" >&2
        exit 1
    fi

    local tag="$1"
    shift

    local from_dir=""
    local message=""
    local force=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --from-dir)
                [[ $# -lt 2 ]] && { echo "Error: --from-dir requires a path" >&2; exit 1; }
                from_dir="$2"
                shift 2
                ;;
            --message)
                [[ $# -lt 2 ]] && { echo "Error: --message requires a value" >&2; exit 1; }
                message="$2"
                shift 2
                ;;
            --force)
                force=true
                shift
                ;;
            *)
                echo "Error: Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done

    # Validate tag format: 3 path segments, each lowercase alphanumeric plus hyphens/underscores
    if ! echo "$tag" | grep -qE '^[a-z0-9_-]+/[a-z0-9_-]+/[a-z0-9_-]+$'; then
        echo "Error: Invalid tag format '$tag'. Expected <ref>/<feature>/<slug> with lowercase alphanumeric, hyphens, and underscores." >&2
        exit 1
    fi

    # Default from-dir to project root
    if [[ -z "$from_dir" ]]; then
        local project_root
        project_root="$(resolve_project_root)"
        from_dir="$project_root"
    fi

    # Default message
    if [[ -z "$message" ]]; then
        message="State for $tag"
    fi

    # Resolve fixture repo via convention path
    local repo_path=""
    local project_root
    project_root="$(resolve_project_root)"
    repo_path="$project_root/.purlin/runtime/fixture-repo"

    if [[ ! -d "$repo_path" ]]; then
        echo "Error: Fixture repo not found at $repo_path. Run 'fixture init' first." >&2
        exit 1
    fi

    # Check if tag already exists
    if git -C "$repo_path" rev-parse "refs/tags/$tag" >/dev/null 2>&1; then
        if [[ "$force" != true ]]; then
            echo "Error: Tag '$tag' already exists. Use --force to overwrite." >&2
            exit 1
        fi
        # Delete existing tag for force overwrite
        git -C "$repo_path" tag -d "$tag" >/dev/null 2>&1
    fi

    # Create temp working clone
    local work_dir
    work_dir="$(mktemp -d)"
    trap 'rm -rf "$work_dir"' RETURN

    git clone "$repo_path" "$work_dir/clone" >/dev/null 2>&1 || {
        # Empty bare repo — initialize a fresh repo
        git init "$work_dir/clone" >/dev/null 2>&1
        git -C "$work_dir/clone" remote add origin "$repo_path"
    }

    cd "$work_dir/clone"
    git config user.email "fixture@purlin.dev"
    git config user.name "Purlin Fixture Builder"

    # Clean working directory (preserve .git)
    git rm -rf --quiet . 2>/dev/null || true
    git clean -fdx --quiet 2>/dev/null || true

    # Copy source files
    if [[ -d "$from_dir" ]]; then
        # Use rsync-like copy, excluding .git
        find "$from_dir" -mindepth 1 -maxdepth 1 -not -name '.git' -exec cp -R {} "$work_dir/clone/" \;
    fi

    # Commit and tag
    git add -A >/dev/null 2>&1
    git commit -m "$message" --allow-empty >/dev/null 2>&1
    git tag "$tag" >/dev/null 2>&1

    # Push to bare repo
    git push origin --tags >/dev/null 2>&1
    # Push the branch so future clones work
    local branch
    branch="$(git rev-parse --abbrev-ref HEAD)"
    git push origin "$branch" >/dev/null 2>&1 || true

    echo "Created tag: $tag"
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
    init)
        cmd_init "$@"
        ;;
    add-tag)
        cmd_add_tag "$@"
        ;;
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
