"""Read-only services derived from one user's rating history."""

from agent_service.app.repository import MovieRepository
from agent_service.app.schemas import BlindSpot, UserProfile


class ProfileService:
    def __init__(self, repository: MovieRepository):
        self.repository = repository

    def get_profile(self, user_id: int) -> UserProfile:
        return self.repository.user_profile(user_id)

    def blind_spots(self, user_id: int, limit: int = 3) -> list[BlindSpot]:
        # A blind spot is less represented in user history than in the catalog.
        seen = self.repository.rated_movie_ids(user_id)
        user_movies = self.repository.movies[
            self.repository.movies["movieId"].isin(seen)
        ]
        user_counts: dict[str, int] = {}
        catalog_counts: dict[str, int] = {}
        for genres in user_movies["genres_list"]:
            for genre in genres:
                user_counts[genre] = user_counts.get(genre, 0) + 1
        for genres in self.repository.movies["genres_list"]:
            for genre in genres:
                catalog_counts[genre] = catalog_counts.get(genre, 0) + 1
        genres = sorted(
            catalog_counts,
            key=lambda genre: (
                user_counts.get(genre, 0) / max(1, len(user_movies))
                - catalog_counts[genre] / len(self.repository.movies)
            ),
        )[:limit]
        results = []
        # Suggest strong unseen titles so every gap has an actionable example.
        for genre in genres:
            candidates = self.repository.movies[
                self.repository.movies["genres_list"].map(lambda values: genre in values)
                & ~self.repository.movies["movieId"].isin(seen)
            ].nlargest(3, "quality_score")
            results.append(
                BlindSpot(
                    genre=genre,
                    user_rating_count=user_counts.get(genre, 0),
                    catalog_count=catalog_counts[genre],
                    suggested_movies=tuple(candidates["title"].astype(str)),
                )
            )
        return results
