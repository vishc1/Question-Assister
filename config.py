"""
Configuration Management
Loads settings from environment variables and provides defaults
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


class Config:
    """Application configuration"""

    # Base paths
    BASE_DIR = Path(__file__).parent
    IDENTITY_DIR = Path(os.getenv("IDENTITY_DIR", "./identity"))
    VECTOR_STORE_PATH = Path(os.getenv("VECTOR_STORE_PATH", "./vector_store"))

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Deepgram Configuration
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

    # RAG Configuration
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))
    TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", 5))
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # Real-time Processing Configuration
    SILENCE_THRESHOLD = float(os.getenv("SILENCE_THRESHOLD", 1.5))
    MIN_QUERY_LENGTH = int(os.getenv("MIN_QUERY_LENGTH", 10))
    GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")
    MAX_BULLET_POINTS = int(os.getenv("MAX_BULLET_POINTS", 3))

    # Supported file types
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".json", ".txt"}

    @classmethod
    def validate(cls):
        """Validate configuration"""
        issues = []

        if not cls.OPENAI_API_KEY:
            issues.append("OPENAI_API_KEY not set. Please set it in .env file")

        if cls.CHUNK_SIZE <= 0:
            issues.append("CHUNK_SIZE must be positive")

        if cls.CHUNK_OVERLAP >= cls.CHUNK_SIZE:
            issues.append("CHUNK_OVERLAP must be less than CHUNK_SIZE")

        if cls.TOP_K_RESULTS <= 0:
            issues.append("TOP_K_RESULTS must be positive")

        return issues

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        cls.IDENTITY_DIR.mkdir(parents=True, exist_ok=True)
        cls.VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        print("\n" + "="*60)
        print("Configuration")
        print("="*60)
        print(f"Identity Directory: {cls.IDENTITY_DIR}")
        print(f"Vector Store Path: {cls.VECTOR_STORE_PATH}")
        print(f"Chunk Size: {cls.CHUNK_SIZE}")
        print(f"Chunk Overlap: {cls.CHUNK_OVERLAP}")
        print(f"Top K Results: {cls.TOP_K_RESULTS}")
        print(f"Embedding Model: {cls.EMBEDDING_MODEL}")
        print(f"Silence Threshold: {cls.SILENCE_THRESHOLD}s")
        print(f"GPT Model: {cls.GPT_MODEL}")
        print(f"Max Bullet Points: {cls.MAX_BULLET_POINTS}")
        print(f"OpenAI API Key: {'✓ Set' if cls.OPENAI_API_KEY else '✗ Not Set'}")
        print(f"Deepgram API Key: {'✓ Set' if cls.DEEPGRAM_API_KEY else '✗ Not Set'}")
        print("="*60 + "\n")
