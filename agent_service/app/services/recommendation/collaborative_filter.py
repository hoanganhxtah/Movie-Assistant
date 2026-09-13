"""Mean-centered user-user collaborative filtering."""

from __future__ import annotations

import numpy as np

from agent_service.app.config import recommendation_settings
from agent_service.app.repository import MovieRepository
from agent_service.app.schemas import PeerOpinion


class UserUserCollaborativeFilter:
    def __init__(self, repository: MovieRepository):
        self.repository = repository
        self.user_ids = np.asarray(repository.user_ids, dtype=int)
        self.movie_ids = repository.movie_ids
        # Rows are users and columns are movies; missing values mean not rated.
        pivot = repository.ratings.pivot_table(
            index="userId", columns="movieId", values="rating", aggfunc="mean"
        ).reindex(index=self.user_ids, columns=self.movie_ids)
        self.ratings = pivot.to_numpy(dtype=float)
        self.observed = ~np.isnan(self.ratings)
        counts = self.observed.sum(axis=1)
        self.user_means = np.divide(
            np.nansum(self.ratings, axis=1),
            counts,
            out=np.full(len(self.user_ids), repository.global_rating_mean),
            where=counts > 0,
        )
        self.centered = np.where(
            self.observed, self.ratings - self.user_means[:, None], 0.0
        )
        self.norms = np.linalg.norm(self.centered, axis=1)
        self._user_row = {
            int(user_id): row for row, user_id in enumerate(self.user_ids)
        }

    def similar_users(self, user_id: int) -> list[tuple[int, float]]:
        row = self._user_row.get(int(user_id))
        if row is None or self.norms[row] == 0:
            return []
        denominator = self.norms * self.norms[row]
        similarity = np.divide(
            self.centered @ self.centered[row],
            denominator,
            out=np.zeros(len(self.user_ids)),
            where=denominator > 0,
        )
        # Penalize similarity based on only a small number of shared ratings.
        overlap = self.observed.astype(np.int16) @ self.observed[row].astype(np.int16)
        similarity *= overlap / (overlap + recommendation_settings.OVERLAP_SHRINKAGE)
        similarity[row] = -np.inf
        valid = np.flatnonzero(
            (similarity > 0)
            & (overlap >= recommendation_settings.MINIMUM_OVERLAP)
        )
        ordered = valid[np.argsort(similarity[valid])[::-1]][
            : recommendation_settings.NEIGHBOR_COUNT
        ]
        return [
            (int(self.user_ids[index]), float(similarity[index])) for index in ordered
        ]

    def predict_scores(self, user_id: int) -> np.ndarray:
        user_row = self._user_row.get(int(user_id))
        predictions = np.full(len(self.movie_ids), np.nan)
        if user_row is None:
            return predictions
        neighbors = self.similar_users(user_id)
        if not neighbors:
            return predictions
        rows = np.asarray([self._user_row[user] for user, _ in neighbors])
        weights = np.asarray([score for _, score in neighbors])
        numerator = weights @ self.centered[rows]
        denominator = np.abs(weights) @ self.observed[rows].astype(float)
        residual = np.divide(
            numerator,
            denominator,
            out=np.full(len(self.movie_ids), np.nan),
            where=denominator > 0,
        )
        raw_prediction = np.clip(self.user_means[user_row] + residual, 0.5, 5.0)
        # A perfect score from one neighbor is weak evidence. Shrink it toward
        # the movie's Bayesian quality score until several neighbors rated it.
        support = self.observed[rows].sum(axis=0).astype(float)
        prior = self.repository.movies["quality_score"].to_numpy(dtype=float)
        shrinkage = recommendation_settings.PREDICTION_SHRINKAGE
        prediction = (
            support * raw_prediction + shrinkage * prior
        ) / (support + shrinkage)
        prediction[denominator == 0] = np.nan
        return prediction

    def peer_opinion(self, user_id: int, movie_id: int) -> PeerOpinion:
        """Aggregate ratings for a movie from the nearest taste neighbors."""
        movie = self.repository.get_movie(movie_id)
        neighbor_ids = {user for user, _ in self.similar_users(user_id)}
        values = self.repository.ratings[
            (self.repository.ratings["movieId"] == int(movie_id))
            & (self.repository.ratings["userId"].isin(neighbor_ids))
        ]["rating"]
        count = len(values)
        return PeerOpinion(
            movie_id=movie.movie_id,
            title=movie.title,
            peer_count=count,
            mean_rating=float(values.mean()) if count else None,
            positive_share=float((values >= 4.0).mean()) if count else None,
            confidence="low" if count < 3 else "medium" if count < 10 else "high",
        )
