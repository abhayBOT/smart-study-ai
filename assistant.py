import os
import re
import pickle
import faiss
import numpy as np
import time
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from functools import lru_cache
import gc

# =========================================================
# FREE HOSTING OPTIMIZATIONS
# =========================================================
# Use smaller embedding model for free hosting (80MB vs 400MB)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Lazy loading for embedding model
@lru_cache(maxsize=1)
def get_embedding_model():
    return SentenceTransformer(EMBEDDING_MODEL_NAME)

# Lazy loading for LLM
@lru_cache(maxsize=1)
def get_llm_pipeline():
    model_name = "distilgpt2"  # Small model for free hosting
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    
    # Fix pad token issue
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    return pipeline("text-generation", model=model, tokenizer=model, max_length=512, pad_token_id=tokenizer.eos_token_id)

# =========================================================
# VECTOR DB PATHS (OPTIMIZED FOR FREE HOSTING)
# =========================================================
# Try compressed versions first, fallback to original
INDEX_PATHS = [
    "vector_db/index_compressed.faiss",
    "vector_db/index_mini.faiss", 
    "vector_db/index.faiss"
]
META_PATHS = [
    "vector_db/metadata_compressed.pkl",
    "vector_db/metadata_mini.pkl",
    "vector_db/metadata.pkl"
]

# Memory cache for loaded data
_cached_index = None
_cached_metadata = None
_cache_timestamp = 0

# =========================================================
# LOAD DATABASE (WITH CACHING AND FALLBACK)
# =========================================================
def load_db():
    global _cached_index, _cached_metadata, _cache_timestamp
    
    # Return cached data if available
    if _cached_index is not None and _cached_metadata is not None:
        print("✅ Using cached vector DB")
        return _cached_index, _cached_metadata
    
    # Try to load from optimized versions first
    for index_path, meta_path in zip(INDEX_PATHS, META_PATHS):
        try:
            if os.path.exists(index_path) and os.path.exists(meta_path):
                print(f"📂 Loading vector DB: {index_path}")
                index = faiss.read_index(index_path)
                
                # Load metadata with compression support
                with open(meta_path, "rb") as f:
                    metadata = pickle.load(f)
                
                print(f"✅ Vector DB Loaded: {index.ntotal} vectors, {len(metadata)} metadata entries")
                
                # Cache the loaded data
                _cached_index = index
                _cached_metadata = metadata
                _cache_timestamp = time.time()
                
                return index, metadata
        except Exception as e:
            print(f"❌ Failed to load {index_path}: {e}")
            continue
    
    print("❌ No vector database found")
    return None, []

# =========================================================
# SEARCH CHUNKS (OPTIMIZED FOR MEMORY)
# =========================================================
def search_chunks(query, index, metadata, k=3):
    try:
        if index is None:
            return []

        # Use smaller k for memory efficiency
        k = min(k, 3)
        
        # Get embedding model (lazy loaded)
        embedding_model = get_embedding_model()
        
        query_vec = embedding_model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).reshape(1, -1)

        query_vec = np.array(query_vec, dtype=np.float32)

        # Search with error handling
        try:
            D, I = index.search(query_vec, k)
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []

        results = []
        
        for i in I[0]:
            if i < len(metadata):
                item = metadata[i]
                if isinstance(item, dict) and "text" in item:
                    # Limit text size for memory efficiency
                    if len(item["text"]) > 500:
                        item = item.copy()
                        item["text"] = item["text"][:500] + "..."
                    results.append(item)

        # Clean up memory
        del query_vec
        gc.collect()
        
        return results

    except Exception as e:
        print("❌ Search Error:", e)
        return []

# =========================================================
# CLEAN OUTPUT
# =========================================================
def clean_output(text):
    remove_phrases = [
        "The given material contains",
        "instructions",
        "dataset",
        "strict rules",
        "OR",
        "Now, consider"
    ]

    for p in remove_phrases:
        text = text.replace(p, "")

    return text

# =========================================================
# BEAUTIFY OUTPUT
# =========================================================
def beautify_answer(text):
    replacements = {
        "Definition": "📘 Definition",
        "Formula": "📐 Formula",
        "Example": "🧠 Example",
        "Key Points": "📌 Key Points",
        "Explanation": "🔬 Explanation",
        "Conclusion": "✔ Conclusion"
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return text

# ✅ ADD THIS HERE ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓


def format_equations(text):
    if not isinstance(text, str):
        return text

    # Step 1: convert x^2 → x²
    text = re.sub(r'(\w)\^2', r'\1²', text)
    text = re.sub(r'(\w)\^3', r'\1³', text)

    # Step 2: convert x2 → x² (if model skips caret)
    text = re.sub(r'(\w)2', r'\1²', text)
    text = re.sub(r'(\w)3', r'\1³', text)

    return text

# =========================================================
# GENERATE ANSWER (FIXED INDENTATION)
# =========================================================
def generate_answer(query, results, selected_class, subject, chapter):

    if not results:
        return "❌ No relevant data found."

    try:
        top_results = results[:3]

        context = "\n".join(
            [r.get("text", "") for r in top_results]
        )[:1200]

        selected_class = selected_class or "Not Specified"
        subject = subject or "General"
        chapter = chapter or "General"

        # ---------------- STRONG PROMPT ----------------
        prompt = f"""
You are an AI study assistant for school students.

Use the study material given in the context to answer the question.

Your answer must follow this structure:

Definition:
Explain the concept clearly.

Explanation:
Explain the concept in simple language so students can understand easily.

Formula:
If the topic contains a formula, write the formula clearly.

Example:
Give one simple example related to the concept.

Only use information from the context.

Context:
{context}

Question:
{query}
"""

        # Use Hugging Face Transformers instead of Ollama
        llm_pipeline = get_llm_pipeline()
        
        response = llm_pipeline(
            prompt,
            max_new_tokens=300,
            temperature=0.2,
            do_sample=True
        )
        
        answer = response[0]["generated_text"]
        
        # Clean up the response
        if prompt in answer:
            answer = answer.replace(prompt, "").strip()

        answer = clean_output(answer)
        answer = beautify_answer(answer)
        answer = format_equations(answer)

        return answer

    except Exception as e:
        print("❌ AI Error:", e)
        
        # Clean up memory
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        fallback = "\n".join([r.get("text", "") for r in results[:2]])
        return fallback[:1200]