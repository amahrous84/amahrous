# Folio PDF Editor

A simple PDF editor that runs in the browser. Open `index.html` in Chrome, Edge, Firefox or Safari. Nothing is installed and nothing is uploaded: your files stay on your computer.

## What it does

| Area | Features |
| --- | --- |
| Edit | **Edit text**: click any line of text in the PDF to rewrite it · **Add text** (Helvetica, Times or Courier, any size, bold, color) · **Whiteout** to cover content |
| Mark up | Highlight · freehand draw · line · arrow · box · oval, with color, width, fill and opacity |
| Insert | Images (PNG, JPEG, WebP, GIF) · signatures you draw or type |
| Pages | Reorder by dragging thumbnails · rotate · duplicate · delete · insert blank pages · append another PDF (merge) |
| Forms | Fill a PDF's existing form fields (text, checkboxes, dropdowns, radio buttons) |
| General | Undo/redo · zoom and fit to width · drag-and-drop files · keyboard shortcuts |

**Save PDF** writes a new copy named `<name>-edited.pdf`. The original file is never changed. Added text is real, selectable PDF text. Characters the standard PDF fonts can't encode (Arabic, Chinese, emoji, and so on) are embedded as an image of the text.

## Shortcuts

`V` select · `E` edit text · `T` add text · `H` highlight · `D` draw · `L` line · `A` arrow · `R` box · `O` oval · `W` whiteout · `I` image · `S` sign
`Ctrl+Z` / `Ctrl+Shift+Z` undo/redo · `Ctrl+S` save · `Ctrl+O` open · `Del` delete selection · arrow keys nudge (hold `Shift` for 10 pt) · `Shift` while drawing keeps lines at 45° and boxes square

## Limits

- "Edit text" covers the old text with white and puts new text on top. That works well on plain backgrounds, and the font is matched to the nearest standard one (sans, serif or mono).
- Password-protected PDFs can't be opened. Remove the password in another app first.
- An internet connection is needed the first time the page loads, to fetch pdf.js and pdf-lib from cdnjs.

## Development

`src/app.html` is the source. Run `./build.sh` to regenerate the standalone `index.html`.
