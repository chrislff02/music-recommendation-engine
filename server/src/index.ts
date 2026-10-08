import app from "./app";

// Port used by the Express backend during local development.
const PORT = 5001;

// Start the HTTP server.
// The Express app itself is defined separately in app.ts so it can be
// imported by tests without automatically opening a network port.
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
