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

  return (
    <main>
      <h1>Music Recommendation Engine</h1>

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
