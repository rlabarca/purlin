#!/bin/bash
# identity.sh — Terminal identity helper (title + iTerm2 badge).
# Source this file; do not execute directly.
#
# Functions:
#   set_term_title <text>     Set tab/window title (all terminals)
#   clear_term_title          Reset title to default
#   set_iterm_badge <text>    Set iTerm2 badge (no-op if not iTerm2)
#   clear_iterm_badge         Clear iTerm2 badge (no-op if not iTerm2)
#   set_agent_identity <text> Set both title and badge
#   clear_agent_identity      Clear both title and badge

# --- Terminal Title (universal) ---

set_term_title() {
    local text="$1"
    if [ -e /dev/tty ]; then
        printf '\033]0;%s\007' "$text" > /dev/tty
    else
        printf '\033]0;%s\007' "$text"
    fi
}

clear_term_title() {
    if [ -e /dev/tty ]; then
        printf '\033]0;\007' > /dev/tty
    else
        printf '\033]0;\007'
    fi
}

# --- iTerm2 Badge (iTerm2 only) ---

set_iterm_badge() {
    [ "${TERM_PROGRAM:-}" = "iTerm.app" ] || return 0
    local text="$1"
    local encoded
    encoded=$(echo -n "$text" | base64 | tr -d '\n')
    if [ -e /dev/tty ]; then
        printf '\e]1337;SetBadgeFormat=%s\a' "$encoded" > /dev/tty
    else
        printf '\e]1337;SetBadgeFormat=%s\a' "$encoded"
    fi
}

clear_iterm_badge() {
    [ "${TERM_PROGRAM:-}" = "iTerm.app" ] || return 0
    if [ -e /dev/tty ]; then
        printf '\e]1337;SetBadgeFormat=\a' > /dev/tty
    else
        printf '\e]1337;SetBadgeFormat=\a'
    fi
}

# --- Convenience wrappers ---

set_agent_identity() {
    local text="$1"
    set_term_title "$text"
    set_iterm_badge "$text"
}

clear_agent_identity() {
    clear_term_title
    clear_iterm_badge
}
