# 24dots_functions.sh -- Print to impact printer with panel or custom config.
# Copyright (C) 2026  Dillon Feeney.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# See the COPYING file for licence details.
#
# Created: 2026-05-20
# Updated: 2026-05-20
#
# ---------------------------------------------------------------------------
# Printing helpers (ESC/P + CUPS).  Require `$PRINTER` to name a valid lp
# destination.  Source this file from ~/.bashrc (or ~/.profile) to load:
#   `[ -f /path/to/24dots_functions.sh ] && . /path/to/24dots_functions.sh`
# Both functions depend on: fmt, lp (CUPS).  print_explicit assumes the
# target printer understands ESC/P control codes.
# ---------------------------------------------------------------------------
# Notes:
# Define $PRINTER before or alongside these functions, for example:
#   `export PRINTER=office`
# in the same file or in your environment setup.  After editing the sourced
# file, reload it with:
#   `. /path/to/24dots_functions.sh`
# or open a new shell.  Confirm loading with:
#   `declare -F 24dots_panel 24dots_explicit`
# which lists the names if defined.
# ---------------------------------------------------------------------------

PRINTER=LQ590_text

24dots_panel() {
# 24dots_panel WIDTH [FILE]
# Copyright (C) 2026  Dillon Feeney
#
# Reflow text to WIDTH columns with fmt and send it to $PRINTER (via CUPS lp).
#
# WIDTH  wrap width in columns; defaults to 80 if omitted
# FILE   file to print; if omitted, reads standard input
#
# If no FILE is given and standard input is a terminal (nothing piped or
# redirected), prints a usage message to stderr and returns 1.
#
# Examples:
#   24dots_panel 60 notes.txt          # wrap file at 60 columns
#   cat notes.txt | 24dots_panel 60    # wrap piped input at 60 columns
#   24dots_panel < notes.txt           # redirected input, default 80 columns
#   24dots_panel                       # error: no input
#
# Created: 2026-05-20
# Updated: 2026-05-20
    local width=${1:-80}
    if [ -t 0 ] && [ -z "$2" ]; then
        echo "Usage: 24dots_panel WIDTH [file]" >&2
        return 1
    fi
    if [ -n "$2" ]; then
        fmt -w "$width" "$2" | lp -d "$PRINTER"
    else
        fmt -w "$width" | lp -d "$PRINTER"
    fi
}

24dots_explicit() {
# 24dots_explicit FONT PITCH [FILE...]
# Copyright (C) 2026  Dillon Feeney
#
# Format text and send it to $PRINTER (via CUPS lp) with ESC/P control codes.
#
# FONT   typeface: roman|sans|courier|prestige|script
#        (unrecognised value leaves the reset-default typeface unchanged)
# PITCH  characters per inch: 10|12|15|17|20, mapping to wrap widths
#        80|96|120|136|160 columns respectively
#        (unrecognised value defaults to width 80 and sends no pitch command)
# FILE   one or more files to print; if omitted, reads standard input
#
# Emits a printer reset and letter-quality mode, selects the font and pitch,
# reflows the text to the pitch-appropriate width with fmt, and appends a
# form feed to eject the page.
#
# Examples:
#   24dots_explicit courier 12 report.txt           # single file
#   24dots_explicit roman 10 ch1.txt ch2.txt        # multiple files, one job
#   ps aux | 24dots_explicit sans 15                # piped input
#   24dots_explicit prestige 17 < notes.txt         # redirected input
#   PRINTER=backoffice 24dots_explicit courier 12 report.txt  # per-call printer
#
# Created: 2026-05-20
# Updated: 2026-05-20
    local font="$1"
    local pitch="$2"
    shift 2

    local width
    case "$pitch" in
        10) width=80 ;;
        12) width=96 ;;
        15) width=120 ;;
        17) width=136 ;;
        20) width=160 ;;
        *)  width=80 ;;
    esac

    {
        printf '\033@\033x\001'
        case "$font" in
            roman)    printf '\033k\000' ;;
            sans)     printf '\033k\001' ;;
            courier)  printf '\033k\002' ;;
            prestige) printf '\033k\003' ;;
            script)   printf '\033k\004' ;;
        esac
        case "$pitch" in
            10) printf '\022\033P' ;;
            12) printf '\022\033M' ;;
            15) printf '\022\033g' ;;
            17) printf '\022\033P\017' ;;
            20) printf '\022\033M\017' ;;
        esac
        if [ -n "$1" ]; then
            fmt -w "$width" "$@"
        else
            fmt -w "$width"
        fi
        printf '\f'
    } | lp -d "$PRINTER"
}
