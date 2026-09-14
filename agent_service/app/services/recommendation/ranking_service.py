"""Combine content, peer and quality signals into grounded recommendations."""

from __future__ import annotations

import numpy as np
import pandas as pd

from agent_service.app.config import recommendation_settings, search_settings
from agent_service.app.repository import MovieRepository
from agent_service.app.schemas import (
    MovieRecommendation,
    RecommendationEvidence,
    ScoreBreakdown,
    SearchFilter,
    SimilarMovie,
)
from agent_service.app.services.search import TfidfMovieRetriever

from .collaborative_filter import UserUserCollaborativeFilter


class RecommendationService:
    def __init__(
        self,
        repository: MovieRepository,
        retriever: TfidfMovieRetriever,
        collaborative: UserUserCollaborativeFilter,
    ):
        self.repository = repository
        self.retriever = retriever
        self.collaborative = collaborative

    @staticmethod
    def _normalize(values: np.ndarray, eligible: np.ndarray) -> np.ndarray:
        """Scale one ranking signal to 0..1 over eligible movies only."""
        result = np.zeros_like(values, dtype=float)
        valid = eligible & np.isfinite(values)
        if not np.any(valid):
            return result

        minimum = float(values[valid].min())
        maximum = float(values[valid].max())
        if maximum > minimum:
            result[valid] = (values[valid] - minimum) / (maximum - minimum)
        return result

    def _eligible(self, user_id: int, filters: SearchFilter) -> np.ndarray:
        # Never recommend an already-rated movie or one outside explicit filters.
        seen = self.repository.rated_movie_ids(user_id)
        values = []
        for row in self.repository.movies.itertuples(index=False):
            genres = {genre.lower() for genre in row.genres_list}
            accepted = int(row.movieId) not in seen
            accepted &= not any(
                genre.lower() in genres for genre in filters.exclude_genres
            )
            accepted &= filters.min_year is None or (
                not np.isnan(row.year) and int(row.year) >= filters.min_year
            )
            accepted &= filters.max_year is None or (
                not np.isnan(row.year) and int(row.year) <= filters.max_year
            )
            values.append(accepted)
        return np.asarray(values, dtype=bool)

    def _build_recommendations(
        self,
        user_id: int,
        selected: np.ndarray,
        final_scores: np.ndarray,
        scores: dict[str, np.ndarray],
        history: pd.DataFrame,
        query: str,
        filters: SearchFilter,
    ) -> list[MovieRecommendation]:
        """Build API recommendations and their evidence for selected movies."""
        user_mean = float(history["rating"].mean())
        liked = history[history["rating"] >= max(4.0, user_mean)]
        liked = liked.sort_values("rating", ascending=False).head(20)
        liked_ratings = {
            int(row.movieId): float(row.rating) for row in liked.itertuples(index=False)
        }
        favorite_genres = {
            genre
            for genre, _, _ in self.repository.user_profile(user_id).favorite_genres
        }
        search_hits = (
            {
                hit.movie_id: hit
                for hit in self.retriever.search(
                    query, filters=filters, top_k=search_settings.CANDIDATE_POOL
                )
            }
            if query.strip()
            else {}
        )

        recommendations = []
        for row_index in selected:
            if not np.isfinite(final_scores[row_index]):
                continue

            movie = self.repository.get_movie(int(self.repository.movie_ids[row_index]))
            similarities = self.retriever.similarities(
                movie.movie_id, list(liked_ratings)
            )
            similar_movies = []
            for liked_id, similarity in sorted(
                similarities.items(), key=lambda item: item[1], reverse=True
            )[:2]:
                if similarity <= 0:
                    continue
                liked_movie = self.repository.get_movie(liked_id)
                similar_movies.append(
                    SimilarMovie(
                        movie_id=liked_id,
                        title=liked_movie.title,
                        user_rating=liked_ratings[liked_id],
                        similarity=similarity,
                    )
                )

            predicted_rating = scores["collaborative_raw"][row_index]
            search_hit = search_hits.get(movie.movie_id)
            recommendations.append(
                MovieRecommendation(
                    movie_id=movie.movie_id,
                    title=movie.title,
                    year=movie.year,
                    genres=movie.genres,
                    scores=ScoreBreakdown(
                        query=float(scores["query"][row_index]),
                        profile=float(scores["profile"][row_index]),
                        collaborative=float(scores["collaborative"][row_index]),
                        quality=float(scores["quality"][row_index]),
                        final=float(final_scores[row_index]),
                    ),
                    evidence=RecommendationEvidence(
                        matched_terms=search_hit.matched_terms if search_hit else (),
                        matched_genres=tuple(
                            genre for genre in movie.genres if genre in favorite_genres
                        ),
                        similar_liked_movies=tuple(similar_movies),
                        predicted_rating=float(predicted_rating)
                        if np.isfinite(predicted_rating)
                        else None,
                        rating_support=movie.rating_count,
                        confidence="high"
                        if movie.rating_count >= 20
                        and np.isfinite(predicted_rating)
                        else "medium"
                        if movie.rating_count >= 5
                        else "low",
                    ),
                )
            )
        return recommendations

    def recommend(
        self,
        user_id: int,
        query: str,
        filters: SearchFilter,
        top_k: int | None = None,
    ) -> list[MovieRecommendation]:
        if not self.repository.has_user(user_id):
            raise KeyError(f"Unknown userId: {user_id}")

        top_k = top_k or recommendation_settings.DEFAULT_TOP_K
        history = self.repository.user_ratings(user_id)
        eligible = self._eligible(user_id, filters)

        # Calculate the four independent ranking signals.
        user_mean = float(history["rating"].mean())
        query_raw = self.retriever.query_scores(query)
        profile_raw = self.retriever.profile_scores(
            {
                int(row.movieId): float(row.rating) - user_mean
                for row in history.itertuples(index=False)
            }
        )
        collaborative_raw = self.collaborative.predict_scores(user_id)
        quality_raw = self.repository.movies["quality_score"].to_numpy(dtype=float)
        collaborative_score = np.clip((collaborative_raw - 0.5) / 4.5, 0.0, 1.0)
        collaborative_score[~np.isfinite(collaborative_score)] = 0.0
        scores = {
            "query": self._normalize(query_raw, eligible),
            "profile": self._normalize(profile_raw, eligible),
            "collaborative": collaborative_score,
            "quality": np.clip((quality_raw - 0.5) / 4.5, 0.0, 1.0),
            "collaborative_raw": collaborative_raw,
        }

        # A specific query emphasizes relevance; a general request emphasizes taste.
        if query.strip():
            weights = (
                recommendation_settings.QUERY_WEIGHT,
                recommendation_settings.PROFILE_WEIGHT,
                recommendation_settings.COLLABORATIVE_WEIGHT,
                recommendation_settings.QUALITY_WEIGHT,
            )
        else:
            weights = (
                0.0,
                recommendation_settings.GENERAL_PROFILE_WEIGHT,
                recommendation_settings.GENERAL_COLLABORATIVE_WEIGHT,
                recommendation_settings.GENERAL_QUALITY_WEIGHT,
            )
        if len(history) < 20:
            weights = (weights[0], weights[1] + 0.10, 0.10, weights[3] + 0.05)

        total = sum(weights)
        weights = tuple(weight / total for weight in weights)
        final_scores = (
            weights[0] * scores["query"]
            + weights[1] * scores["profile"]
            + weights[2] * scores["collaborative"]
            + weights[3] * scores["quality"]
        )
        final_scores[~eligible] = -np.inf
        selected = np.argsort(final_scores)[::-1][:top_k]

        # Keep response/evidence construction outside the ranking flow.
        return self._build_recommendations(
            user_id=user_id,
            selected=selected,
            final_scores=final_scores,
            scores=scores,
            history=history,
            query=query,
            filters=filters,
        )
