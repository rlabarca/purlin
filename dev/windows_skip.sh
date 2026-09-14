#!/usr/bin/env bash
# Is this shell running on Windows? Sourced by the `*.test.sh` wrappers at the
# project root, which is the one place the answer is needed and so the one
# place it is written.
#
# The end-to-end suites below those wrappers need a POSIX shell: they generate
# ssh keys, sign commits and read `%G?` back, and Git Bash is not one for that.
# The proofs they serve carry `@env(linux)`, so the Linux job proves them and a
# Windows run lists them as needing linux rather than reporting a failure that
# is about the host.
#
# Three answers, because one is not enough. `OS` is set by Windows itself and
# every shell there inherits it, whichever bash the run found. `OSTYPE` is set
# by bash and reads `msys` or `cygwin` there. `uname` is the last of the three
# because it is an external command: a bash that is on Windows without the
# rest of a Git Bash installation has no `uname` to run, and a check that asks
# only `uname` then answers "not Windows" and the suite runs anyway.
purlin_on_windows() {
  [ "${OS:-}" = "Windows_NT" ] && return 0
  case "${OSTYPE:-}" in
    msys*|cygwin*|win32*) return 0 ;;
  esac
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*|Windows*) return 0 ;;
  esac
  case "$(uname -o 2>/dev/null)" in
    Msys|Cygwin|Windows*) return 0 ;;
  esac
  return 1
}

# Say so and exit 0 when this is Windows; return and let the wrapper carry on
# when it is not.
purlin_skip_on_windows() {
  if purlin_on_windows; then
    echo "This suite does not run under Git Bash on Windows. Its proofs carry"
    echo "@env(linux), so the Linux job proves them."
    exit 0
  fi
}
