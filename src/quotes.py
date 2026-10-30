import html
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import pymupdf

#a quote is only accepted if this share of it was found in one run
MIN_PARTIAL_MATCH = 0.6
MIN_CELL_CHARS = 4

#data_quote looks like: [table 2, p. 342] | Banksia | R | 5 |; [text, p. 3] Some sentence.
TAG_PATTERN = re.compile(r"(?:^|;\s+)\[([^\[\]]+)\]\s*")
ELLIPSIS_PATTERN = re.compile(r"\[?(?:\.\s?){3,}\]?|\[?…\]?")

#labels give either the pdf's own page ("pdf p. 8") or the page printed on the paper ("p. 342")
PAGE_PATTERN = re.compile(r"\b(pdf\s+)?pp?\.\s*(\d+)")
PAGE_RANGE_PATTERN = re.compile(r"(\d+)\s*[-–—]\s*(\d+)")


@dataclass
class Quote:
    label: str
    text: str
    page: int = -1
    rects: list = field(default_factory=list)
    match: str = "not found"


def normalise(text):
    #keep letters and digits only, so line breaks and hyphenation can't stop a match
    text = unicodedata.normalize("NFKC", text).casefold()
    return "".join(char for char in text if char.isalnum())


def parse_quotes(data_quote):
    tags = list(TAG_PATTERN.finditer(data_quote))
    if not tags:
        return [Quote("quote", data_quote.strip())] if data_quote.strip() else []

    quotes = []
    for index, tag in enumerate(tags):
        end = tags[index + 1].start() if index + 1 < len(tags) else len(data_quote)
        quotes.append(Quote(tag.group(1), data_quote[tag.end():end].strip()))
    return quotes


class PageIndex:
    #one long normalised string for a page, which remembers the word behind each character
    def __init__(self, page):
        self.words = page.get_text("words", sort=False)
        self.text = ""
        self.char_to_word = []

        for word_index, word in enumerate(self.words):
            characters = normalise(word[4])
            self.text += characters
            self.char_to_word += [word_index] * len(characters)

    def rects(self, start, end):
        return self.line_rects({self.char_to_word[i] for i in range(start, end)})

    def line_rects(self, word_indexes):
        lines = {}
        for word_index in sorted(word_indexes):
            word = self.words[word_index]
            rect = pymupdf.Rect(word[:4])
            line = (word[5], word[6])
            lines[line] = lines[line] | rect if line in lines else rect
        return list(lines.values())

    def row_rects(self, start, end):
        #every word sharing a horizontal band with the matched cell
        first = pymupdf.Rect(self.words[self.char_to_word[start]][:4])
        middle = (first.y0 + first.y1) / 2
        return self.line_rects({
            index for index, word in enumerate(self.words)
            if word[1] <= middle <= word[3]
        })


def find_exact(index_pages, needle):
    for page_number, page in enumerate(index_pages):
        start = page.text.find(needle)
        if start >= 0:
            return page_number, page.rects(start, start + len(needle))
    return None


def find_partial(index_pages, needle):
    best_size = 0
    best = None
    for page_number, page in enumerate(index_pages):
        matcher = SequenceMatcher(None, page.text, needle, autojunk=False)
        run = matcher.find_longest_match(0, len(page.text), 0, len(needle))
        if run.size > best_size:
            best_size = run.size
            best = (page_number, page, run.a)

    if best is None or best_size < len(needle) * MIN_PARTIAL_MATCH:
        return None
    page_number, page, start = best
    return page_number, page.rects(start, start + best_size)


def find_table_row(index_pages, text):
    cells = [normalise(cell) for cell in text.split("|")]
    cells = [cell for cell in cells if cell]
    names = sorted(
        (cell for cell in cells if len(cell) >= MIN_CELL_CHARS and not cell.isdigit()),
        key=len,
        reverse=True,
    )
    if not names:
        return None

    #the same species can sit in several tables, so take the row holding the most cells
    best_score = 0
    best = None
    for page_number, page in enumerate(index_pages):
        start = page.text.find(names[0])
        while start >= 0:
            rects = page.row_rects(start, start + len(names[0]))
            row = normalise("".join(
                word[4] for word in page.words
                if any(pymupdf.Rect(word[:4]).intersects(rect) for rect in rects)
            ))
            score = sum(cell in row for cell in cells)
            if score > best_score:
                best_score = score
                best = (page_number, rects)
            start = page.text.find(names[0], start + 1)
    return best


def plain_text(text):
    #some quotes hold html table rows copied from the paper's markdown
    text = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", " | ", text)
    return html.unescape(re.sub(r"<[^>]+>", " ", text))


def locate(index_pages, quote):
    pieces = ELLIPSIS_PATTERN.split(plain_text(quote.text))

    #table quotes are the species' row, then "...", then the table's header row
    if "|" in pieces[0]:
        found = find_table_row(index_pages, pieces[0])
        if found:
            quote.page, quote.rects = found
            quote.match = "table row"
            return

    pieces = [normalise(piece) for piece in pieces]
    pieces = [piece for piece in pieces if piece]

    for piece in pieces:
        found = find_exact(index_pages, piece)
        match = "exact"
        if not found and len(piece) >= MIN_CELL_CHARS:
            found = find_partial(index_pages, piece)
            match = "partial"
        if found:
            if quote.page < 0:
                quote.page = found[0]
                quote.match = match
            #highlights are drawn page by page, so only keep pieces on the first page
            if found[0] == quote.page:
                quote.rects += found[1]


def first_printed_page(source, page_count):
    #the citation's page range only counts if it is as long as the pdf, e.g. 339-349 for 11 pages
    for first, last in PAGE_RANGE_PATTERN.findall(source):
        if int(last) - int(first) + 1 == page_count:
            return int(first)
    return None


def page_from_label(label, first_printed, page_count):
    found = PAGE_PATTERN.search(label)
    if not found:
        return -1

    if found.group(1):
        page = int(found.group(2)) - 1
    elif first_printed is not None:
        page = int(found.group(2)) - first_printed
    else:
        return -1
    return page if 0 <= page < page_count else -1


def find_quotes(index_pages, data_quote, source=""):
    quotes = parse_quotes(data_quote)
    page_count = len(index_pages)
    first_printed = first_printed_page(source, page_count)

    for quote in quotes:
        locate(index_pages, quote)

        #scanned pages have no text to search, but the label still says where to look
        if quote.page < 0:
            quote.page = page_from_label(quote.label, first_printed, page_count)
            if quote.page >= 0:
                quote.match = "page only"
    return quotes
