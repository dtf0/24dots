# 24dots

A diagnostic and calibration script for the Epson LQ-590II 24-pin impact printer
running on Debian or Raspberry Pi OS via CUPS.  Prints a one-page sample showing
every internal font and pitch combination the printer supports, along with
column rulers and a bottom-margin measurement strip.

## Purpose

The LQ-590II has nine font/quality panel selections (USD, HSD, Draft, Roman,
Sans Serif, Courier, Prestige, Script, Others) and up to six pitches per font
(10, 12, 15, 17, 20 cpi, and PS proportional).  This script exercises every
supported combination on a single sheet of 9.5 x 11 fanfold continuous paper so
the operator can:

- Verify all internal fonts and pitches render correctly
- Compare typeface, weight, and quality of each font visually
- Confirm that ESC/P 2 command transmission through CUPS is intact
- Measure where text lands relative to the top and bottom perforations for
  margin calibration

## Requirements

Hardware:

- Epson LQ-590II (or compatible 24-pin ESC/P 2 printer)
- 9.5 x 11 inch US fanfold continuous paper loaded on the rear push
  tractor
- USB connection to the host

Software:

- Debian 12 or Raspberry Pi OS Bookworm
- CUPS with a raw queue named LQ590_text targeting the printer
- Bash (the script is not POSIX sh portable; it relies on bash builtin
  `printf` behaviour for octal escape interpretation)

Printer configuration (set once via the front panel):

- Software emulation:  ESC/P2
- Page length for rear tractor:  11 inches
- Skip over perforation:  Off
- Auto tear off:  On (recommended)
- Top-of-form:  1/2 inch below perforation (set via Micro Adjust)

## Installation

Save the script as `/usr/local/bin/24dots` and make it
executable:

```
sudo install -m 755 24dots /usr/local/bin/24dots
```

Or copy and chmod manually:

```
sudo cp 24dots.v6.sh /usr/local/bin/24dots
sudo chmod +x /usr/local/bin/24dots
```

The script targets a CUPS queue named "LQ590_text" by default.  If the queue is
named differently, edit the PRINTER variable near the top of the script.

## Usage

Ensure paper is loaded on the rear push tractor and the printer is at
top-of-form.  Run:

```
24dots
```

The script prints continuously and does not advance to the next page when
finished.  Paper is left positioned at the last printed line so the
bottom-margin measurement can be taken.  Press Tear Off/Bin on the printer (or
wait for Auto tear off to fire) to advance the page for tearing.

## Output

