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

type PreferenceItem = {
  id: number;
  name: string;
};

type PreferencesResponse = {
  genres: PreferenceItem[];
  artists: PreferenceItem[];
};

type GenresResponse = {
  genres: PreferenceItem[];
};

type ArtistsResponse = {
  artists: PreferenceItem[];
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
  const [expandedRecommendations, setExpandedRecommendations] = useState<
    Record<number, boolean>
  >({});
  const [activeSection, setActiveSection] = useState<
    "home" | "recommendations" | "browse"
  >("home");
  const [preferencesLoaded, setPreferencesLoaded] = useState(false);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [savedFavoriteGenres, setSavedFavoriteGenres] = useState<
    PreferenceItem[]
  >([]);
  const [savedFavoriteArtists, setSavedFavoriteArtists] = useState<
    PreferenceItem[]
  >([]);
  const [selectedGenreIds, setSelectedGenreIds] = useState<number[]>([]);
  const [selectedArtists, setSelectedArtists] = useState<PreferenceItem[]>([]);
  const [availableGenres, setAvailableGenres] = useState<PreferenceItem[]>([]);
  const [artistSearchInput, setArtistSearchInput] = useState("");
  const [artistSearchResults, setArtistSearchResults] = useState<
    PreferenceItem[]
  >([]);
  const [artistSearchLoading, setArtistSearchLoading] = useState(false);
  const [preferencesSaving, setPreferencesSaving] = useState(false);
  const [preferencesError, setPreferencesError] = useState("");
  const meaningfulRatingCount = Object.values(ratings).filter(
    (value) => value !== 3,
  ).length;

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

  useEffect(() => {
    if (!user || !token) {
      setPreferencesLoaded(false);
      setPreferencesOpen(false);
      setSavedFavoriteGenres([]);
      setSavedFavoriteArtists([]);
      setSelectedGenreIds([]);
      setSelectedArtists([]);
      setAvailableGenres([]);
      return;
    }

    async function fetchPreferences() {
      try {
        setPreferencesLoaded(false);
        setPreferencesError("");

        const [preferencesResponse, genresResponse] = await Promise.all([
          fetch("http://localhost:5001/api/preferences", {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }),

          fetch("http://localhost:5001/api/genres"),
        ]);

        if (!preferencesResponse.ok) {
          throw new Error("Failed to load your music preferences");
        }

        if (!genresResponse.ok) {
          throw new Error("Failed to load genres");
        }

        const preferencesData: PreferencesResponse =
          await preferencesResponse.json();

        const genresData: GenresResponse = await genresResponse.json();

        setSavedFavoriteGenres(preferencesData.genres);
        setSavedFavoriteArtists(preferencesData.artists);

        setSelectedGenreIds(
          preferencesData.genres.map((genreItem) => genreItem.id),
        );

        setSelectedArtists(preferencesData.artists);

        setAvailableGenres(genresData.genres);

        const hasPreferences =
          preferencesData.genres.length > 0 ||
          preferencesData.artists.length > 0;

        setPreferencesOpen(!hasPreferences);
        setPreferencesLoaded(true);
      } catch (err) {
        if (err instanceof Error) {
          setPreferencesError(err.message);
        } else {
          setPreferencesError("Failed to load music preferences");
        }

        setPreferencesLoaded(true);
      }
    }

    void fetchPreferences();
  }, [user, token]);

  useEffect(() => {
    if (!preferencesOpen) {
      return;
    }

    const searchTerm = artistSearchInput.trim();

    if (searchTerm.length < 2) {
      setArtistSearchResults([]);
      setArtistSearchLoading(false);
      return;
    }

    const controller = new AbortController();

    const timeoutId = window.setTimeout(async () => {
      try {
        setArtistSearchLoading(true);

        const params = new URLSearchParams({
          search: searchTerm,
          limit: "12",
        });

        const response = await fetch(
          `http://localhost:5001/api/artists?${params.toString()}`,
          {
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          throw new Error("Failed to search artists");
        }

        const data: ArtistsResponse = await response.json();

        setArtistSearchResults(data.artists);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }

        console.error(err);
      } finally {
        if (!controller.signal.aborted) {
          setArtistSearchLoading(false);
        }
      }
    }, 300);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [artistSearchInput, preferencesOpen]);

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

  useEffect(() => {
    const sectionIds = ["home", "recommendations", "browse"];

    const sections = sectionIds
      .map((id) => document.getElementById(id))
      .filter((section): section is HTMLElement => section !== null);

    if (sections.length === 0) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntries = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (visibleEntries.length === 0) {
          return;
        }

        const id = visibleEntries[0].target.id;

        if (id === "home" || id === "recommendations" || id === "browse") {
          setActiveSection(id);
        }
      },
      {
        root: null,
        rootMargin: "-20% 0px -55% 0px",
        threshold: [0.1, 0.25, 0.5, 0.75],
      },
    );

    sections.forEach((section) => observer.observe(section));

    return () => {
      observer.disconnect();
    };
  }, [user]);

  function toggleRecommendationDetails(songId: number) {
    setExpandedRecommendations((current) => ({
      ...current,
      [songId]: !current[songId],
    }));
  }

  function toggleFavoriteGenre(genreId: number) {
    setSelectedGenreIds((current) => {
      if (current.includes(genreId)) {
        return current.filter((id) => id !== genreId);
      }

      if (current.length >= 5) {
        return current;
      }

      return [...current, genreId];
    });
  }

  function addFavoriteArtist(artist: PreferenceItem) {
    setSelectedArtists((current) => {
      if (current.some((item) => item.id === artist.id)) {
        return current;
      }

      if (current.length >= 5) {
        return current;
      }

      return [...current, artist];
    });
  }

  function removeFavoriteArtist(artistId: number) {
    setSelectedArtists((current) =>
      current.filter((artist) => artist.id !== artistId),
    );
  }

  function openTasteProfile() {
    setSelectedGenreIds(savedFavoriteGenres.map((genreItem) => genreItem.id));

    setSelectedArtists(savedFavoriteArtists);

    setArtistSearchInput("");
    setArtistSearchResults([]);
    setPreferencesError("");
    setPreferencesOpen(true);
  }

  function cancelTasteProfile() {
    setSelectedGenreIds(savedFavoriteGenres.map((genreItem) => genreItem.id));

    setSelectedArtists(savedFavoriteArtists);

    setArtistSearchInput("");
    setArtistSearchResults([]);
    setPreferencesError("");
    setPreferencesOpen(false);
  }

  async function saveTasteProfile() {
    if (!token) {
      return;
    }

    if (selectedGenreIds.length === 0 && selectedArtists.length === 0) {
      setPreferencesError("Choose at least one favorite genre or artist.");

      return;
    }

    try {
      setPreferencesSaving(true);
      setPreferencesError("");

      const response = await fetch("http://localhost:5001/api/preferences", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          genreIds: selectedGenreIds,
          artistIds: selectedArtists.map((artist) => artist.id),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error ?? "Failed to save music preferences");
      }

      const preferencesData = data as PreferencesResponse;

      setSavedFavoriteGenres(preferencesData.genres);
      setSavedFavoriteArtists(preferencesData.artists);

      setSelectedGenreIds(
        preferencesData.genres.map((genreItem) => genreItem.id),
      );

      setSelectedArtists(preferencesData.artists);

      setArtistSearchInput("");
      setArtistSearchResults([]);

      setPreferencesOpen(false);

      if (meaningfulRatingCount > 0) {
        await fetchRecommendations();
      }
    } catch (err) {
      if (err instanceof Error) {
        setPreferencesError(err.message);
      } else {
        setPreferencesError("Failed to save music preferences");
      }
    } finally {
      setPreferencesSaving(false);
    }
  }

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

    setPreferencesLoaded(false);
    setPreferencesOpen(false);

    setSavedFavoriteGenres([]);
    setSavedFavoriteArtists([]);

    setSelectedGenreIds([]);
    setSelectedArtists([]);

    setAvailableGenres([]);

    setArtistSearchInput("");
    setArtistSearchResults([]);

    setPreferencesError("");
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
          <a
            className={
              activeSection === "home" ? "nav-item active" : "nav-item"
            }
            href="#home"
          >
            <span className="nav-icon">⌂</span>
            Home
          </a>

          {user && (
            <a
              className={
                activeSection === "recommendations"
                  ? "nav-item active"
                  : "nav-item"
              }
              href="#recommendations"
            >
              <span className="nav-icon">★</span>
              For You
            </a>
          )}

          <a
            className={
              activeSection === "browse" ? "nav-item active" : "nav-item"
            }
            href="#browse"
          >
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

              {preferencesLoaded && (
                <button
                  type="button"
                  className="sidebar-taste-button"
                  onClick={openTasteProfile}
                >
                  Edit Taste Profile
                </button>
              )}

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

        {user && preferencesLoaded && preferencesOpen && (
          <section className="onboarding-section">
            <div className="onboarding-card">
              <div className="onboarding-header">
                <div>
                  <p className="eyebrow">Personalize Your Experience</p>

                  <h2>Build Your Taste Profile</h2>

                  <p>
                    Choose some genres and artists you enjoy. These preferences
                    help MusicMatch personalize recommendations while it learns
                    from your ratings.
                  </p>
                </div>

                {savedFavoriteGenres.length > 0 ||
                savedFavoriteArtists.length > 0 ? (
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={cancelTasteProfile}
                  >
                    Cancel
                  </button>
                ) : null}
              </div>

              <div className="onboarding-block">
                <div className="onboarding-block-heading">
                  <div>
                    <h3>Favorite Genres</h3>

                    <p>Choose up to 5 genres.</p>
                  </div>

                  <span>{selectedGenreIds.length}/5</span>
                </div>

                <div className="preference-chip-grid">
                  {availableGenres.map((genreItem) => {
                    const selected = selectedGenreIds.includes(genreItem.id);

                    const disabled = !selected && selectedGenreIds.length >= 5;

                    return (
                      <button
                        key={genreItem.id}
                        type="button"
                        disabled={disabled}
                        className={
                          selected
                            ? "preference-chip selected"
                            : "preference-chip"
                        }
                        onClick={() => toggleFavoriteGenre(genreItem.id)}
                      >
                        {selected && (
                          <span className="preference-check">✓</span>
                        )}

                        {genreItem.name}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="onboarding-block">
                <div className="onboarding-block-heading">
                  <div>
                    <h3>Favorite Artists</h3>

                    <p>Search for artists and choose up to 5.</p>
                  </div>

                  <span>{selectedArtists.length}/5</span>
                </div>

                {selectedArtists.length > 0 && (
                  <div className="selected-artists">
                    {selectedArtists.map((artist) => (
                      <button
                        key={artist.id}
                        type="button"
                        className="selected-artist-chip"
                        onClick={() => removeFavoriteArtist(artist.id)}
                        title={`Remove ${artist.name}`}
                      >
                        <span>{artist.name}</span>
                        <span aria-hidden="true">×</span>
                      </button>
                    ))}
                  </div>
                )}

                <div className="artist-search">
                  <input
                    type="text"
                    placeholder="Search artists..."
                    value={artistSearchInput}
                    onChange={(event) =>
                      setArtistSearchInput(event.target.value)
                    }
                  />

                  {artistSearchInput.trim().length > 0 &&
                    artistSearchInput.trim().length < 2 && (
                      <p className="artist-search-hint">
                        Type at least 2 characters.
                      </p>
                    )}

                  {artistSearchLoading && (
                    <p className="artist-search-hint">Searching artists...</p>
                  )}

                  {!artistSearchLoading &&
                    artistSearchInput.trim().length >= 2 &&
                    artistSearchResults.length === 0 && (
                      <p className="artist-search-hint">No artists found.</p>
                    )}

                  {artistSearchResults.length > 0 && (
                    <div className="artist-search-results">
                      {artistSearchResults.map((artist) => {
                        const selected = selectedArtists.some(
                          (item) => item.id === artist.id,
                        );

                        const disabled =
                          !selected && selectedArtists.length >= 5;

                        return (
                          <button
                            key={artist.id}
                            type="button"
                            disabled={disabled}
                            className={
                              selected
                                ? "artist-result selected"
                                : "artist-result"
                            }
                            onClick={() =>
                              selected
                                ? removeFavoriteArtist(artist.id)
                                : addFavoriteArtist(artist)
                            }
                          >
                            <span>{artist.name}</span>

                            <span>{selected ? "Selected" : "+"}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {preferencesError && (
                <p className="error-message">{preferencesError}</p>
              )}

              <div className="onboarding-actions">
                <div>
                  <strong>
                    {selectedGenreIds.length + selectedArtists.length} selected
                  </strong>

                  <span>
                    Your ratings will still become more important as MusicMatch
                    learns your taste.
                  </span>
                </div>

                <button
                  type="button"
                  className="primary-button"
                  disabled={preferencesSaving}
                  onClick={saveTasteProfile}
                >
                  {preferencesSaving ? "Saving..." : "Save Taste Profile"}
                </button>
              </div>
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

                  {meaningfulRatingCount === 0 ? (
                    <>
                      <h3>
                        {savedFavoriteGenres.length > 0 ||
                        savedFavoriteArtists.length > 0
                          ? "Your taste profile is ready"
                          : "Start by building your taste profile"}
                      </h3>

                      <p>
                        {savedFavoriteGenres.length > 0 ||
                        savedFavoriteArtists.length > 0
                          ? "Now rate a few songs above or below 3 stars so MusicMatch can combine your favorite genres and artists with your listening preferences."
                          : "Choose some favorite genres or artists above, then rate a few songs so MusicMatch can start learning what you like."}
                      </p>

                      <p className="empty-state-hint">
                        Ratings of 3/5 are treated as neutral and do not
                        strongly affect your recommendations.
                      </p>
                    </>
                  ) : meaningfulRatingCount < 3 ? (
                    <>
                      <h3>Rate a few more songs</h3>

                      <p>
                        You have {meaningfulRatingCount} meaningful{" "}
                        {meaningfulRatingCount === 1 ? "rating" : "ratings"} so
                        far. A few more ratings will help produce stronger
                        recommendations.
                      </p>
                    </>
                  ) : (
                    <>
                      <h3>No recommendations found</h3>

                      <p>
                        The engine has enough rating information, but it did not
                        find any recommendation candidates right now.
                      </p>
                    </>
                  )}
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

                    <div className="recommendation-details-wrapper">
                      <button
                        type="button"
                        className="recommendation-details-toggle"
                        onClick={() => toggleRecommendationDetails(song.id)}
                      >
                        <span>Why this recommendation</span>

                        <span
                          className={
                            expandedRecommendations[song.id]
                              ? "details-chevron expanded"
                              : "details-chevron"
                          }
                        >
                          ▾
                        </span>
                      </button>

                      {expandedRecommendations[song.id] && (
                        <div className="recommendation-details">
                          <div className="recommendation-detail-row">
                            <span>Audio similarity</span>

                            <strong>
                              {(song.positive_similarity * 100).toFixed(0)}%
                            </strong>
                          </div>

                          <div className="recommendation-detail-bar">
                            <div
                              className="recommendation-detail-fill"
                              style={{
                                width: `${Math.min(
                                  Math.max(song.positive_similarity * 100, 0),
                                  100,
                                )}%`,
                              }}
                            />
                          </div>

                          <div className="recommendation-detail-row">
                            <span>Genre preference</span>

                            <strong>
                              {(song.genre_score * 100).toFixed(0)}%
                            </strong>
                          </div>

                          <div className="recommendation-detail-bar">
                            <div
                              className="recommendation-detail-fill"
                              style={{
                                width: `${Math.min(
                                  Math.max(song.genre_score * 100, 0),
                                  100,
                                )}%`,
                              }}
                            />
                          </div>

                          <div className="recommendation-detail-row">
                            <span>Popularity</span>

                            <strong>
                              {(song.popularity * 100).toFixed(0)}%
                            </strong>
                          </div>

                          <div className="recommendation-detail-bar">
                            <div
                              className="recommendation-detail-fill"
                              style={{
                                width: `${Math.min(
                                  Math.max(song.popularity * 100, 0),
                                  100,
                                )}%`,
                              }}
                            />
                          </div>

                          <div className="recommendation-detail-row">
                            <span>Similarity to disliked songs</span>

                            <strong>
                              {(song.negative_similarity * 100).toFixed(0)}%
                            </strong>
                          </div>

                          <div className="recommendation-detail-bar negative">
                            <div
                              className="recommendation-detail-fill negative"
                              style={{
                                width: `${Math.min(
                                  Math.max(song.negative_similarity * 100, 0),
                                  100,
                                )}%`,
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </div>

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
