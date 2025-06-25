# 📚 Chat with Documents

A powerful AI-powered document chatbot that allows you to query and interact with your PDF documents using advanced language models and vector search.

## ✨ Features

- 🔍 **Intelligent Document Search**: Uses ChromaDB for efficient vector-based document retrieval
- 🤖 **Multiple AI Models**: Supports Groq's language models for high-quality responses
- 📄 **PDF Processing**: Automatically processes and indexes PDF documents
- ⚡ **Real-time Responses**: Typewriter animation effect for engaging user experience
- 🎯 **Context-Aware**: Provides relevant answers based on document content with source citations
- 🔧 **Easy Configuration**: Simple setup with environment variables

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google AI API Key
- Groq API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd "chat with docs"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. **Add your PDF documents**
   Place your PDF files in the `data/books/` directory

5. **Generate the document database**
   ```bash
   python database.py
   ```

6. **Start chatting with your documents**
   ```bash
   python retrieve.py "What is the main topic of the documents?"
   ```

## 📁 Project Structure

```
chat with docs/
├── 📄 chatbot.py          # Main chatbot interface
├── 🗄️ database.py         # Document processing and database creation
├── 🔍 retrieve.py         # Query processing and response generation
├── 📋 requirements.txt    # Python dependencies
├── ⚙️ pyproject.toml      # Project configuration
├── 🔒 .env               # Environment variables (create this)
├── 📖 README.md          # This file
├── 📁 data/
│   └── 📁 books/         # Place your PDF documents here
└── 📁 chroma/            # Vector database (auto-generated)
```

## 🛠️ Usage

### Processing Documents

First, process your PDF documents to create the searchable database:

```bash
python database.py
```

This will:
- Load all PDF files from `data/books/`
- Split documents into chunks
- Generate embeddings using Google's embedding model
- Store everything in ChromaDB

### Querying Documents

Ask questions about your documents:

```bash
python retrieve.py "Explain the key concepts in machine learning"
```

The system will:
- Search for relevant document chunks
- Generate a comprehensive answer using Groq's AI model
- Display the response with typewriter animation
- Show source citations

## ⚙️ Configuration

### Text Splitting Parameters

In `database.py`, you can adjust:

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,      # Size of each text chunk
    chunk_overlap=100,   # Overlap between chunks
    length_function=len,
    add_start_index=True,
)
```

### Search Parameters

In `retrieve.py`, you can modify:

```python
results = db.similarity_search_with_relevance_scores(query_text, k=7)  # Number of results
```

### Typewriter Animation Speed

Adjust the typing speed:

```python
time.sleep(0.03)  # Seconds between characters (lower = faster)
```

## 🤖 Supported Models

- **Embeddings**: Google's `models/embedding-001`
- **Language Model**: Groq's `meta-llama/llama-4-maverick-17b-128e-instruct`

## 🔧 Troubleshooting

### Common Issues

1. **API Key Errors**
   - Ensure your `.env` file contains valid API keys
   - Check that the `.env` file is in the root directory

2. **No Results Found**
   - Verify PDF files are in `data/books/` directory
   - Run `python database.py` to rebuild the database
   - Check if your query is related to the document content

3. **PDF Loading Errors**
   - Ensure PDF files are not corrupted
   - Check file permissions
   - Some PDFs might be password-protected

## 📊 Performance Tips

- **Chunk Size**: Larger chunks (500-1000) for detailed contexts, smaller chunks (200-400) for precise answers
- **Overlap**: 10-20% of chunk size for good continuity
- **Search Results**: More results (k=5-10) for comprehensive answers, fewer (k=3-5) for focused responses

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for the document processing framework
- [ChromaDB](https://www.trychroma.com/) for vector database capabilities
- [Groq](https://groq.com/) for fast AI inference
- [Google AI](https://ai.google/) for embedding models

## 📞 Support

If you encounter any issues or have questions, please:
1. Check the troubleshooting section above
2. Search existing issues in the repository
3. Create a new issue with detailed information

---

⭐ **Star this repository if you find it helpful!**