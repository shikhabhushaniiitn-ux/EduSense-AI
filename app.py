import streamlit as st
import fitz

# Page configuration
st.set_page_config(
    page_title="EduSense AI",
    page_icon="🎓",
    layout="wide"
)

# Title
st.title("🎓 EduSense AI")
st.subheader("AI-Powered Learning Assistant")

st.write(
    "Upload your study material and EduSense AI "
    "will extract the content for learning."
)

# PDF uploader
uploaded_file = st.file_uploader(
    "📄 Upload your PDF study material",
    type=["pdf"]
)

# Process uploaded PDF
if uploaded_file is not None:

    st.success(f"Uploaded: {uploaded_file.name}")

    # Open PDF from memory
    pdf_document = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf"
    )

    # Extract text
    text = ""

    for page in pdf_document:
        text += page.get_text()

    pdf_document.close()

    # Display extracted text
    st.subheader("📖 Extracted Text")

    if text.strip():
        st.text_area(
            "PDF Content",
            text,
            height=500
        )
    else:
        st.warning(
            "No text could be extracted from this PDF."
        )