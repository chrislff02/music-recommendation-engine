import { useCallback, useEffect, useState } from "react";

import "./App.css";

type Song = {
  id: number;

  title: string;

  externalId: string;

  tempo: number;

  energy: number;

  danceability: number;

  valence: number;

  acousticness: number;

  instrumentalness: number;

  speechiness: number;

  liveness: number;

  popularity: number;

  duration: number;

  artist: string;

  genre: string | null;
};

type SongsResponse = {
  page: number;

  limit: number;

  total: number;

  totalPages: number;

  songs: Song[];
};

type User = {
  id: number;

  email: string;

  username: string;

  createdAt: string;
};

type AuthResponse = {
  user: User;

  token: string;
};

type Recommendation = {
  id: number;

  title: string;

  artist: string;

  genre: string | null;

  positive_similarity: number;

  negative_similarity: number;

  genre_score: number;

  popularity: number;

  score: number;

  explanation: string;
};

type RecommendationsResponse = {
  recommendations: Recommendation[];
};

const GENRES = [
  "",

  "Rock",

  "Electronic",

  "Hip-Hop",

  "Folk",

  "Old-Time / Historic",

  "Pop",

  "Classical",

  "Jazz",

  "International",

  "Instrumental",

  "Blues",

  "Experimental",
];

