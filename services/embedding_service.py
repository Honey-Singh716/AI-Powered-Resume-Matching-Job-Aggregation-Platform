import torch
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Limit PyTorch CPU threads globally to prevent excessive memory and CPU usage
torch.set_num_threads(1)
torch.set_grad_enabled(False)

_model = None


def get_model():
    global _model

    if _model is None:
        print("Loading Embedding Model...")
        # Load model on CPU specifically to save GPU memory overhead
        _model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            device="cpu"
        )
        print("Embedding Model Loaded")

    return _model


def generate_embedding(text: str):
    model = get_model()
    # Use torch.inference_mode() / no_grad() context to prevent memory retention
    with torch.no_grad():
        embedding = model.encode(text, show_progress_bar=False, convert_to_numpy=True)
    return embedding


def calculate_semantic_score_from_embeddings(candidate_embedding, job_embedding):
    similarity = cosine_similarity(
        [candidate_embedding],
        [job_embedding]
    )

    return similarity[0][0]