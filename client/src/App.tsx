import { useEffect, useState } from "react";

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
      } catch {
        sessionStorage.removeItem("token");
        setToken("");
        setUser(null);
      }
    }

    fetchCurrentUser();
  }, [token]);

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
      return;
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
    } catch (err) {
      if (err instanceof Error) {
        setRatingError(err.message);
      } else {
        setRatingError("Failed to save rating");
      }
    }
  }

  function handleLogout() {
    sessionStorage.removeItem("token");
    setToken("");
    setUser(null);
    setRatings({});
  }

  return (
    <main>
      <h1>Music Recommendation Engine</h1>

      <section>
        {user ? (
          <>
            <p>
              Logged in as <strong>{user.username}</strong>
            </p>

            <button onClick={handleLogout}>Log Out</button>
          </>
        ) : (
          <>
            <h2>{authMode === "login" ? "Log In" : "Register"}</h2>

            <form onSubmit={handleAuth}>
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

              <button type="submit">
                {authMode === "login" ? "Log In" : "Register"}
              </button>
            </form>

            {authError && <p>{authError}</p>}

            <button
              type="button"
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
          </>
        )}
      </section>

      <hr />

      <h2>Browse Songs</h2>

      <form onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="Search songs or artists..."
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
        />

        <button type="submit">Search</button>
      </form>

      <div>
        <label htmlFor="genre">Genre: </label>

        <select id="genre" value={genre} onChange={handleGenreChange}>
          {GENRES.map((genreOption) => (
            <option key={genreOption || "all"} value={genreOption}>
              {genreOption || "All Genres"}
            </option>
          ))}
        </select>

        <button type="button" onClick={handleClearFilters}>
          Clear Filters
        </button>
      </div>

      {loading && <p>Loading songs...</p>}

      {error && <p>{error}</p>}

      {ratingError && <p>{ratingError}</p>}

      {!loading && !error && songs.length === 0 && <p>No songs found.</p>}

      {!loading && !error && songs.length > 0 && (
        <>
          <div>
            {songs.map((song) => (
              <div key={song.id}>
                <h3>{song.title}</h3>

                <p>Artist: {song.artist}</p>

                <p>Genre: {song.genre ?? "Unknown"}</p>

                <p>
                  Duration: {Math.floor(song.duration / 60)}:
                  {String(song.duration % 60).padStart(2, "0")}
                </p>

                {user ? (
                  <div>
                    <p>
                      Your rating:{" "}
                      {ratings[song.id] ? `${ratings[song.id]}/5` : "Not rated"}
                    </p>

                    <div>
                      {[1, 2, 3, 4, 5].map((value) => (
                        <button
                          key={value}
                          type="button"
                          onClick={() => handleRateSong(song.id, value)}
                        >
                          {value}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p>Log in to rate this song.</p>
                )}

                <hr />
              </div>
            ))}
          </div>

          <div>
            <button
              onClick={() => setPage((current) => current - 1)}
              disabled={page === 1}
            >
              Previous
            </button>

            <span>
              {" "}
              Page {page} of {totalPages}{" "}
            </span>

            <button
              onClick={() => setPage((current) => current + 1)}
              disabled={page === totalPages}
            >
              Next
            </button>
          </div>
        </>
      )}
    </main>
  );
}

export default App;
