"""
Document parser for extracting text from uploaded files.
Supports PDF, DOCX, and plain text files.
"""

import mimetypes
from io import BytesIO
from typing import Optional, Tuple

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document
except ImportError:
    Document = None


class DocumentParser:
    """Parse documents and extract text content."""

    @staticmethod
    def detect_file_type(filename: str, content: bytes) -> str:
        """Detect file type from filename and content."""
        # Try to guess from filename first
        mime_type, _ = mimetypes.guess_type(filename)

        if mime_type:
            return mime_type

        # Check file signature/magic bytes
        if content.startswith(b"%PDF"):
            return "application/pdf"
        elif content.startswith(b"PK\x03\x04"):  # ZIP-based formats (DOCX, etc.)
            if filename.lower().endswith(".docx"):
                return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        # Default to text
        return "text/plain"

    @staticmethod
    def parse_document(filename: str, content: bytes) -> Tuple[str, Optional[str]]:
        """
        Parse document and extract text.

        Returns:
            Tuple of (extracted_text, error_message)
        """
        try:
            file_type = DocumentParser.detect_file_type(filename, content)

            if file_type == "application/pdf":
                return DocumentParser._parse_pdf(content)
            elif "wordprocessingml" in file_type or filename.lower().endswith(".docx"):
                return DocumentParser._parse_docx(content)
            elif file_type.startswith("text/"):
                return DocumentParser._parse_text(content)
            else:
                return DocumentParser._parse_text_fallback(content)

        except Exception as e:
            return "", f"Error parsing document: {str(e)}"

    @staticmethod
    def _parse_pdf(content: bytes) -> Tuple[str, Optional[str]]:
        """Parse PDF content."""
        if not PyPDF2:
            return "", "PDF parsing not available (PyPDF2 not installed)"

        try:
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text_parts = []
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())

            text = "\n".join(text_parts).strip()

            if not text:
                return "", "No text could be extracted from PDF"

            return text, None

        except Exception as e:
            return "", f"PDF parsing error: {str(e)}"

    @staticmethod
    def _parse_docx(content: bytes) -> Tuple[str, Optional[str]]:
        """Parse DOCX content."""
        if not Document:
            return "", "DOCX parsing not available (python-docx not installed)"

        try:
            docx_file = BytesIO(content)
            doc = Document(docx_file)

            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text.strip())

            text = "\n".join(text_parts).strip()

            if not text:
                return "", "No text could be extracted from DOCX"

            return text, None

        except Exception as e:
            return "", f"DOCX parsing error: {str(e)}"

    @staticmethod
    def _parse_text(content: bytes) -> Tuple[str, Optional[str]]:
        """Parse plain text content."""
        try:
            # Try different encodings
            for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
                try:
                    text = content.decode(encoding).strip()
                    if text:
                        return text, None
                except UnicodeDecodeError:
                    continue

            return "", "Could not decode text file with any common encoding"

        except Exception as e:
            return "", f"Text parsing error: {str(e)}"

    @staticmethod
    def _parse_text_fallback(content: bytes) -> Tuple[str, Optional[str]]:
        """Fallback text parsing for unknown file types."""
        try:
            # Try to extract any readable text
            text = content.decode("utf-8", errors="ignore").strip()

            if len(text) < 10:  # Too short to be meaningful
                return "", "File appears to be binary or contains no readable text"

            return text, None

        except Exception as e:
            return "", f"Fallback parsing error: {str(e)}"

    @staticmethod
    def extract_key_info(text: str, doc_type: str = "document") -> dict:
        """
        Extract key information from document text.

        Args:
            text: The extracted text
            doc_type: Type of document ("resume" or "job_description")

        Returns:
            Dictionary with structured information
        """
        info = {
            "type": doc_type,
            "length": len(text),
            "word_count": len(text.split()),
            "summary": text[:500] + "..." if len(text) > 500 else text,
        }

        if doc_type == "resume":
            # Basic resume parsing
            lines = text.lower().split("\n")

            # Look for common resume sections
            sections = {
                "experience": any(
                    "experience" in line or "work" in line for line in lines
                ),
                "education": any(
                    "education" in line or "degree" in line for line in lines
                ),
                "skills": any(
                    "skills" in line or "technical" in line for line in lines
                ),
                "contact": any(
                    "email" in line or "@" in line or "phone" in line for line in lines
                ),
            }
            info["sections"] = sections

            # Extract potential company names (simple heuristic)
            companies = []
            for line in lines:
                if any(
                    keyword in line
                    for keyword in [
                        "inc",
                        "corp",
                        "llc",
                        "ltd",
                        "company",
                        "technologies",
                    ]
                ):
                    companies.append(line.strip())
            info["potential_companies"] = companies[:5]  # Limit to first 5

        elif doc_type == "job_description":
            # Basic job description parsing
            lines = text.lower().split("\n")

            # Look for common job posting sections
            sections = {
                "requirements": any(
                    "requirements" in line or "qualifications" in line for line in lines
                ),
                "responsibilities": any(
                    "responsibilities" in line or "duties" in line for line in lines
                ),
                "benefits": any(
                    "benefits" in line or "perks" in line for line in lines
                ),
                "salary": any(
                    "salary" in line or "$" in text or "compensation" in line
                    for line in lines
                ),
            }
            info["sections"] = sections

            # Extract potential skills/technologies mentioned
            tech_keywords = [
                "python",
                "javascript",
                "sql",
                "aws",
                "docker",
                "kubernetes",
                "react",
                "angular",
                "machine learning",
                "ai",
            ]
            mentioned_tech = [tech for tech in tech_keywords if tech in text.lower()]
            info["technologies"] = mentioned_tech

        return info


def create_document_context(
    resume_text: Optional[str], job_desc_text: Optional[str]
) -> str:
    """
    Create a formatted context string for the interviewer agent.

    Args:
        resume_text: Extracted resume text
        job_desc_text: Extracted job description text

    Returns:
        Formatted context string for the agent
    """
    context_parts = []

    if resume_text:
        resume_info = DocumentParser.extract_key_info(resume_text, "resume")
        context_parts.append(
            f"""
CANDIDATE'S RESUME:
{resume_text}

Resume Analysis:
- Contains {resume_info['word_count']} words
- Sections identified: {', '.join([k for k, v in resume_info['sections'].items() if v])}
- Potential companies mentioned: {', '.join(resume_info['potential_companies'][:3]) if resume_info['potential_companies'] else 'None clearly identified'}
"""
        )

    if job_desc_text:
        job_info = DocumentParser.extract_key_info(job_desc_text, "job_description")
        context_parts.append(
            f"""
JOB DESCRIPTION:
{job_desc_text}

Job Analysis:
- Contains {job_info['word_count']} words
- Sections identified: {', '.join([k for k, v in job_info['sections'].items() if v])}
- Technologies mentioned: {', '.join(job_info['technologies']) if job_info['technologies'] else 'None specifically mentioned'}
"""
        )

    if context_parts:
        return f"""
DOCUMENT CONTEXT:
{'='*50}
{chr(10).join(context_parts)}
{'='*50}

INTERVIEW INSTRUCTIONS BASED ON DOCUMENTS:
- Reference specific experiences, companies, or projects from the resume naturally
- Ask follow-up questions about work history, achievements, and challenges
- Connect job requirements to candidate's background
- Probe deeper into relevant technical skills and experience
- Ask about career progression and decision-making
- Explore how past experience relates to the target role
"""

    return ""
