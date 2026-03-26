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
#                                       If project given, title = "project - text"
#   clear_agent_identity      Clear title + badge + Warp tab
#   update_session_identity <mode> [project]  Detect context, format badge,
#                                             dispatch to all environments
#   purlin_detect_env         Print detected environments
#
# TTY resolution: /dev/tty may not be accessible in sandboxed environments
# (e.g. Claude Code). We resolve the real TTY device from the parent process
# as a fallback, ensuring escape sequences reach the correct terminal session.

# --- TTY resolution ---
# Resolve once at source time. Prefer /dev/tty, fall back to parent's TTY device.
_PURLIN_TTY=""
if [ -e /dev/tty ] && (echo -n > /dev/tty) 2>/dev/null; then
    _PURLIN_TTY="/dev/tty"
elif [ -n "${PPID:-}" ]; then
    _parent_tty=$(ps -p "$PPID" -o tty= 2>/dev/null | tr -d ' ')
    if [ -n "$_parent_tty" ] && [ "$_parent_tty" != "??" ] && [ -e "/dev/$_parent_tty" ]; then
        _PURLIN_TTY="/dev/$_parent_tty"
    fi
    unset _parent_tty
fi

# --- Environment Detection ---
# Detect once at source time. Terminal type cannot change mid-session.
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
# Warp's OSC 0 support for tab naming is unreliable in some versions
# (ref: warp-dev/Warp#8330). Separate from set_term_title so a proprietary
# Warp sequence can replace OSC 0 without touching the universal title function.

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
# Computes badge from mode + branch/worktree context.
#
# Usage: update_session_identity <mode_display> [project]
#   mode_display: "Engineer", "PM", "QA", "Purlin", or custom label
#   project: project name (optional, used for title prefix)
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
    local mode_display="$1"
    local project="${2:-}"
    local context
    context="$(_purlin_detect_context)"

    if [ -n "$context" ]; then
        _PURLIN_LAST_BADGE="$mode_display ($context)"
    else
        _PURLIN_LAST_BADGE="$mode_display"
    fi

    if [ -n "$project" ]; then
        _PURLIN_LAST_TITLE="$project - $_PURLIN_LAST_BADGE"
    else
        _PURLIN_LAST_TITLE="$_PURLIN_LAST_BADGE"
    fi

    set_term_title "$_PURLIN_LAST_TITLE"
    set_iterm_badge "$_PURLIN_LAST_BADGE"
    set_warp_tab_name "$_PURLIN_LAST_TITLE"
}
