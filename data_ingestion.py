"""
Data Ingestion Module
Reads and processes documents from the /identity directory
Supports: PDF, DOCX, and JSON (ChatGPT export format)
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from config import Config


class DataIngestion:
    """Handles loading and processing of documents from the identity directory"""

    def __init__(self, identity_dir: Path = None):
        self.identity_dir = identity_dir or Config.IDENTITY_DIR
        self.supported_extensions = Config.SUPPORTED_EXTENSIONS

    def load_pdf(self, file_path: Path) -> List[Document]:
        """Load PDF file using LangChain's PyPDFLoader"""
        try:
            loader = PyPDFLoader(str(file_path))
            documents = loader.load()

            # Add metadata
            for doc in documents:
                doc.metadata.update({
                    "source": str(file_path),
                    "file_type": "pdf",
                    "file_name": file_path.name,
                    "loaded_at": datetime.now().isoformat()
                })

            print(f"✓ Loaded PDF: {file_path.name} ({len(documents)} pages)")
            return documents

        except Exception as e:
            print(f"✗ Error loading PDF {file_path.name}: {e}")
            return []

    def load_docx(self, file_path: Path) -> List[Document]:
        """Load DOCX file using LangChain's Docx2txtLoader"""
        try:
            loader = Docx2txtLoader(str(file_path))
            documents = loader.load()

            # Add metadata
            for doc in documents:
                doc.metadata.update({
                    "source": str(file_path),
                    "file_type": "docx",
                    "file_name": file_path.name,
                    "loaded_at": datetime.now().isoformat()
                })

            print(f"✓ Loaded DOCX: {file_path.name}")
            return documents

        except Exception as e:
            print(f"✗ Error loading DOCX {file_path.name}: {e}")
            return []

    def load_chatgpt_json(self, file_path: Path) -> List[Document]:
        """
        Load ChatGPT export JSON file

        Expected format:
        [
            {
                "id": "...",
                "create_time": timestamp,
                "title": "Conversation title",
                "mapping": {
                    "node_id": {
                        "message": {
                            "content": {
                                "parts": ["text content"]
                            },
                            "author": {"role": "user|assistant"},
                            "create_time": timestamp
                        }
                    }
                }
            }
        ]
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            documents = []

            # Handle both single conversation and list of conversations
            conversations = data if isinstance(data, list) else [data]

            for conv in conversations:
                conv_id = conv.get('id', 'unknown')
                conv_title = conv.get('title', 'Untitled Conversation')
                create_time = conv.get('create_time')

                # Extract messages from mapping
                mapping = conv.get('mapping', {})

                for node_id, node in mapping.items():
                    message = node.get('message')
                    if not message:
                        continue

                    content = message.get('content', {})
                    parts = content.get('parts', [])
                    author = message.get('author', {}).get('role', 'unknown')
                    msg_time = message.get('create_time')

                    # Combine all parts into a single text
                    text = '\n'.join([str(part) for part in parts if part])

                    if text.strip():
                        doc = Document(
                            page_content=text,
                            metadata={
                                "source": str(file_path),
                                "file_type": "chatgpt_json",
                                "file_name": file_path.name,
                                "conversation_id": conv_id,
                                "conversation_title": conv_title,
                                "author": author,
                                "message_id": node_id,
                                "create_time": msg_time,
                                "loaded_at": datetime.now().isoformat()
                            }
                        )
                        documents.append(doc)

            print(f"✓ Loaded ChatGPT JSON: {file_path.name} ({len(documents)} messages)")
            return documents

        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON in {file_path.name}: {e}")
            return []
        except Exception as e:
            print(f"✗ Error loading JSON {file_path.name}: {e}")
            return []

    def load_generic_json(self, file_path: Path) -> List[Document]:
        """
        Load generic JSON file
        Attempts to extract text from various JSON structures
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            documents = []

            def extract_text(obj, path=""):
                """Recursively extract text from JSON object"""
                texts = []

                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        texts.extend(extract_text(value, new_path))

                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        new_path = f"{path}[{i}]"
                        texts.extend(extract_text(item, new_path))

                elif isinstance(obj, str) and obj.strip():
                    texts.append((path, obj))

                return texts

            text_items = extract_text(data)

            for path, text in text_items:
                if len(text) > 20:  # Only include substantial text
                    doc = Document(
                        page_content=text,
                        metadata={
                            "source": str(file_path),
                            "file_type": "json",
                            "file_name": file_path.name,
                            "json_path": path,
                            "loaded_at": datetime.now().isoformat()
                        }
                    )
                    documents.append(doc)

            print(f"✓ Loaded JSON: {file_path.name} ({len(documents)} text items)")
            return documents

        except Exception as e:
            print(f"✗ Error loading JSON {file_path.name}: {e}")
            return []

    def load_json(self, file_path: Path) -> List[Document]:
        """Load JSON file - tries ChatGPT format first, then generic"""
        # Try ChatGPT format first
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if it looks like ChatGPT export
            if isinstance(data, list) and len(data) > 0:
                if 'mapping' in data[0] or 'conversation_id' in data[0]:
                    return self.load_chatgpt_json(file_path)
            elif isinstance(data, dict) and 'mapping' in data:
                return self.load_chatgpt_json(file_path)
        except:
            pass

        # Fall back to generic JSON loader
        return self.load_generic_json(file_path)

    def scan_directory(self) -> List[Path]:
        """Scan identity directory for supported files"""
        if not self.identity_dir.exists():
            print(f"⚠ Identity directory not found: {self.identity_dir}")
            return []

        files = []
        for ext in self.supported_extensions:
            files.extend(self.identity_dir.glob(f"*{ext}"))
            files.extend(self.identity_dir.glob(f"**/*{ext}"))  # Recursive search

        # Remove duplicates and sort
        files = sorted(set(files))

        return files

    def load_txt(self, file_path: Path) -> List[Document]:
        """Load plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            doc = Document(
                page_content=text,
                metadata={
                    "source": str(file_path),
                    "file_type": "txt",
                    "file_name": file_path.name,
                    "loaded_at": datetime.now().isoformat()
                }
            )
            print(f"✓ Loaded TXT: {file_path.name} ({len(text)} chars)")
            return [doc]

        except Exception as e:
            print(f"✗ Error loading TXT {file_path.name}: {e}")
            return []

    def load_all_documents(self) -> List[Document]:
        """Load all documents from the identity directory"""
        print("\n" + "="*60)
        print("Data Ingestion: Loading Documents")
        print("="*60 + "\n")

        print(f"Scanning directory: {self.identity_dir}")

        files = self.scan_directory()

        if not files:
            print("\n⚠ No supported files found in identity directory")
            print(f"Supported formats: {', '.join(self.supported_extensions)}")
            return []

        print(f"\nFound {len(files)} files to process:\n")

        all_documents = []

        for file_path in files:
            ext = file_path.suffix.lower()

            if ext == '.pdf':
                docs = self.load_pdf(file_path)
            elif ext == '.docx':
                docs = self.load_docx(file_path)
            elif ext == '.json':
                docs = self.load_json(file_path)
            elif ext == '.txt':
                docs = self.load_txt(file_path)
            else:
                print(f"⊘ Skipping unsupported file: {file_path.name}")
                continue

            all_documents.extend(docs)

        print("\n" + "="*60)
        print(f"✓ Loaded {len(all_documents)} documents from {len(files)} files")
        print("="*60 + "\n")

        return all_documents

    def get_statistics(self, documents: List[Document]) -> Dict[str, Any]:
        """Get statistics about loaded documents"""
        stats = {
            "total_documents": len(documents),
            "by_file_type": {},
            "by_source": {},
            "total_characters": 0,
            "total_words": 0
        }

        for doc in documents:
            # Count by file type
            file_type = doc.metadata.get('file_type', 'unknown')
            stats['by_file_type'][file_type] = stats['by_file_type'].get(file_type, 0) + 1

            # Count by source file
            file_name = doc.metadata.get('file_name', 'unknown')
            stats['by_source'][file_name] = stats['by_source'].get(file_name, 0) + 1

            # Count characters and words
            content = doc.page_content
            stats['total_characters'] += len(content)
            stats['total_words'] += len(content.split())

        return stats

    def print_statistics(self, documents: List[Document]):
        """Print statistics about loaded documents"""
        stats = self.get_statistics(documents)

        print("\n" + "="*60)
        print("Document Statistics")
        print("="*60)

        print(f"\nTotal Documents: {stats['total_documents']}")
        print(f"Total Characters: {stats['total_characters']:,}")
        print(f"Total Words: {stats['total_words']:,}")

        print("\nBy File Type:")
        for file_type, count in stats['by_file_type'].items():
            print(f"  {file_type}: {count}")

        print("\nBy Source File:")
        for file_name, count in sorted(stats['by_source'].items()):
            print(f"  {file_name}: {count} documents")

        print("="*60 + "\n")


def main():
    """Test data ingestion"""
    Config.ensure_directories()

    ingestion = DataIngestion()
    documents = ingestion.load_all_documents()

    if documents:
        ingestion.print_statistics(documents)

        # Show sample document
        print("Sample Document:")
        print("-" * 60)
        sample = documents[0]
        print(f"Content: {sample.page_content[:200]}...")
        print(f"\nMetadata: {json.dumps(sample.metadata, indent=2)}")
        print("-" * 60)


if __name__ == "__main__":
    main()
