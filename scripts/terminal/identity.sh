#!/bin/bash
# identity.sh — Terminal identity helper (title + badge + tab name).
# Source this file; do not execute directly.
#
# Functions:
#   set_term_title <text>     Set tab/window title (all terminals)
#   clear_term_title          Reset title to default
#   set_iterm_badge <text>    Set iTerm2 badge (no-op if not iTerm2)
#   clear_iterm_badge         Clear iTerm2 badge (no-op if not iTerm2)
#   set_warp_tab_name <text>  Set Warp tab name (no-op if not Warp)
#   clear_warp_tab_name       Clear Warp tab name (no-op if not Warp)
#   set_agent_identity <text> [project]  Set title + badge + Warp tab
#   clear_agent_identity      Clear title + badge + Warp tab
#   update_session_identity [label]  Detect context, format badge,
#                                    dispatch to all environments
#   purlin_detect_env         Print detected environments
#
# Identity format: (<branch_or_worktree>) <label>
#   Examples: (main) purlin, (dev/0.8.6) purlin, (W1) building webhook_delivery
#
# TTY resolution: /dev/tty may not be accessible in sandboxed environments
# (e.g. Claude Code). We resolve the real TTY device from the parent process
# as a fallback, ensuring escape sequences reach the correct terminal session.

# --- TTY resolution ---
_PURLIN_TTY=""
_PURLIN_TTY_CACHE="${PURLIN_PROJECT_ROOT:-.}/.purlin/cache/session_tty"
if [ -e /dev/tty ] && (echo -n > /dev/tty) 2>/dev/null; then
    _PURLIN_TTY="/dev/tty"
elif [ -n "${PPID:-}" ]; then
    _parent_tty=$(ps -p "$PPID" -o tty= 2>/dev/null | tr -d ' ')
    if [ -n "$_parent_tty" ] && [ "$_parent_tty" != "??" ] && [ -e "/dev/$_parent_tty" ]; then
        _PURLIN_TTY="/dev/$_parent_tty"
    fi
    unset _parent_tty
fi
# Fallback: read cached TTY from session init (survives teardown)
if [ -z "$_PURLIN_TTY" ] && [ -f "$_PURLIN_TTY_CACHE" ]; then
    _cached_tty=$(cat "$_PURLIN_TTY_CACHE" 2>/dev/null)
    if [ -n "$_cached_tty" ] && [ -e "$_cached_tty" ]; then
        _PURLIN_TTY="$_cached_tty"
    fi
    unset _cached_tty
fi

# --- Environment Detection ---
_PURLIN_ENV_ITERM=false
_PURLIN_ENV_WARP=false
_PURLIN_ENV_TITLE=true

case "${TERM_PROGRAM:-}" in
    iTerm.app)    _PURLIN_ENV_ITERM=true ;;
    WarpTerminal) _PURLIN_ENV_WARP=true ;;
esac

purlin_detect_env() {
    echo "title:$_PURLIN_ENV_TITLE iterm:$_PURLIN_ENV_ITERM warp:$_PURLIN_ENV_WARP"
}

# Persist resolved TTY so SessionEnd hooks can find it during teardown
purlin_save_tty() {
    if [ -n "$_PURLIN_TTY" ]; then
        local cache_dir="${PURLIN_PROJECT_ROOT:-.}/.purlin/cache"
        mkdir -p "$cache_dir" 2>/dev/null
        echo "$_PURLIN_TTY" > "$cache_dir/session_tty"
    fi
}

# Remove cached TTY (call during SessionEnd after clearing identity)
purlin_cleanup_tty() {
    rm -f "${PURLIN_PROJECT_ROOT:-.}/.purlin/cache/session_tty"
}

# Write escape sequence to the resolved TTY (or stdout as last resort)
_purlin_tty_printf() {
    if [ -n "$_PURLIN_TTY" ]; then
        printf "$@" > "$_PURLIN_TTY" 2>/dev/null || printf "$@"
    else
        printf "$@"
    fi
}

# --- Terminal Title (universal) ---

set_term_title() {
    local text="$1"
    _purlin_tty_printf '\033]0;%s\007' "$text"
}

clear_term_title() {
    _purlin_tty_printf '\033]0;\007'
}

# --- iTerm2 Badge (iTerm2 only) ---

set_iterm_badge() {
    [ "$_PURLIN_ENV_ITERM" = true ] || return 0
    local text="$1"
    local encoded
    encoded=$(echo -n "$text" | base64 | tr -d '\n')
    _purlin_tty_printf '\e]1337;SetBadgeFormat=%s\a' "$encoded"
}

clear_iterm_badge() {
    [ "$_PURLIN_ENV_ITERM" = true ] || return 0
    _purlin_tty_printf '\e]1337;SetBadgeFormat=\a'
}

# --- Warp Terminal Tab Name (best-effort) ---

set_warp_tab_name() {
    [ "$_PURLIN_ENV_WARP" = true ] || return 0
    local text="$1"
    _purlin_tty_printf '\033]0;%s\007' "$text"
}

clear_warp_tab_name() {
    [ "$_PURLIN_ENV_WARP" = true ] || return 0
    _purlin_tty_printf '\033]0;\007'
}

# --- Convenience wrappers ---

set_agent_identity() {
    local text="$1"
    local project="${2:-}"
    if [ -n "$project" ]; then
        set_term_title "$project - $text"
        set_warp_tab_name "$project - $text"
    else
        set_term_title "$text"
        set_warp_tab_name "$text"
    fi
    set_iterm_badge "$text"
}

clear_agent_identity() {
    clear_term_title
    clear_iterm_badge
    clear_warp_tab_name
}

# --- Centralized Session Identity ---
# Single function to update all naming environments.
# Computes a unified label from branch/worktree context + task/project.
#
# Usage: update_session_identity [label]
#   label: project name or short task description (optional)
#
# Format: (<context>) <label>
#   Examples: (main) purlin, (dev/0.8.6) building webhook_delivery
#
# Side effects:
#   Sets $_PURLIN_LAST_BADGE and $_PURLIN_LAST_TITLE
#   Writes to all detected terminal environments

_PURLIN_LAST_BADGE=""
_PURLIN_LAST_TITLE=""

_purlin_detect_context() {
    if [ -f ".purlin_worktree_label" ]; then
        cat .purlin_worktree_label
    else
        git rev-parse --abbrev-ref HEAD 2>/dev/null
    fi
}

update_session_identity() {
    local label="${1:-}"
    local context unified
    context="$(_purlin_detect_context)"

    if [ -n "$context" ]; then
        unified="(${context})"
    else
        unified=""
    fi

    if [ -n "$label" ]; then
        unified="${unified} ${label}"
    fi

    # Trim leading space if no context
    unified="${unified# }"

    _PURLIN_LAST_BADGE="$unified"
    _PURLIN_LAST_TITLE="$unified"

    set_term_title "$_PURLIN_LAST_TITLE"
    set_iterm_badge "$_PURLIN_LAST_BADGE"
    set_warp_tab_name "$_PURLIN_LAST_TITLE"
}
