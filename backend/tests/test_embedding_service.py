import math

from app.services.rag.embedding_service import (
    LocalHashingEmbeddingProvider,
    get_embedding_provider,
    reset_embedding_provider,
)


def test_local_provider_is_deterministic():
    provider = LocalHashingEmbeddingProvider(dimensions=64)
    v1 = provider.embed_one("I love hiking in the mountains")
    v2 = provider.embed_one("I love hiking in the mountains")
    assert v1 == v2


def test_local_provider_output_shape_and_normalization():
    provider = LocalHashingEmbeddingProvider(dimensions=64)
    vector = provider.embed_one("some text to embed")
    assert len(vector) == 64
    norm = math.sqrt(sum(v * v for v in vector))
    assert abs(norm - 1.0) < 1e-6


def test_local_provider_empty_text_returns_zero_vector():
    provider = LocalHashingEmbeddingProvider(dimensions=32)
    vector = provider.embed_one("")
    assert vector == [0.0] * 32


def test_local_provider_similar_text_scores_higher_than_unrelated():
    provider = LocalHashingEmbeddingProvider(dimensions=128)

    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    base = provider.embed_one("my favorite food is pizza with extra cheese")
    similar = provider.embed_one("pizza with extra cheese is my favorite food")
    unrelated = provider.embed_one("the quarterly financial report was delayed")

    assert cosine(base, similar) > cosine(base, unrelated)


def test_embed_many_matches_embed_one():
    provider = LocalHashingEmbeddingProvider(dimensions=32)
    texts = ["hello there", "goodbye now"]
    batch = provider.embed_many(texts)
    singles = [provider.embed_one(t) for t in texts]
    assert batch == singles


def test_get_embedding_provider_defaults_to_local_without_api_key(monkeypatch):
    reset_embedding_provider()
    monkeypatch.setattr("app.config.EMBEDDING_PROVIDER", "auto")
    monkeypatch.setattr("app.config.EMBEDDING_API_KEY", "")
    provider = get_embedding_provider()
    try:
        assert provider.name == "local_hashing"
    finally:
        reset_embedding_provider()
