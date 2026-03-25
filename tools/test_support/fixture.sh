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

# --- Config helpers (fixture_repo_url in .purlin/config.json) ---
_read_fixture_repo_url() {
    local project_root
    project_root="$(resolve_project_root)"
    local config="$project_root/.purlin/config.json"
    if [[ -f "$config" ]]; then
        python3 -c "
import json, sys
with open('$config') as f:
    d = json.load(f)
v = d.get('fixture_repo_url', '')
if v:
    print(v)
" 2>/dev/null || true
    fi
}

_write_fixture_repo_url() {
    local url="$1"
    local project_root
    project_root="$(resolve_project_root)"
    local config="$project_root/.purlin/config.json"
    if [[ ! -f "$config" ]]; then
        echo "Error: Config file not found at $config" >&2
        return 1
    fi
    python3 -c "
import json
with open('$config') as f:
    d = json.load(f)
d['fixture_repo_url'] = '$url'
with open('$config', 'w') as f:
    json.dump(d, f, indent=4)
    f.write('\n')
"
}

usage() {
    cat <<'USAGE'
Usage: fixture <subcommand> [args]

Subcommands:
  init [--path <path>]                                Create bare fixture repo
  add-tag <tag> [--from-dir <path>] [--message <msg>] [--force] [--no-push]
                                                       Create tagged commit
  checkout <repo-url> <tag> [--dir <path>]             Clone fixture at tag
  cleanup <path>                                       Remove fixture directory
  list <repo-url> [--ref <project-ref>]                List fixture tags
  verify-url <url>                                     Test read/write access
  remote <url>                                         Configure remote fixture repo
  push <remote-url> [--tag <tag>]                      Push tags to remote
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
    local no_push=false

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
            --no-push)
                no_push=true
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

    # Auto-push to remote if configured and not suppressed
    if [[ "$no_push" != true ]]; then
        local remote_url
        remote_url="$(_read_fixture_repo_url)"
        if [[ -n "$remote_url" ]]; then
            local push_output
            local push_rc=0
            push_output=$(git -C "$repo_path" push "$remote_url" "refs/tags/$tag:refs/tags/$tag" 2>&1) || push_rc=$?
            if [[ $push_rc -eq 0 ]]; then
                echo "Pushed $tag to remote."
            else
                echo "Warning: Auto-push to remote failed. Local tag is still valid." >&2
                echo "  $push_output" >&2
            fi
        fi
    fi
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

