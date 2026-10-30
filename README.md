# ryer

**R**eview **Y**our **E**xtracted **R**esults
A little GUI for reviewing extracted data by comparing your spreadsheet with corresponding PDFs.

WIP!

## Running

Needs `PyQt6` and `pymupdf`.

```
python src/main.py
```

Use File > Load CSV, then select a row. The CSV needs two columns:

- `pdf_path`: absolute, or relative to the CSV's folder or any folder above it.
- `data_quote`: quotes to highlight, as `[location] quote; [location] quote`.

If a quote can't be found, for example on a scanned page, the viewer opens the page named in its location and shows "page only". A location of `pdf p. 8` is the PDF's own page. A location of `p. 342` is the printed page, which needs an optional `source` column whose citation has a page range as long as the PDF, such as `339-349` for 11 pages.
