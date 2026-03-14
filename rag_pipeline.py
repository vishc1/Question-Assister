"""
RAG (Retrieval-Augmented Generation) Pipeline
Handles chunking, embedding, vector storage, and retrieval
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from config import Config
from data_ingestion import DataIngestion


class RAGPipeline:
    """
    RAG Pipeline for personal context retrieval
    - Chunks documents into 500 character segments with 50 char overlap
    - Creates FAISS vector index with OpenAI embeddings
    - Provides retrieval function for personal context
    """

    def __init__(
        self,
        identity_dir: Path = None,
        vector_store_path: Path = None,
        openai_api_key: str = None
    ):
        self.identity_dir = identity_dir or Config.IDENTITY_DIR
        self.vector_store_path = vector_store_path or Config.VECTOR_STORE_PATH

        # Set OpenAI API key
        self.openai_api_key = openai_api_key or Config.OPENAI_API_KEY
        if self.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.openai_api_key

        # Initialize components
        self.embeddings = None
        self.vector_store = None
        self.text_splitter = None
        self.documents = []
        self.chunks = []

        # Configuration
        self.chunk_size = Config.CHUNK_SIZE
        self.chunk_overlap = Config.CHUNK_OVERLAP
        self.top_k = Config.TOP_K_RESULTS
        self.embedding_model = Config.EMBEDDING_MODEL

        # Index metadata
        self.index_metadata = {
            "created_at": None,
            "total_documents": 0,
            "total_chunks": 0,
            "source_files": []
        }

    def initialize_components(self):
        """Initialize embeddings and text splitter"""
        print("\n" + "="*60)
        print("Initializing RAG Pipeline Components")
        print("="*60 + "\n")

        # Initialize OpenAI embeddings
        try:
            self.embeddings = OpenAIEmbeddings(
                model=self.embedding_model,
                openai_api_key=self.openai_api_key
            )
            print(f"✓ OpenAI Embeddings initialized (model: {self.embedding_model})")
        except Exception as e:
            print(f"✗ Error initializing embeddings: {e}")
            raise

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        print(f"✓ Text splitter initialized (size: {self.chunk_size}, overlap: {self.chunk_overlap})")

        print()

    def load_documents(self) -> List[Document]:
        """Load documents from identity directory"""
        ingestion = DataIngestion(self.identity_dir)
        self.documents = ingestion.load_all_documents()
        return self.documents

    def chunk_documents(self, documents: List[Document] = None) -> List[Document]:
        """
        Chunk documents into smaller segments
        Uses 500 character chunks with 50 character overlap
        """
        if documents is None:
            documents = self.documents

        if not documents:
            print("⚠ No documents to chunk")
            return []

        print("\n" + "="*60)
        print("Chunking Documents")
        print("="*60 + "\n")

        self.chunks = self.text_splitter.split_documents(documents)

        print(f"✓ Split {len(documents)} documents into {len(self.chunks)} chunks")
        print(f"  Chunk size: {self.chunk_size} characters")
        print(f"  Overlap: {self.chunk_overlap} characters")

        # Calculate statistics
        chunk_lengths = [len(chunk.page_content) for chunk in self.chunks]
        avg_length = sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0

        print(f"\nChunk Statistics:")
        print(f"  Average length: {avg_length:.0f} characters")
        print(f"  Min length: {min(chunk_lengths) if chunk_lengths else 0}")
        print(f"  Max length: {max(chunk_lengths) if chunk_lengths else 0}")
        print()

        return self.chunks

    def create_vector_store(self, chunks: List[Document] = None) -> FAISS:
        """Create FAISS vector store from document chunks"""
        if chunks is None:
            chunks = self.chunks

        if not chunks:
            print("⚠ No chunks to vectorize")
            return None

        print("\n" + "="*60)
        print("Creating Vector Store")
        print("="*60 + "\n")

        try:
            print(f"Creating embeddings for {len(chunks)} chunks...")
            print("(This may take a while for large datasets)")

            self.vector_store = FAISS.from_documents(
                documents=chunks,
                embedding=self.embeddings
            )

            print(f"✓ Vector store created with {len(chunks)} vectors")

            # Update metadata
            from datetime import datetime
            self.index_metadata = {
                "created_at": datetime.now().isoformat(),
                "total_documents": len(self.documents),
                "total_chunks": len(chunks),
                "source_files": list(set([
                    doc.metadata.get('file_name', 'unknown')
                    for doc in self.documents
                ])),
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "embedding_model": self.embedding_model
            }

            return self.vector_store

        except Exception as e:
            print(f"✗ Error creating vector store: {e}")
            raise

    def save_vector_store(self, path: Path = None):
        """Save FAISS vector store to disk"""
        if not self.vector_store:
            print("⚠ No vector store to save")
            return

        save_path = path or self.vector_store_path
        save_path.mkdir(parents=True, exist_ok=True)

        print("\n" + "="*60)
        print("Saving Vector Store")
        print("="*60 + "\n")

        try:
            # Save FAISS index
            index_path = save_path / "faiss_index"
            self.vector_store.save_local(str(index_path))
            print(f"✓ FAISS index saved to: {index_path}")

            # Save metadata
            metadata_path = save_path / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(self.index_metadata, f, indent=2)
            print(f"✓ Metadata saved to: {metadata_path}")

            print()

        except Exception as e:
            print(f"✗ Error saving vector store: {e}")
            raise

    def load_vector_store(self, path: Path = None) -> bool:
        """Load FAISS vector store from disk"""
        load_path = path or self.vector_store_path
        index_path = load_path / "faiss_index"
        metadata_path = load_path / "metadata.json"

        if not index_path.exists():
            print(f"⚠ No vector store found at: {index_path}")
            return False

        print("\n" + "="*60)
        print("Loading Vector Store")
        print("="*60 + "\n")

        try:
            # Initialize embeddings if not already done
            if not self.embeddings:
                self.embeddings = OpenAIEmbeddings(
                    model=self.embedding_model,
                    openai_api_key=self.openai_api_key
                )

            # Load FAISS index
            self.vector_store = FAISS.load_local(
                str(index_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"✓ FAISS index loaded from: {index_path}")

            # Load metadata
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.index_metadata = json.load(f)
                print(f"✓ Metadata loaded")

                print(f"\nIndex Information:")
                print(f"  Created: {self.index_metadata.get('created_at', 'unknown')}")
                print(f"  Documents: {self.index_metadata.get('total_documents', 0)}")
                print(f"  Chunks: {self.index_metadata.get('total_chunks', 0)}")
                print(f"  Source files: {len(self.index_metadata.get('source_files', []))}")

            print()
            return True

        except Exception as e:
            print(f"✗ Error loading vector store: {e}")
            return False

    def get_personal_context(
        self,
        query: str,
        top_k: int = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve personal context based on query

        Args:
            query: The question or text to search for
            top_k: Number of results to return (default from config)
            include_metadata: Whether to include document metadata

        Returns:
            List of dictionaries with content and metadata
        """
        if not self.vector_store:
            print("⚠ Vector store not loaded. Call load_vector_store() first.")
            return []

        k = top_k or self.top_k

        try:
            # Perform similarity search
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k
            )

            # Format results
            formatted_results = []
            for i, (doc, score) in enumerate(results):
                result = {
                    "rank": i + 1,
                    "content": doc.page_content,
                    "similarity_score": float(score),
                }

                if include_metadata:
                    result["metadata"] = doc.metadata

                formatted_results.append(result)

            return formatted_results

        except Exception as e:
            print(f"✗ Error retrieving context: {e}")
            return []

    def build_index(self, force_rebuild: bool = False):
        """
        Build the complete RAG index
        Loads documents, chunks them, creates vector store, and saves

        Args:
            force_rebuild: If True, rebuild even if index exists
        """
        print("\n" + "="*70)
        print(" "*25 + "RAG INDEX BUILD")
        print("="*70)

        # Check if index already exists
        if not force_rebuild and (self.vector_store_path / "faiss_index").exists():
            print("\n✓ Vector store already exists")
            print(f"  Location: {self.vector_store_path / 'faiss_index'}")
            print("\nTo rebuild, run with force_rebuild=True")
            return False

        try:
            # Validate configuration
            issues = Config.validate()
            if issues:
                print("\n✗ Configuration issues:")
                for issue in issues:
                    print(f"  - {issue}")
                return False

            Config.ensure_directories()

            # Initialize components
            self.initialize_components()

            # Load documents
            self.load_documents()

            if not self.documents:
                print("\n⚠ No documents found to index")
                print(f"  Add PDF, DOCX, or JSON files to: {self.identity_dir}")
                return False

            # Chunk documents
            self.chunk_documents()

            if not self.chunks:
                print("\n⚠ No chunks created from documents")
                return False

            # Create vector store
            self.create_vector_store()

            # Save vector store
            self.save_vector_store()

            print("\n" + "="*70)
            print("✓ RAG INDEX BUILD COMPLETE")
            print("="*70 + "\n")

            return True

        except Exception as e:
            print(f"\n✗ Index build failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def search_interactive(self):
        """Interactive search mode for testing"""
        if not self.vector_store:
            print("⚠ No vector store loaded")
            return

        print("\n" + "="*60)
        print("Interactive Search Mode")
        print("="*60)
        print("\nType your query (or 'quit' to exit)\n")

        while True:
            try:
                query = input("Query: ").strip()

                if query.lower() in ['quit', 'exit', 'q']:
                    break

                if not query:
                    continue

                print("\n" + "-"*60)
                results = self.get_personal_context(query)

                if not results:
                    print("No results found")
                else:
                    for result in results:
                        print(f"\n[Rank {result['rank']}] (Score: {result['similarity_score']:.4f})")
                        print(f"Content: {result['content'][:200]}...")

                        if 'metadata' in result:
                            meta = result['metadata']
                            print(f"Source: {meta.get('file_name', 'unknown')}")
                            if 'conversation_title' in meta:
                                print(f"Conversation: {meta['conversation_title']}")

                print("-"*60 + "\n")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

        print("\n✓ Search session ended")


def main():
    """Main function for testing and building index"""
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "build":
            # Build index
            rag = RAGPipeline()
            force = "--force" in sys.argv
            rag.build_index(force_rebuild=force)

        elif command == "search":
            # Interactive search
            rag = RAGPipeline()
            if rag.load_vector_store():
                rag.search_interactive()
            else:
                print("⚠ No index found. Run 'python rag_pipeline.py build' first")

        elif command == "info":
            # Show index information
            rag = RAGPipeline()
            if rag.load_vector_store():
                print("\n" + "="*60)
                print("Index Information")
                print("="*60)
                print(json.dumps(rag.index_metadata, indent=2))
                print()
            else:
                print("⚠ No index found")

        else:
            print(f"Unknown command: {command}")
            print("\nUsage:")
            print("  python rag_pipeline.py build [--force]  - Build/rebuild index")
            print("  python rag_pipeline.py search           - Interactive search")
            print("  python rag_pipeline.py info             - Show index info")

    else:
        print("\nRAG Pipeline")
        print("\nUsage:")
        print("  python rag_pipeline.py build [--force]  - Build/rebuild index")
        print("  python rag_pipeline.py search           - Interactive search")
        print("  python rag_pipeline.py info             - Show index info")


if __name__ == "__main__":
    main()
