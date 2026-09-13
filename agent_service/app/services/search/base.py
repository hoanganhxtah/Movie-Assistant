from typing import Mapping, Protocol, Sequence

import numpy as np

from agent_service.app.schemas import SearchFilter, SearchHit


class MovieRetriever(Protocol):
    def search(
        self, query: str, filters: SearchFilter | None = None, top_k: int = 20
    ) -> list[SearchHit]: ...

    def query_scores(self, query: str) -> np.ndarray: ...

    def profile_scores(self, movie_weights: Mapping[int, float]) -> np.ndarray: ...

    def similarities(
        self, movie_id: int, other_movie_ids: Sequence[int]
    ) -> dict[int, float]: ...

