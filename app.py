import streamlit as st
import fitz

# Page configuration
st.set_page_config(
    page_title="EduSense AI",
    page_icon="🎓",
    layout="wide"
)

# Header
st.title("🎓 EduSense AI")
st.subheader("AI-Powered Learning Assistant")

st.write(
    "Upload your study material and explore its content."
)

# Sidebar
with st.sidebar:
    st.header("📚 Learning Tools")
    st.write("Upload a PDF to get started.")

# PDF uploader
uploaded_file = st.file_uploader(
    "📄 Upload your study material",
    type=["pdf"]
)

if uploaded_file is not None:

    st.success(f"Uploaded: {uploaded_file.name}")

    # Open PDF
    pdf_document = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf"
    )

    # PDF information
    total_pages = len(pdf_document)

    st.info(f"📑 Total pages: {total_pages}")

    # Extract text
    text = ""

    for page in pdf_document:
        text += page.get_text()

    pdf_document.close()

    # Display extracted text
    if text.strip():

        st.subheader("📖 Extracted Content")

        st.text_area(
            "Study Material",
            text,
            height=500
        )

        # Basic statistics
        words = text.split()

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "📝 Words",
                len(words)
            )

        with col2:
            st.metric(
                "🔤 Characters",
                len(text)
            )

    else:

        st.warning(
            "⚠️ No text could be extracted from this PDF."
        )