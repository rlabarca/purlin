#!/bin/bash
# identity.sh — Terminal identity helper (title + iTerm2 badge).
# Source this file; do not execute directly.
#
# Functions:
#   set_term_title <text>     Set tab/window title (all terminals)
#   clear_term_title          Reset title to default
#   set_iterm_badge <text>    Set iTerm2 badge (no-op if not iTerm2)
#   clear_iterm_badge         Clear iTerm2 badge (no-op if not iTerm2)
#   set_agent_identity <text> [project]  Set both title and badge
#                                       If project given, title = "project - text"
#   clear_agent_identity      Clear both title and badge
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
    [ "${TERM_PROGRAM:-}" = "iTerm.app" ] || return 0
    local text="$1"
    local encoded
    encoded=$(echo -n "$text" | base64 | tr -d '\n')
    _purlin_tty_printf '\e]1337;SetBadgeFormat=%s\a' "$encoded"
}

clear_iterm_badge() {
    [ "${TERM_PROGRAM:-}" = "iTerm.app" ] || return 0
    _purlin_tty_printf '\e]1337;SetBadgeFormat=\a'
}

# --- Convenience wrappers ---

set_agent_identity() {
    local text="$1"
    local project="${2:-}"
    if [ -n "$project" ]; then
        set_term_title "$project - $text"
    else
        set_term_title "$text"
    fi
    set_iterm_badge "$text"
}

clear_agent_identity() {
    clear_term_title
    clear_iterm_badge
}
