from __future__ import annotations

import tempfile
import unittest

from app.ai import EmbeddingService
from app.ai.vector_store import QdrantLocalVectorStorage, VectorQuery


class QdrantRetrievalTests(unittest.TestCase):
    def test_qdrant_local_query_returns_filtered_neighbors(self) -> None:
        embedding_service = EmbeddingService()
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = QdrantLocalVectorStorage(embedding_service, tmpdir)
            posts = [
                {
                    "id": 1,
                    "raw_text": "I keep waiting at the station where goodbye still echoes.",
                    "summary": "A station goodbye.",
                    "embedding_json": embedding_service.serialize_vector(
                        embedding_service.generate_embedding(
                            "I keep waiting at the station where goodbye still echoes."
                        ).vector
                    ),
                    "embedding_model": embedding_service.generate_embedding("station goodbye").embedding_model,
                    "pipeline_version": "test-v1",
                    "semantic_profile_json": '{"distance": 1.0}',
                    "selected_content_notes_json": '["grief"]',
                    "content_type": "community",
                    "detected_emotions_json": '["longing"]',
                    "keywords_json": '["station"]',
                },
                {
                    "id": 2,
                    "raw_text": "The platform still feels full of distance and memory.",
                    "summary": "Distance and memory.",
                    "embedding_json": embedding_service.serialize_vector(
                        embedding_service.generate_embedding(
                            "The platform still feels full of distance and memory."
                        ).vector
                    ),
                    "embedding_model": embedding_service.generate_embedding("distance memory").embedding_model,
                    "pipeline_version": "test-v1",
                    "semantic_profile_json": '{"distance": 1.0, "memory": 1.0}',
                    "selected_content_notes_json": '[]',
                    "content_type": "public_archive",
                    "detected_emotions_json": '["nostalgia"]',
                    "keywords_json": '["platform"]',
                },
                {
                    "id": 3,
                    "raw_text": "Grief turned every room into a museum.",
                    "summary": "A room of grief.",
                    "embedding_json": embedding_service.serialize_vector(
                        embedding_service.generate_embedding(
                            "Grief turned every room into a museum."
                        ).vector
                    ),
                    "embedding_model": embedding_service.generate_embedding("grief museum").embedding_model,
                    "pipeline_version": "test-v1",
                    "semantic_profile_json": '{"loss": 1.0}',
                    "selected_content_notes_json": '["grief"]',
                    "content_type": "community",
                    "detected_emotions_json": '["grief"]',
                    "keywords_json": '["grief"]',
                },
            ]
            storage.upsert_posts(posts)

            ranked = storage.query(
                VectorQuery(
                    source_post=posts[0],
                    candidate_posts=posts,
                    limit=5,
                    exclude_post_id=1,
                    avoid_content_note="grief",
                )
            )

            self.assertTrue(ranked)
            self.assertEqual(ranked[0][0], 2)
            self.assertNotIn(3, [post_id for post_id, _ in ranked])


if __name__ == "__main__":
    unittest.main()
