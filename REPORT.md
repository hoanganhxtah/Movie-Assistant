# Report: Movie Discovery Agent

## Problem Analysis

Users have an existing MovieLens rating history and want to discover movies through
natural-language conversations. A useful recommendation must match the current
intent, reflect long-term preferences, satisfy explicit constraints, exclude movies
the user has already rated, and provide reasons traceable to the data. This makes the
task more than a simple search problem.

The three main challenges are that 51% of the movies have fewer than five ratings,
tags are sparse, and plots are long while user queries are short. The system must
also combine content and collaborative signals, remember previous recommendations
for follow-up questions, and prevent the LLM from inventing facts or statistics.

## Approach

The system consists of an independent Streamlit UI and a FastAPI backend. The core
`MovieAgent` is built with `langchain.agents.create_agent` and supports tool calling
through five domain tools: `recommend_movies`, `search_movies`, `get_user_profile`,
`get_peer_opinion`, and `find_blind_spots`. The LLM interprets the conversation and
selects an appropriate tool, or answers greetings and small talk directly without
producing irrelevant recommendation results. Conversation history is maintained by
an `InMemorySaver` checkpointer keyed by `thread_id` to support follow-up questions.

The recommendation pipeline combines:

- TF-IDF word unigrams and bigrams over titles, genres, tags, and plots, with a
  metadata boost.
- A mean-centered content profile built from movies rated by the user.
- User-user collaborative filtering with cosine similarity, minimum overlap, and
  shrinkage to reduce confidence in neighbors with limited shared data.
- Bayesian movie quality so movies with very few ratings do not dominate the ranking
  only because of a high average score.
- Hard filters for previously rated movies, excluded genres, and year ranges.

Heavy objects are initialized once during the FastAPI lifespan. With a static corpus
of 5,135 movies, an in-memory index is simpler and sufficiently fast; a separate RAG
microservice or vector database is not yet necessary.

### Decision Log

| Decision | Alternative considered | Rationale |
|---|---|---|
| One LangChain tool-calling agent | Supervisor or multi-agent graph | One model is sufficient to select among five tools; the design is compact, has lower latency, and supports multiple providers |
| Local TF-IDF retrieval in the backend | Reuse `rag_service` with Qdrant or Chroma | The corpus is small and static, so this avoids an additional service while still supporting effective keyword and plot search |
| Hybrid content, collaborative, and quality ranking | Content-only, collaborative-only, or popularity-only ranking | Each signal compensates for weaknesses in the others and produces understandable evidence |

## Evaluation

The system is evaluated with 23 automated tests and sample conversations based on
the assignment requirements. All tests currently pass. The main scenarios are:

| Test scenario | Expected behavior | Result |
|---|---|---|
| General recommendation for a user | Use rating history to recommend unseen movies | Pass |
| Search for “a dark psychological thriller with a twist” | Return relevant movies from the local catalog | Pass |
| Follow up with “Why would I like that?” | Preserve the context of the previous recommendation | Pass |
| Ask what users with similar taste think | Use ratings from similar users and return supporting evidence | Pass |
| Like Toy Story but exclude Animation | Use the reference movie while enforcing the excluded genre | Pass |
| Request Action movies after 2002 | Return only Action movies released from 2003 onward | Pass |
| Request a specific number of movies | Do not return more movies than requested | Pass |
| Find genres the user has explored less | Return blind spots with unseen movie suggestions | Pass |
| Send a normal greeting | Answer directly without calling the recommendation tool | Pass |
| Check grounding | Ensure returned movie IDs and evidence belong to the dataset | Pass |
| Use an unknown user | Reject the API request instead of generating an invalid recommendation | Pass |

### Failure Analysis

1. For “a dark psychological thriller with a twist,” `Zero Dark Thirty` may appear
   near the top because *dark* occurs in the title and the movie has the Thriller
   genre, even though it is not a psychological twist story. TF-IDF matches terms but
   does not understand their semantic role. Embeddings or a lightweight reranker over
   the top candidates would improve this case.
2. For “I liked Toy Story but I am tired of animated movies,” `A Kid in King Arthur's
   Court` matches four genres, but its collaborative prediction is only 2.91/5. Query
   relevance can currently outweigh the negative preference signal. A minimum
   predicted-rating threshold or weights learned on a validation set could improve
   this behavior.
3. A blind spot currently means that a genre is underrepresented in the user's
   history compared with the catalog. It does not distinguish between a genre the
   user intentionally avoids and one they have not explored. The system should ask a
   follow-up question or include rating sentiment before labeling it a blind spot.

## Reflection

The main strength is that retrieval, profile construction, collaborative filtering,
and ranking run locally on the dataset. Structured scores and evidence are not
invented by the LLM. The end-to-end conversational flow still requires a configured
LLM provider and its corresponding API key. Hard constraints are enforced by the
recommendation service after the agent converts them into filters, reducing the risk
of answers that contradict the retrieved data. The UI communicates only through
HTTP, so the backend can be reused by other clients.

The main weakness is that pure TF-IDF does not capture subtle semantic differences,
such as identical words used in different contexts. The current tests focus on the
main workflows and do not yet fully cover provider failures, concurrent requests, or
prompt injection. With more time, I would evaluate multiple temporal folds, measure
constraint compliance and explanation faithfulness, and add semantic reranking before
considering a separate retrieval microservice for larger corpora or higher traffic.

## Future Work

Separating the LLM from retrieval and ranking keeps the data signals testable and
reproducible for the same tool input. However, changing the provider or model can
still change the end-to-end result because the LLM decides which tool to call and how
to transform a request into a query, genres, years, and a reference movie. Evaluation
must therefore cover tool routing, constraint extraction, and grounding for each
model, rather than comparing only response fluency.

The next optimization priorities are:

1. Introduce a multi-agent architecture only when the workflow requires it. An
   orchestrator can delegate complex requests to specialized components: a local
   search and recommendation agent, an evidence and result-quality evaluator, and a
   web-search agent when the local catalog does not contain enough information. Web
   results must include citations and remain clearly separated from ratings in the
   local dataset. Simple requests should continue through the current single-agent
   path to avoid unnecessary latency and cost. Retry should not be an unconstrained
   autonomous agent; it should be implemented as a recovery node or orchestration
   policy with attempt limits, timeouts, and explicit stop conditions.
2. Add semantic retrieval or a cross-encoder reranker over the TF-IDF candidate pool
   to better understand themes, moods, and semantic relationships while preserving
   hard filters and traceable evidence.
3. Build a dedicated search-evaluation suite for configuring and comparing retrieval
   approaches. It should contain fixed queries for keyword search, semantic search,
   genre and year filters, negative constraints, and no-result cases. Parameters such
   as metadata boost, candidate-pool size, semantic threshold, and combination weights
   should be moved into configuration. Every change should rerun the suite so a better
   configuration can be selected before release.
4. Replace `InMemorySaver` with a checkpoint store that supports TTL and context
   limits. Bind each `thread_id` to the authenticated user, and add rate limiting,
   timeouts, tracing, and readiness checks before deploying multiple workers.