_https_to_ssh() {
    # Convert HTTPS GitHub/GitLab URL to SSH equivalent.
    # Returns empty string if not a recognized host.
    local url="$1"
    local ssh_url=""

    if [[ "$url" =~ ^https://github\.com/([^/]+)/([^/]+)$ ]]; then
        local owner="${BASH_REMATCH[1]}"
        local repo="${BASH_REMATCH[2]}"
        repo="${repo%.git}"
        ssh_url="git@github.com:${owner}/${repo}.git"
    elif [[ "$url" =~ ^https://gitlab\.com/([^/]+)/([^/]+)$ ]]; then
        local owner="${BASH_REMATCH[1]}"
        local repo="${BASH_REMATCH[2]}"
        repo="${repo%.git}"
        ssh_url="git@gitlab.com:${owner}/${repo}.git"
    fi

    echo "$ssh_url"
}

cmd_verify_url() {
    if [[ $# -lt 1 ]]; then
        echo "Error: verify-url requires <url>" >&2
        exit 1
    fi

    local url="$1"

    # Test read access with the given URL
    if git ls-remote --tags "$url" >/dev/null 2>&1; then
        echo "$url"
        return 0
    fi

    # If HTTPS, try SSH fallback for known hosts
    if [[ "$url" =~ ^https:// ]]; then
        local ssh_url
        ssh_url="$(_https_to_ssh "$url")"
        if [[ -n "$ssh_url" ]]; then
            if git ls-remote --tags "$ssh_url" >/dev/null 2>&1; then
                echo "$ssh_url"
                return 0
            fi
        fi
    fi

    # No access method worked
    echo "Cannot access $url for read or write." >&2
    echo "" >&2
    echo "For GitHub private repos:" >&2
    echo "  1. Ensure SSH key is configured: ssh -T git@github.com" >&2
    echo "  2. Use SSH URL format: git@github.com:<owner>/<repo>.git" >&2
    echo "" >&2
    echo "For HTTPS with token:" >&2
    echo "  1. Configure credential helper: git config credential.helper store" >&2
    echo "  2. Or use token URL: https://<token>@github.com/<owner>/<repo>" >&2
    exit 1
}

cmd_push() {
    if [[ $# -lt 1 ]]; then
        echo "Error: push requires <remote-url>" >&2
        exit 1
    fi

    local remote_url="$1"
    shift

    local specific_tag=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --tag)
                [[ $# -lt 2 ]] && { echo "Error: --tag requires a value" >&2; exit 1; }
                specific_tag="$2"
                shift 2
                ;;
            *)
                echo "Error: Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done

    # Resolve local convention-path fixture repo
    local project_root
    project_root="$(resolve_project_root)"
    local repo_path="$project_root/.purlin/runtime/fixture-repo"

    if [[ ! -d "$repo_path" ]]; then
        echo "Error: Local fixture repo not found at $repo_path. Run 'fixture init' first." >&2
        exit 1
    fi

    local push_output
    local push_rc=0

    if [[ -n "$specific_tag" ]]; then
        # Verify tag exists locally
        if ! git -C "$repo_path" rev-parse "refs/tags/$specific_tag" >/dev/null 2>&1; then
            echo "Error: Tag '$specific_tag' not found in local fixture repo." >&2
            exit 1
        fi
        # Push specific tag
        push_output=$(git -C "$repo_path" push "$remote_url" "refs/tags/$specific_tag:refs/tags/$specific_tag" 2>&1) || push_rc=$?
    else
        # Push all tags
        push_output=$(git -C "$repo_path" push "$remote_url" --tags 2>&1) || push_rc=$?
    fi

    if [[ $push_rc -ne 0 ]]; then
        echo "Error: Push to $remote_url failed." >&2
        echo "" >&2
        echo "Git output:" >&2
        echo "$push_output" >&2
        echo "" >&2
        echo "This may be an authentication or permissions issue. To configure push access:" >&2
        echo "  - SSH: Ensure your SSH key is added (ssh-add ~/.ssh/id_ed25519)" >&2
        echo "  - HTTPS: Configure a personal access token (git credential-store)" >&2
        echo "  - Permissions: Verify you have write access to the remote repository" >&2
        exit 1
    fi

    if [[ -n "$specific_tag" ]]; then
        echo "Pushed tag: $specific_tag"
    else
        echo "Pushed all tags to $remote_url"
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

cmd_remote() {
    if [[ $# -lt 1 ]]; then
        # No URL: print current remote if set
        local current
        current="$(_read_fixture_repo_url)"
        if [[ -n "$current" ]]; then
            echo "Current fixture remote: $current"
        else
            echo "No fixture remote configured."
            echo "Usage: fixture remote <url>"
        fi
        return 0
    fi

    local url="$1"

    # Verify URL access (captures the working URL, may convert HTTPS→SSH)
    local verified_url
    verified_url="$(cmd_verify_url "$url")" || return 1

    # Check if already configured
    local current
    current="$(_read_fixture_repo_url)"
    if [[ -n "$current" ]]; then
        if [[ "$current" == "$verified_url" ]]; then
            echo "Remote is already set to $current"
            return 0
        fi
        echo "Remote is already set to $current. Replace with $verified_url? [y/n]"
        read -r reply
        if [[ "$reply" != "y" && "$reply" != "Y" ]]; then
            echo "Keeping current remote."
            return 0
        fi
    fi

    local project_root
    project_root="$(resolve_project_root)"
    local repo_path="$project_root/.purlin/runtime/fixture-repo"

    if [[ -d "$repo_path" ]]; then
        # Local repo exists — add remote and push
        local is_bare
        is_bare="$(git -C "$repo_path" rev-parse --is-bare-repository 2>/dev/null || echo "false")"
        if [[ "$is_bare" != "true" ]]; then
            echo "Error: $repo_path exists but is not a bare git repo." >&2
            return 1
        fi

        # Add or update the origin remote
        if git -C "$repo_path" remote get-url origin >/dev/null 2>&1; then
            git -C "$repo_path" remote set-url origin "$verified_url"
        else
            git -C "$repo_path" remote add origin "$verified_url"
        fi

        # Push all tags and branches
        local tag_count=0
        local tags
        tags="$(git -C "$repo_path" tag -l 2>/dev/null)" || true
        if [[ -n "$tags" ]]; then
            tag_count="$(echo "$tags" | wc -l | tr -d ' ')"
            git -C "$repo_path" push origin --tags 2>/dev/null || {
                echo "Warning: Failed to push tags to remote." >&2
            }
        fi

        # Push branches too
        git -C "$repo_path" push origin --all 2>/dev/null || true

        # Save to config
        _write_fixture_repo_url "$verified_url"
        echo "Synced $tag_count fixture tags to remote."
    else
        # No local repo — clone from remote or init if empty
        local ref_count
        ref_count="$(git ls-remote "$verified_url" 2>/dev/null | wc -l | tr -d ' ')" || ref_count=0

        mkdir -p "$(dirname "$repo_path")"

        if [[ "$ref_count" -gt 0 ]]; then
            # Remote has content — bare clone it
            git clone --bare "$verified_url" "$repo_path" >/dev/null 2>&1
        else
            # Remote is empty — init locally and add remote
            git init --bare "$repo_path" >/dev/null 2>&1
            git -C "$repo_path" remote add origin "$verified_url"
        fi

        # Save to config
        _write_fixture_repo_url "$verified_url"
        echo "Fixture repo configured. Remote: $verified_url"
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
    verify-url)
        cmd_verify_url "$@"
        ;;
    remote)
        cmd_remote "$@"
        ;;
    push)
        cmd_push "$@"
        ;;
    prune)
        cmd_prune "$@"
        ;;
    *)
        echo "Error: Unknown subcommand: $subcommand" >&2
        usage
        ;;
esac
