import app from "./app";

// Port used by the Express backend during local development.
const PORT = Number(process.env.PORT) || 5001;

// Start the HTTP server.
// The Express app itself is defined separately in app.ts so it can be
// imported by tests without automatically opening a network port.
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Server running on port ${PORT}`);
});
