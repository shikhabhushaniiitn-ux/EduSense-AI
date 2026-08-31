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
    """Extract text from an uploaded PDF."""

    pdf_document = read_pdf(uploaded_file)

    text = ""

    for page in pdf_document:
        text += page.get_text()

    pdf_document.close()

    return text


def get_pdf_page_count(uploaded_file):
    """Return the number of pages in a PDF."""

    pdf_document = read_pdf(uploaded_file)

    page_count = len(pdf_document)

    pdf_document.close()

    return page_count