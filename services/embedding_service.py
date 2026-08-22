from threading import Lock
import logging

_model = None
_model_lock = Lock()


def get_model():
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                import torch
                from sentence_transformers import SentenceTransformer

                # Limit PyTorch CPU threads to prevent excessive memory and CPU usage.
                torch.set_num_threads(1)
                logging.info("Loading embedding model on first embedding request...")
                # Keep the existing model and vector dimensions for DB compatibility.
                _model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
                logging.info("Embedding model loaded.")

    return _model


def generate_embedding(text: str):
    import torch

    model = get_model()
    with torch.inference_mode():
        embedding = model.encode(text, show_progress_bar=False, convert_to_numpy=True)
    return embedding


def calculate_semantic_score_from_embeddings(candidate_embedding, job_embedding):
    from sklearn.metrics.pairwise import cosine_similarity

    similarity = cosine_similarity(
        [candidate_embedding],
        [job_embedding]
    )

    return similarity[0][0]