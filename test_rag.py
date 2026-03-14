#!/usr/bin/env python3
"""
RAG Pipeline Test Script
Tests all components of the RAG pipeline
"""

import sys
from pathlib import Path
import json


def test_imports():
    """Test that all required packages are installed"""
    print("\n" + "="*60)
    print("Testing RAG Dependencies")
    print("="*60 + "\n")

    packages = {
        'langchain': 'LangChain',
        'langchain_openai': 'LangChain OpenAI',
        'langchain_community': 'LangChain Community',
        'openai': 'OpenAI',
        'faiss': 'FAISS',
        'pypdf': 'PyPDF',
        'docx': 'python-docx',
        'tiktoken': 'TikTok',
        'dotenv': 'python-dotenv'
    }

    all_success = True

    for module, name in packages.items():
        try:
            __import__(module)
            print(f"✓ {name}: OK")
        except ImportError as e:
            print(f"✗ {name}: FAILED - {e}")
            all_success = False

    return all_success


def test_config():
    """Test configuration"""
    print("\n" + "="*60)
    print("Testing Configuration")
    print("="*60 + "\n")

    try:
        from config import Config

        Config.print_config()

        issues = Config.validate()
        if issues:
            print("Configuration Issues:")
            for issue in issues:
                print(f"  ✗ {issue}")
            return False
        else:
            print("✓ Configuration valid")
            return True

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_data_ingestion():
    """Test data ingestion module"""
    print("\n" + "="*60)
    print("Testing Data Ingestion")
    print("="*60 + "\n")

    try:
        from data_ingestion import DataIngestion
        from config import Config

        Config.ensure_directories()

        ingestion = DataIngestion()
        print(f"✓ DataIngestion initialized")
        print(f"  Identity directory: {ingestion.identity_dir}")

        # Scan for files
        files = ingestion.scan_directory()
        print(f"\n✓ Found {len(files)} files:")

        if files:
            for file in files:
                print(f"  - {file.name}")
        else:
            print("  (no files found)")
            print(f"\n  Add files to: {ingestion.identity_dir}")

        return True

    except Exception as e:
        print(f"✗ Data ingestion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_pipeline():
    """Test RAG pipeline"""
    print("\n" + "="*60)
    print("Testing RAG Pipeline")
    print("="*60 + "\n")

    try:
        from rag_pipeline import RAGPipeline

        rag = RAGPipeline()
        print("✓ RAGPipeline initialized")

        # Try to load existing index
        if rag.load_vector_store():
            print("✓ Vector store loaded successfully")

            # Test query
            print("\n" + "="*60)
            print("Testing Query")
            print("="*60 + "\n")

            test_query = "Python"
            print(f"Query: '{test_query}'")

            results = rag.get_personal_context(test_query, top_k=3)

            if results:
                print(f"\n✓ Found {len(results)} results:")
                for result in results:
                    print(f"\n[Rank {result['rank']}] Score: {result['similarity_score']:.4f}")
                    print(f"Content: {result['content'][:150]}...")
                    if 'metadata' in result:
                        print(f"Source: {result['metadata'].get('file_name', 'unknown')}")
            else:
                print("✗ No results found")

            return True
        else:
            print("⚠ No vector store found")
            print("\nTo test the full pipeline:")
            print("  1. Add documents to 'identity/' directory")
            print("  2. Run: python rag_pipeline.py build")
            print("  3. Run this test again")
            return False

    except Exception as e:
        print(f"✗ RAG pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_sample_documents():
    """Create sample documents for testing"""
    print("\n" + "="*60)
    print("Creating Sample Documents")
    print("="*60 + "\n")

    from config import Config

    Config.ensure_directories()

    # Sample resume content
    sample_resume = """
John Doe
Software Engineer

EXPERIENCE:
- Senior Python Developer at TechCorp (2020-2024)
  * Led development of microservices architecture using Python, FastAPI, and Docker
  * Implemented machine learning models for recommendation system
  * Mentored junior developers and conducted code reviews

- Full Stack Developer at StartupXYZ (2018-2020)
  * Built web applications using Python, React, and PostgreSQL
  * Developed RESTful APIs and integrated third-party services
  * Improved system performance by 40% through optimization

SKILLS:
Python, JavaScript, React, Docker, Kubernetes, AWS, Machine Learning, SQL, Git

EDUCATION:
Bachelor of Science in Computer Science
University of Technology (2014-2018)

PROJECTS:
- Personal Finance Tracker: Built a full-stack application for budget management
- Weather Prediction Model: Developed ML model using TensorFlow and scikit-learn
- Open Source Contributions: Active contributor to several Python libraries
"""

    # Sample project description
    sample_projects = """
PROJECT DESCRIPTIONS

1. E-Commerce Platform (TechCorp)
   Built a scalable e-commerce platform handling 100K+ daily transactions.
   Technologies: Python, Django, Redis, PostgreSQL, AWS
   Challenges: Optimized database queries, implemented caching strategy
   Results: Reduced page load time by 60%, increased conversion rate by 25%

2. Recommendation Engine (TechCorp)
   Developed a machine learning-based product recommendation system.
   Technologies: Python, TensorFlow, scikit-learn, Apache Spark
   Challenges: Handling large datasets, model training optimization
   Results: Improved recommendation accuracy by 35%, increased user engagement

3. Real-time Analytics Dashboard (StartupXYZ)
   Created a real-time analytics dashboard for business metrics.
   Technologies: Python, React, WebSockets, InfluxDB
   Challenges: Real-time data processing, efficient visualization
   Results: Enabled data-driven decisions, reduced reporting time by 80%
"""

    # Save to files
    try:
        resume_path = Config.IDENTITY_DIR / "sample_resume.txt"
        with open(resume_path, 'w') as f:
            f.write(sample_resume)
        print(f"✓ Created: {resume_path}")

        projects_path = Config.IDENTITY_DIR / "sample_projects.txt"
        with open(projects_path, 'w') as f:
            f.write(sample_projects)
        print(f"✓ Created: {projects_path}")

        # Create sample JSON
        sample_json = {
            "profile": {
                "name": "John Doe",
                "title": "Software Engineer",
                "specialties": ["Python", "Machine Learning", "Web Development"]
            },
            "achievements": [
                "Led team of 5 developers",
                "Deployed 20+ production applications",
                "Published 3 technical articles"
            ],
            "leadership": [
                "Mentored 10+ junior developers",
                "Organized tech talks and workshops",
                "Led architecture design sessions"
            ]
        }

        json_path = Config.IDENTITY_DIR / "sample_profile.json"
        with open(json_path, 'w') as f:
            json.dump(sample_json, f, indent=2)
        print(f"✓ Created: {json_path}")

        print("\n✓ Sample documents created successfully")
        print(f"  Location: {Config.IDENTITY_DIR}")
        print("\nNext steps:")
        print("  1. Run: python rag_pipeline.py build")
        print("  2. Run: python test_rag.py")

        return True

    except Exception as e:
        print(f"✗ Error creating sample documents: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print(" "*25 + "RAG PIPELINE TESTS")
    print("="*70)

    results = {
        'imports': test_imports(),
        'config': test_config(),
        'data_ingestion': test_data_ingestion(),
        'rag_pipeline': test_rag_pipeline()
    }

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60 + "\n")

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    all_passed = all(results.values())

    print("\n" + "="*60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("⚠ Some tests failed")
        print("\nCommon fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Set up .env file with OPENAI_API_KEY")
        print("  3. Add documents to identity/ directory")
        print("  4. Build index: python rag_pipeline.py build")

    print("="*60 + "\n")

    return all_passed


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "create-samples":
        create_sample_documents()
        return

    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✓ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
