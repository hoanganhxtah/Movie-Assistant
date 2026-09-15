"""The only module that reads and joins the source CSV files."""

from __future__ import annotations

import re
from difflib import get_close_matches
from pathlib import Path

import pandas as pd

from agent_service.app.schemas import Movie, UserProfile


REQUIRED_MOVIE_COLUMNS = {"movieId", "title", "year", "genres", "plot"}
REQUIRED_RATING_COLUMNS = {"userId", "movieId", "rating", "timestamp"}
REQUIRED_TAG_COLUMNS = {"userId", "movieId", "tag", "timestamp"}


class DatasetError(ValueError):
    """Raised when the local CSV files do not match the expected schema."""

    pass


def normalize_title(value: str) -> str:
    """Normalize a title for exact, embedded and fuzzy lookup."""
    value = re.sub(r"\(\d{4}\)\s*$", "", str(value))
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


class MovieRepository:
    def __init__(
        self,
        movies: pd.DataFrame,
        ratings: pd.DataFrame,
        tags: pd.DataFrame,
    ):
        """Create a repository from movie, rating and tag data."""
        self.movies = movies.copy()
        self.ratings = ratings.copy()
        self.tags = tags.copy()
        self._validate()
        self._prepare()

    def _validate(self) -> None:
        # Fail at startup instead of returning unreliable recommendations later.
        for name, frame, required in (
            ("movies", self.movies, REQUIRED_MOVIE_COLUMNS),
            ("ratings", self.ratings, REQUIRED_RATING_COLUMNS),
            ("tags", self.tags, REQUIRED_TAG_COLUMNS),
        ):
            missing = required.difference(frame.columns)
            if missing:
                raise DatasetError(f"{name} missing columns: {sorted(missing)}")
        if self.movies["movieId"].duplicated().any():
            raise DatasetError("movieId must be unique")
        if self.movies["plot"].isna().any():
            raise DatasetError("plot must be present for every movie")
        if not self.ratings["rating"].between(0.5, 5.0).all():
            raise DatasetError("rating must be between 0.5 and 5.0")
        movie_ids = set(self.movies["movieId"].astype(int))
        for name, frame in (("ratings", self.ratings), ("tags", self.tags)):
            orphan_ids = set(frame["movieId"].astype(int)).difference(movie_ids)
            if orphan_ids:
                raise DatasetError(f"{name} has movieId outside the catalog")

    def _prepare(self) -> None:
        # Convert raw CSV columns into structures reused by search and ranking.
        self.movies = self.movies.copy()
        self.ratings = self.ratings.copy()
        self.tags = self.tags.copy()
        self.movies["movieId"] = self.movies["movieId"].astype(int)
        self.movies["year"] = pd.to_numeric(self.movies["year"], errors="coerce")
        self.movies["genres_list"] = self.movies["genres"].fillna("").map(
            lambda value: tuple(
                genre
                for genre in str(value).split("|")
                if genre and genre != "(no genres listed)"
            )
        )
        self.tags["tag"] = self.tags["tag"].fillna("").astype(str).str.strip().str.lower()
        tag_map = (
            self.tags[self.tags["tag"] != ""]
            .groupby("movieId")["tag"]
            .agg(lambda values: tuple(dict.fromkeys(values)))
            .to_dict()
        )
        self.movies["tags_list"] = self.movies["movieId"].map(
            lambda movie_id: tag_map.get(int(movie_id), ())
        )

        # Bayesian quality avoids overrating movies with only a few votes.
        stats = self.ratings.groupby("movieId")["rating"].agg(["mean", "count"])
        global_mean = float(self.ratings["rating"].mean())
        minimum_votes = max(5.0, float(stats["count"].quantile(0.60)))
        self.movies = self.movies.join(stats, on="movieId")
        self.movies["rating_count"] = self.movies["count"].fillna(0).astype(int)
        self.movies["rating_mean"] = self.movies["mean"]
        counts = self.movies["rating_count"].astype(float)
        means = self.movies["rating_mean"].fillna(global_mean)
        self.movies["quality_score"] = (
            counts / (counts + minimum_votes) * means
            + minimum_votes / (counts + minimum_votes) * global_mean
        )
        self.global_rating_mean = global_mean

        self.movies.reset_index(drop=True, inplace=True)
        self.movie_ids = self.movies["movieId"].to_numpy(dtype=int)
        self.user_ids = tuple(
            sorted(int(user_id) for user_id in self.ratings["userId"].unique())
        )
        # Lookup maps avoid repeatedly scanning DataFrames during a request.
        self._row_by_id = {
            int(movie_id): row for row, movie_id in enumerate(self.movie_ids)
        }
        self._title_to_ids: dict[str, list[int]] = {}
        for movie_id, title in self.movies[["movieId", "title"]].itertuples(index=False):
            self._title_to_ids.setdefault(normalize_title(title), []).append(int(movie_id))
        self._titles_by_length = sorted(
            (title for title in self._title_to_ids if len(title) >= 4),
            key=len,
            reverse=True,
        )

    def has_user(self, user_id: int) -> bool:
        return int(user_id) in self.user_ids

    def row_for_movie(self, movie_id: int) -> int:
        return self._row_by_id[int(movie_id)]

    def get_movie(self, movie_id: int) -> Movie:
        row = self.movies.iloc[self.row_for_movie(movie_id)]
        return Movie(
            movie_id=int(row["movieId"]),
            title=str(row["title"]),
            year=None if pd.isna(row["year"]) else int(row["year"]),
            genres=tuple(row["genres_list"]),
            plot=str(row["plot"]),
            tags=tuple(row["tags_list"]),
            rating_mean=None
            if pd.isna(row["rating_mean"])
            else float(row["rating_mean"]),
            rating_count=int(row["rating_count"]),
            quality_score=float(row["quality_score"]),
        )

    def user_ratings(self, user_id: int) -> pd.DataFrame:
        return self.ratings[self.ratings["userId"] == int(user_id)].copy()

    def rated_movie_ids(self, user_id: int) -> set[int]:
        return set(self.user_ratings(user_id)["movieId"].astype(int))

    def resolve_title(self, text: str) -> Movie | None:
        """Resolve a full or embedded title, then fall back to a close match."""
        normalized = normalize_title(text)
        exact = self._title_to_ids.get(normalized)
        if exact:
            return self.get_movie(exact[0])
        padded = f" {normalized} "
        for title in self._titles_by_length:
            if f" {title} " in padded:
                return self.get_movie(self._title_to_ids[title][0])
        match = get_close_matches(normalized, self._title_to_ids, n=1, cutoff=0.80)
        return self.get_movie(self._title_to_ids[match[0]][0]) if match else None

    def user_profile(self, user_id: int) -> UserProfile:
        """Summarize the genres and movies most liked by one user."""
        ratings = self.user_ratings(user_id)
        if ratings.empty:
            raise KeyError(f"Unknown userId: {user_id}")
        joined = ratings.merge(
            self.movies[["movieId", "title", "genres_list"]],
            on="movieId",
            how="left",
        )
        genre_rows = [
            (genre, float(row.rating))
            for row in joined.itertuples(index=False)
            for genre in row.genres_list
        ]
        genre_frame = pd.DataFrame(genre_rows, columns=["genre", "rating"])
        genre_stats = genre_frame.groupby("genre")["rating"].agg(["mean", "count"])
        favorites = tuple(
            (str(genre), float(row["mean"]), int(row["count"]))
            for genre, row in genre_stats.sort_values(
                ["mean", "count"], ascending=False
            ).head(5).iterrows()
        )
        liked = joined.sort_values(["rating", "timestamp"], ascending=False).head(5)
        return UserProfile(
            user_id=int(user_id),
            rating_count=len(ratings),
            average_rating=float(ratings["rating"].mean()),
            favorite_genres=favorites,
            liked_movies=tuple(
                (int(row.movieId), str(row.title), float(row.rating))
                for row in liked.itertuples(index=False)
            ),
        )


def load_movie_repository(data_dir: str | Path) -> MovieRepository:
    """Read MovieLens CSV files and create a repository."""
    data_dir = Path(data_dir)
    return MovieRepository(
        movies=pd.read_csv(data_dir / "movies_with_plots.csv"),
        ratings=pd.read_csv(data_dir / "ratings.csv"),
        tags=pd.read_csv(data_dir / "tags.csv"),
    )