![Scan of tractor-feed paper with this script's output printed on it.](/output.jpg)

### Output layout

The printed page contains:

  1. A column ruler at 10 cpi marking every 10 columns up to column 80
  2. A second column ruler at 20 cpi marking every 10 columns up to
     column 160 (both rulers should end at the same physical position
     on the page if the printer is calibrated correctly)
  3. A title line identifying the test and paper format
  4. Six lines for Roman font (10, 12, 15, 17, 20 cpi, and PS)
  5. Six lines for Sans Serif (same pitches)
  6. Six lines for Courier (same pitches)
  7. Five lines for Prestige (10, 12, 17, 20 cpi, PS -- no 15 cpi)
  8. Five lines for Script (same pitches as Prestige)
  9. Five lines for Draft mode (10, 12, 15, 17, 20 cpi)
 10. A ruler header
 11. 18 numbered ruler lines for bottom-margin measurement

Total:  60 lines = 10 inches at 6 LPI.  With the 1/2 inch top-of-form
offset, the last ruler line lands 1/2 inch above the next perforation,
giving symmetric top and bottom margins on standard 11-inch fanfold.

### Interpreting the output

Each printed line should appear in a visibly distinct typeface and
pitch.  Expected observations:

  - Within each font, characters get narrower as cpi increases.  10 cpi is
    widest, 20 cpi narrowest.
  - 15 cpi and 17 cpi look similar but not identical (15 cpi is proportionally
    wider).
  - PS (proportional) shows variable character widths -- 'i' narrower than 'W'.
  - Roman is a serif typeface; Sans Serif has no serifs; Courier is monospace
    with serifs; Prestige is a slab serif; Script is cursive.
  - Draft lines print noticeably faster and lighter than LQ lines.

Common anomalies that indicate a configuration issue:

  - All pitches within a font appear identical: the printer is collapsing
    condensed modes (firmware issue or wrong base pitch sequence -- v4 of the
    script had this problem before v6 corrected it).
  - All fonts look like Roman: ESC k commands are not reaching the printer.
    Check the queue is raw and not filtering.
  - Letters appear at the start of lines (e.g. "PRoman 10 cpi"): the ESC byte is
    being stripped from font/pitch commands.  Check shell is bash, not dash.
  - "000Roman" or similar numeric prefix: a broken font helper that emits an
    octal digit string rather than the byte (v3 issue).

### Testing draft sub-modes (USD, HSD)

The Draft block at the end of the page uses ESC x 0 to enter draft quality.  The
actual speed within draft mode (Normal Draft, HSD, or USD) is controlled by the
printer's panel Font button, not by ESC/P 2 commands.

To compare all three:

  1. Set panel Font selection to Draft, run the script, label the
     output "Normal Draft"
  2. Set panel Font to HSD, run again, label "HSD"
  3. Set panel Font to USD, run again, label "USD"

The Draft block lines will print in whatever speed is currently selected on the
panel.

## ESC/P 2 command reference

Commands used by the script:

  | Sequence    | Bytes        | Purpose                          |
  |-------------|--------------|----------------------------------|
  | ESC @       | 0x1B 0x40    | Reset printer                    |
  | ESC x 1     | 0x1B 0x78 1  | Select LQ (Letter Quality) mode  |
  | ESC x 0     | 0x1B 0x78 0  | Select Draft mode                |
  | ESC k n     | 0x1B 0x6B n  | Select font n (0..7)             |
  | DC2         | 0x12         | Cancel condensed mode            |
  | ESC P       | 0x1B 0x50    | Set 10 cpi base pitch            |
  | ESC M       | 0x1B 0x4D    | Set 12 cpi base pitch            |
  | ESC g       | 0x1B 0x67    | Set 15 cpi base pitch            |
  | SI          | 0x0F         | Apply condensed mode             |
  | ESC SI      | 0x1B 0x0F    | Apply condensed mode (alt form)  |
  | ESC p 1     | 0x1B 0x70 1  | Enable proportional spacing      |
  | ESC p 0     | 0x1B 0x70 0  | Disable proportional spacing     |

Font numbers used:

  | n | Font         |
  |---|--------------|
  | 0 | Roman        |
  | 1 | Sans Serif   |
  | 2 | Courier      |
  | 3 | Prestige     |
  | 4 | Script       |
  | 5 | OCR-B        |
  | 6 | (varies)     |
  | 7 | Orator       |

Condensed-mode interaction:

The combinations of base pitch and condensed mode produce the effective
pitches:

  | Base | + Condensed | Effective cpi |
  |------|-------------|---------------|
  | 10   | no          | 10            |
  | 12   | no          | 12            |
  | 15   | no          | 15            |
  | 10   | yes (SI)    | 17.1          |
  | 12   | yes (SI)    | 20            |

Each pitch helper in v6 cancels condensed first (DC2), then sets the
correct base pitch, and applies condensed where needed.  This guarantees
five distinct widths regardless of prior state.

## Limitations

- Tested only on Epson LQ-590II.  Other 24-pin Epson printers with ESC/P 2
  support (LQ-2090II, LQ-590, FX series) may work but font sets and supported
  pitches differ.
- Assumes a raw CUPS queue named LQ590_text.  A filtered queue with a PPD-based
  driver will rasterise the entire stream and produce different output
  (typically a coarse bitmap of Helvetica-like text instead of native printer
  fonts).
- Hardcoded for 9.5 x 11 US fanfold paper at 6 LPI.  Other paper sizes or LPI
  settings require adjusting the ruler widths and ruler line count in the
  script.
- Assumes 1/2 inch top-of-form offset set via Micro Adjust.  Without that, the
  layout will beoff vertically but still readable.
- Bash-only.  Will not run under dash or POSIX sh.

## `24dots_functions.sh`

Printing helpers (ESC/P + CUPS).  Require `$PRINTER` to name a valid lp
destination.  Source this file from ~/.bashrc (or ~/.profile) to load:
```sh
[ -f ~/.shell_functions ] && . ~/.shell_functions
```
Both functions depend on: fmt, lp (CUPS).  print_explicit assumes the target
printer understands ESC/P control codes.

Notes:
Define $PRINTER before or alongside these functions, for example:
```sh
export PRINTER=office
```
in the same file or in your environment setup.

After editing the sourced file, reload it with:
```sh
. path/to/24dots_functions.sh
```
or open a new shell.

Confirm loading with:
```sh
declare -F print_panel print_explicit
```
which lists the names if defined.

## See also

- Epson LQ-590II User's Guide (NPD5799-02 EN)
  - https://files.support.epson.com/pdf/lq590ii/lq590iiug.pdf
- ESC/P 2 reference (pp. 156-157 of the user's guide)
- `foomatic-db-compressed-ppds` package for the LQ-2550 Foomatic PPD (used for
  graphical PDF printing through a separate filtered queue)

## Licence

This project is licensed per file:

- `24dots` and `24dots_functions.sh` -- GNU GPL v3 or later
- `output.jpg` -- Creative Commons Attribution-ShareAlike 4.0
- `README.md` (this file) -- GNU Free Documentation License 1.3

Full per-file licensing is recorded in [COPYING](COPYING), in the
machine-readable Debian copyright format.  Licence texts are in the
`LICENSES/` directory.

---

Copyright (C)  2026  Dillon Feeney.  Permission is granted to copy,
distribute and/or modify this document under the terms of the GNU Free
Documentation License, Version 1.3 or any later version published by
the Free Software Foundation; with no Invariant Sections, no
Front-Cover Texts, and no Back-Cover Texts.  A copy of the licence is
in LICENSES/GFDL-1.3-no-invariants-only.txt.
