"""Fast local search using TF-IDF n-grams plus metadata keyword boost."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.preprocessing import normalize

from agent_service.app.config import search_settings
from agent_service.app.repository import MovieRepository
from agent_service.app.schemas import SearchFilter, SearchHit


TOKEN_RE = re.compile(r"[a-z0-9]+")
IGNORED_TERMS = set(ENGLISH_STOP_WORDS).union(
    {"movie", "film", "want", "phim", "tôi", "muốn", "một"}
)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text).lower())


class TfidfMovieRetriever:
    def __init__(self, repository: MovieRepository):
        self.repository = repository
        self.movie_ids = repository.movie_ids
        self._row_by_id = {
            int(movie_id): row for row, movie_id in enumerate(self.movie_ids)
        }
        self.documents: list[str] = []
        self.metadata_terms: list[set[str]] = []
        # Repeat compact metadata so it has more weight than a long plot.
        for row in repository.movies.itertuples(index=False):
            genres = " ".join(row.genres_list)
            tags = " ".join(row.tags_list)
            self.documents.append(
                f"{row.title} {genres} {genres} {tags} {tags} {row.plot}"
            )
            self.metadata_terms.append(
                set(tokenize(f"{row.title} {genres} {tags}"))
            )
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=search_settings.MAX_FEATURES,
            sublinear_tf=True,
        )
        self.matrix = self.vectorizer.fit_transform(self.documents)

    def query_scores(self, query: str) -> np.ndarray:
        query = str(query).strip()
        if not query:
            return np.zeros(len(self.movie_ids), dtype=float)
        # Cosine-like TF-IDF score is supplemented by exact metadata terms.
        query_vector = self.vectorizer.transform([query])
        scores = np.asarray((self.matrix @ query_vector.T).toarray()).ravel()
        terms = set(tokenize(query)).difference(IGNORED_TERMS)
        if terms:
            boost = np.asarray(
                [len(terms.intersection(values)) / len(terms) for values in self.metadata_terms]
            )
            scores += 0.15 * boost
        return scores

    @staticmethod
    def _accepts(row, filters: SearchFilter) -> bool:
        genres = {genre.lower() for genre in row.genres_list}
        if any(genre.lower() in genres for genre in filters.exclude_genres):
            return False
        if filters.min_year is not None and (
            np.isnan(row.year) or int(row.year) < filters.min_year
        ):
            return False
        if filters.max_year is not None and (
            np.isnan(row.year) or int(row.year) > filters.max_year
        ):
            return False
        return True

    def search(
        self,
        query: str,
        filters: SearchFilter | None = None,
        top_k: int = 20,
    ) -> list[SearchHit]:
        filters = filters or SearchFilter()
        scores = self.query_scores(query)
        order = np.argsort(scores)[::-1]
        query_terms = set(tokenize(query)).difference(IGNORED_TERMS)
        hits: list[SearchHit] = []
        for row_index in order:
            if scores[row_index] <= 0:
                break
            row = self.repository.movies.iloc[int(row_index)]
            if not self._accepts(row, filters):
                continue
            year = None if np.isnan(row["year"]) else int(row["year"])
            matched = tuple(
                sorted(query_terms.intersection(set(tokenize(self.documents[row_index]))))[:8]
            )
            hits.append(
                SearchHit(
                    movie_id=int(row["movieId"]),
                    title=str(row["title"]),
                    year=year,
                    genres=tuple(row["genres_list"]),
                    score=float(scores[row_index]),
                    matched_terms=matched,
                )
            )
            if len(hits) >= top_k:
                break
        return hits

    def profile_scores(self, movie_weights: Mapping[int, float]) -> np.ndarray:
        # Build one taste vector from movies rated above or below the user's mean.
        weights = np.zeros(len(self.movie_ids), dtype=float)
        for movie_id, weight in movie_weights.items():
            row = self._row_by_id.get(int(movie_id))
            if row is not None:
                weights[row] = float(weight)
        if not np.any(weights):
            return np.zeros(len(self.movie_ids), dtype=float)
        weights /= np.sum(np.abs(weights))
        profile = sparse.csr_matrix(weights.reshape(1, -1)) @ self.matrix
        profile = normalize(profile)
        return np.asarray((self.matrix @ profile.T).toarray()).ravel()

    def similarities(
        self, movie_id: int, other_movie_ids: Sequence[int]
    ) -> dict[int, float]:
        source_row = self._row_by_id.get(int(movie_id))
        targets = [
            int(value) for value in other_movie_ids if int(value) in self._row_by_id
        ]
        if source_row is None or not targets:
            return {}
        target_rows = [self._row_by_id[value] for value in targets]
        values = np.asarray(
            (self.matrix[target_rows] @ self.matrix[source_row].T).toarray()
        ).ravel()
        return dict(zip(targets, (float(value) for value in values)))