function App() {
  const [songs, setSongs] = useState<Song[]>([]);

  const [page, setPage] = useState(1);

  const [totalPages, setTotalPages] = useState(1);

  const [searchInput, setSearchInput] = useState("");

  const [search, setSearch] = useState("");

  const [genre, setGenre] = useState("");

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const [user, setUser] = useState<User | null>(null);

  const [token, setToken] = useState(
    () => sessionStorage.getItem("token") ?? "",
  );

  const [authMode, setAuthMode] = useState<"login" | "register">("login");

  const [authEmail, setAuthEmail] = useState("");

  const [authUsername, setAuthUsername] = useState("");

  const [authPassword, setAuthPassword] = useState("");

  const [authError, setAuthError] = useState("");

  const [ratings, setRatings] = useState<Record<number, number>>({});

  const [ratingError, setRatingError] = useState("");

  const [ratingsLoaded, setRatingsLoaded] = useState(false);

  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  const [recommendationsLoading, setRecommendationsLoading] = useState(false);

  const [recommendationsError, setRecommendationsError] = useState("");

  useEffect(() => {
    async function fetchSongs() {
      try {
        setLoading(true);

        setError("");

        const params = new URLSearchParams({
          page: String(page),

          limit: "10",
        });

        if (search) {
          params.set("search", search);
        }

        if (genre) {
          params.set("genre", genre);
        }

        const response = await fetch(
          `http://localhost:5001/api/songs?${params.toString()}`,
        );

        if (!response.ok) {
          throw new Error("Failed to fetch songs");
        }

        const data: SongsResponse = await response.json();

        setSongs(data.songs);

        setTotalPages(data.totalPages);
      } catch (err) {
        console.error(err);

        setError("Could not load songs.");
      } finally {
        setLoading(false);
      }
    }

    fetchSongs();
  }, [page, search, genre]);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setRatings({});
      setRatingsLoaded(false);
      return;
    }

    async function fetchCurrentUser() {
      try {
        const response = await fetch("http://localhost:5001/api/auth/me", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error("Invalid session");
        }

        const data = await response.json();

        setUser(data.user);

        const ratingsResponse = await fetch(
          "http://localhost:5001/api/ratings/me",
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          },
        );

        if (!ratingsResponse.ok) {
          throw new Error("Failed to load ratings");
        }

        const ratingsData = await ratingsResponse.json();

        const ratingsMap: Record<number, number> = {};

        for (const rating of ratingsData.ratings) {
          ratingsMap[rating.songId] = rating.value;
        }

        setRatings(ratingsMap);
        setRatingsLoaded(true);
      } catch {
        sessionStorage.removeItem("token");
        setToken("");
        setUser(null);
        setRatings({});
        setRatingsLoaded(false);
        setRecommendations([]);
      }
    }

    fetchCurrentUser();
  }, [token]);

  const fetchRecommendations = useCallback(async () => {
    if (!token) {
      return;
    }

    try {
      setRecommendationsLoading(true);

      setRecommendationsError("");

      const response = await fetch(
        "http://localhost:5001/api/recommendations",

        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      const data: RecommendationsResponse = await response.json();

      if (!response.ok) {
        throw new Error("Failed to load recommendations");
      }

      setRecommendations(data.recommendations);
    } catch (err) {
      if (err instanceof Error) {
        setRecommendationsError(err.message);
      } else {
        setRecommendationsError("Failed to load recommendations");
      }
    } finally {
      setRecommendationsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!user || !ratingsLoaded) {
      return;
    }

    const hasMeaningfulRatings = Object.values(ratings).some(
      (value) => value !== 3,
    );

    if (!hasMeaningfulRatings) {
      setRecommendations([]);
      return;
    }

    void fetchRecommendations();
  }, [user, ratings, ratingsLoaded, fetchRecommendations]);

  function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setPage(1);

    setSearch(searchInput.trim());
  }

  function handleGenreChange(event: React.ChangeEvent<HTMLSelectElement>) {
    setPage(1);

    setGenre(event.target.value);
  }

  function handleClearFilters() {
    setSearchInput("");

    setSearch("");

    setGenre("");

    setPage(1);
  }

  async function handleAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      setAuthError("");

      const endpoint =
        authMode === "login"
          ? "http://localhost:5001/api/auth/login"
          : "http://localhost:5001/api/auth/register";

      const body =
        authMode === "login"
          ? {
              email: authEmail,

              password: authPassword,
            }
          : {
              email: authEmail,

              username: authUsername,

              password: authPassword,
            };

      const response = await fetch(endpoint, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error ?? "Authentication failed");
      }

      const authData = data as AuthResponse;

      sessionStorage.setItem("token", authData.token);

      setToken(authData.token);

      setUser(authData.user);

      setAuthEmail("");

      setAuthUsername("");

      setAuthPassword("");
    } catch (err) {
      if (err instanceof Error) {
        setAuthError(err.message);
      } else {
        setAuthError("Authentication failed");
      }
    }
  }

  async function handleRateSong(songId: number, value: number) {
    if (!token) {
      setRatingError("You must be logged in to rate songs.");

      return false;
    }

    try {
      setRatingError("");

      const response = await fetch("http://localhost:5001/api/ratings", {
        method: "POST",

        headers: {
          "Content-Type": "application/json",

          Authorization: `Bearer ${token}`,
        },

        body: JSON.stringify({
          songId,

          value,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error ?? "Failed to save rating");
      }

      setRatings((current) => ({
        ...current,

        [songId]: data.rating.value,
      }));

      return true;
    } catch (err) {
      if (err instanceof Error) {
        setRatingError(err.message);
      } else {
        setRatingError("Failed to save rating");
      }

      return false;
    }
  }

  async function handleRateRecommendation(songId: number, value: number) {
    await handleRateSong(songId, value);
  }

  function handleLogout() {
    sessionStorage.removeItem("token");

    setToken("");

    setUser(null);

    setRatings({});

    setRatingsLoaded(false);

    setRecommendations([]);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">♪</div>

          <div>
            <h2>MusicMatch</h2>

            <p>Discovery Engine</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <a className="nav-item active" href="#home">
            <span className="nav-icon">⌂</span>
            Home
          </a>

          {user && (
            <a className="nav-item" href="#recommendations">
              <span className="nav-icon">★</span>
              For You
            </a>
          )}

          <a className="nav-item" href="#browse">
            <span className="nav-icon">⌕</span>
            Browse
          </a>
        </nav>

        <div className="sidebar-spacer" />

        <div className="sidebar-account">
          {user ? (
            <>
              <div className="user-avatar">
                {user.username.charAt(0).toUpperCase()}
              </div>

              <div className="sidebar-user-info">
                <span>Signed in as</span>

                <strong>{user.username}</strong>
              </div>

              <button
                type="button"
                className="sidebar-logout"
                onClick={handleLogout}
              >
                Log Out
              </button>
            </>
          ) : (
            <>
              <div className="user-avatar">?</div>

              <div className="sidebar-user-info">
                <span>Browsing as</span>

                <strong>Guest</strong>
              </div>
            </>
          )}
        </div>
      </aside>

      <main className="main-content">
        <header className="app-header" id="home">
          <div>
            <p className="eyebrow">Personalized Music Discovery</p>

            <h1>Music Recommendation Engine</h1>

            <p className="app-subtitle">
              Rate songs and discover music matched to your taste.
            </p>
          </div>
        </header>

        {!user && (
          <section className="auth-section">
            <div className="auth-card">
              <div className="section-heading">
                <p className="eyebrow">Your Account</p>

                <h2>
                  {authMode === "login" ? "Welcome Back" : "Create an Account"}
                </h2>
              </div>

              <form className="auth-form" onSubmit={handleAuth}>
                <input
                  type="email"
                  placeholder="Email"
                  value={authEmail}
                  onChange={(event) => setAuthEmail(event.target.value)}
                />

                {authMode === "register" && (
                  <input
                    type="text"
                    placeholder="Username"
                    value={authUsername}
                    onChange={(event) => setAuthUsername(event.target.value)}
                  />
                )}

                <input
                  type="password"
                  placeholder="Password"
                  value={authPassword}
                  onChange={(event) => setAuthPassword(event.target.value)}
                />

                <button type="submit" className="primary-button">
                  {authMode === "login" ? "Log In" : "Register"}
                </button>
              </form>

              {authError && <p className="error-message">{authError}</p>}

              <button
                type="button"
                className="text-button"
                onClick={() =>
                  setAuthMode((current) =>
                    current === "login" ? "register" : "login",
                  )
                }
              >
                {authMode === "login"
                  ? "Need an account? Register"
                  : "Already have an account? Log In"}
              </button>
            </div>
          </section>
        )}

        {user && (
          <section className="recommendations-section" id="recommendations">
            {" "}
            <div className="recommendations-header">
              <div>
                <p className="eyebrow">Made For You</p>

                <h2>Recommended For You</h2>

                <p className="recommendations-subtitle">
                  Personalized using your ratings and listening preferences.
                </p>
              </div>

              <button
                type="button"
                className="primary-button"
                onClick={fetchRecommendations}
                disabled={recommendationsLoading}
              >
                {recommendationsLoading
                  ? "Refreshing..."
                  : recommendations.length > 0
                    ? "Refresh Recommendations"
                    : "Get Recommendations"}
              </button>
            </div>
            {recommendationsLoading && (
              <div className="status-message">
                Generating recommendations...
              </div>
            )}
            {recommendationsError && (
              <p className="error-message">{recommendationsError}</p>
            )}
            {!recommendationsLoading &&
              recommendations.length === 0 &&
              !recommendationsError && (
                <div className="recommendations-empty">
                  <div className="empty-icon">♪</div>

                  <h3>No recommendations yet</h3>

                  <p>
                    Rate a few songs to help the recommendation engine
                    understand what you like.
                  </p>
                </div>
              )}
            {recommendations.length > 0 && (
              <div className="recommendations-grid">
                {recommendations.map((song) => (
                  <article className="recommendation-card" key={song.id}>
                    <div className="recommendation-card-header">
                      <div>
                        <h3 className="recommendation-title">{song.title}</h3>

                        <p className="recommendation-meta">
                          {song.artist}

                          <span>•</span>

                          {song.genre ?? "Unknown"}
                        </p>
                      </div>

                      <div className="match-badge">
                        {(song.score * 100).toFixed(1)}% Match
                      </div>
                    </div>

                    <p className="recommendation-explanation">
                      {song.explanation}
                    </p>

                    <div className="recommendation-rating">
                      <div>
                        <span className="rating-label">Your rating</span>

                        <p className="rating-value">
                          {ratings[song.id]
                            ? `${ratings[song.id]}/5`
                            : "Not rated"}
                        </p>
                      </div>

                      <div
                        className="rating-buttons"
                        aria-label={`Rate ${song.title}`}
                      >
                        {[1, 2, 3, 4, 5].map((value) => (
                          <button
                            key={value}
                            type="button"
                            title={`${value} out of 5`}
                            aria-label={`Rate ${song.title} ${value} out of 5`}
                            className={
                              ratings[song.id] === value
                                ? "rating-button selected"
                                : "rating-button"
                            }
                            onClick={() =>
                              handleRateRecommendation(song.id, value)
                            }
                          >
                            ★
                          </button>
                        ))}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        <section className="browse-section" id="browse">
          <div className="section-heading browse-heading">
            <div>
              <p className="eyebrow">Explore</p>

              <h2>Browse Songs</h2>

              <p>
                Search the catalog and rate songs to improve your
                recommendations.
              </p>
            </div>
          </div>

          <div className="filters-card">
            <form className="search-form" onSubmit={handleSearch}>
              <input
                type="text"
                placeholder="Search songs or artists..."
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />

              <button type="submit" className="primary-button">
                Search
              </button>
            </form>

            <div className="filter-row">
              <div className="genre-filter">
                <label htmlFor="genre">Genre</label>

                <select id="genre" value={genre} onChange={handleGenreChange}>
                  {GENRES.map((genreOption) => (
                    <option key={genreOption || "all"} value={genreOption}>
                      {genreOption || "All Genres"}
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="button"
                className="secondary-button"
                onClick={handleClearFilters}
              >
                Clear Filters
              </button>
            </div>
          </div>

          {loading && <div className="status-message">Loading songs...</div>}

          {error && <p className="error-message">{error}</p>}

          {ratingError && <p className="error-message">{ratingError}</p>}

          {!loading && !error && songs.length === 0 && (
            <div className="status-message">No songs found.</div>
          )}

          {!loading && !error && songs.length > 0 && (
            <>
              <div className="songs-grid">
                {songs.map((song) => (
                  <article className="song-card" key={song.id}>
                    <div className="song-card-top">
                      <div>
                        <h3>{song.title}</h3>

                        <p className="song-artist">{song.artist}</p>
                      </div>

                      <span className="genre-badge">
                        {song.genre ?? "Unknown"}
                      </span>
                    </div>

                    <div className="song-details">
                      <span>Duration</span>

                      <strong>
                        {Math.floor(song.duration / 60)}:
                        {String(song.duration % 60).padStart(2, "0")}
                      </strong>
                    </div>

                    {user ? (
                      <div className="song-rating">
                        <div>
                          <span className="rating-label">Your rating</span>

                          <p className="rating-value">
                            {ratings[song.id]
                              ? `${ratings[song.id]}/5`
                              : "Not rated"}
                          </p>
                        </div>

                        <div className="rating-buttons">
                          {[1, 2, 3, 4, 5].map((value) => (
                            <button
                              key={value}
                              type="button"
                              title={`${value} out of 5`}
                              className={
                                ratings[song.id] === value
                                  ? "rating-button selected"
                                  : "rating-button"
                              }
                              onClick={() => handleRateSong(song.id, value)}
                            >
                              ★
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="login-message">Log in to rate this song.</p>
                    )}
                  </article>
                ))}
              </div>

              <div className="pagination">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setPage((current) => current - 1)}
                  disabled={page === 1}
                >
                  Previous
                </button>

                <span>
                  Page <strong>{page}</strong> of <strong>{totalPages}</strong>
                </span>

                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setPage((current) => current + 1)}
                  disabled={page === totalPages}
                >
                  Next
                </button>
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
