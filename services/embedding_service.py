from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

_model = None


def get_model():
    global _model

    if _model is None:
        print("Loading Embedding Model...")

        _model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        print("Embedding Model Loaded")

    return _model


def generate_embedding(
        text: str
):
    model = get_model()
    embedding = model.encode(text)

    return embedding


def calculate_semantic_score(
        candidate_text: str,
        job_text: str
):
    model = get_model()
    candidate_embedding = model.encode(candidate_text)
    job_embedding = model.encode(job_text)

    similarity = cosine_similarity(
        [candidate_embedding],
        [job_embedding]
    )

    return similarity[0][0]


def calculate_semantic_score_from_embeddings(
        candidate_embedding,
        job_embedding
):
    similarity = cosine_similarity(
        [candidate_embedding],
        [job_embedding]
    )

    return similarity[0][0]