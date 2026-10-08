import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";
import App from "./App.tsx";

// Mount the React application into the root element provided by index.html.
createRoot(document.getElementById("root")!).render(
  // StrictMode helps catch common development issues such as unsafe
  // side effects and deprecated React behavior.
  <StrictMode>
    <App />
  </StrictMode>,
);
