import fitz


def read_pdf(uploaded_file):
    """Open the uploaded PDF once."""

    pdf_bytes = uploaded_file.getvalue()

    pdf_document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    return pdf_document


def extract_text_from_pdf(uploaded_file):
    """
    Extract text from an uploaded PDF.

    BUGFIX: the previous version used page.get_text() (default
    "text" mode) and simply concatenated every page's text with
    "+=". Two problems with that:

    1. get_text()'s default reading order is based on the PDF's
       internal draw order, not visual position - for PDFs
       exported from PowerPoint (very common for lecture slides),
       small text boxes like a footer ("Presented by: Dr. ...
       Assistant Professor  Department of ...") are often drawn
       as several separate, closely-spaced runs. Those runs can
       get concatenated with NO whitespace between them ("Bhopale.
       Assistant ProfessorDepartment of..."), which then defeats
       both heading detection (it's not a clean short line anymore)
       and boilerplate-repeat detection (no two pages produce an
       identical line to match against).
    2. Concatenating page texts with a bare "+=" means the last
       line of one page can run directly into the first line of
       the next page if the page's own text doesn't end in a
       newline.

    Fix: extract text BLOCK BY BLOCK (each visually distinct text
    box becomes its own block), sort blocks top-to-bottom /
    left-to-right, and join them with explicit newlines - so every
    visually separate piece of text (including a footer credit
    line) always ends up on its own clean line. Pages are joined
    with a form-feed character ("\\x0c"), which Python's
    str.splitlines() already treats as a line boundary, so nothing
    downstream needs to change to benefit from the page boundary -
    it also lets boilerplate-detection code reason about "how many
    pages" a repeated line appeared on if it ever needs to.
    """

    pdf_document = read_pdf(uploaded_file)

    page_texts = []

    for page in pdf_document:

        blocks = page.get_text("blocks")

        # Sort top-to-bottom, then left-to-right, so reading
        # order matches how a human would actually read the page.
        blocks = sorted(
            blocks,
            key=lambda block: (round(block[1], 1), block[0])
        )

        block_lines = [
            block[4].strip()
            for block in blocks
            if block[4] and block[4].strip()
        ]

        page_texts.append(
            "\n".join(block_lines)
        )

    pdf_document.close()

    return "\x0c".join(page_texts)


def get_pdf_page_count(uploaded_file):
    """Return the number of pages in a PDF."""

    pdf_document = read_pdf(uploaded_file)

    page_count = len(pdf_document)

    pdf_document.close()

    return page_count