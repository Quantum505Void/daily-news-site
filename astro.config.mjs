import { defineConfig } from "astro/config";

export default defineConfig({
  output: "static",
  site: "https://Quantum505Void.github.io",
  base: "/daily-news-site",
  build: {
    assets: "_assets",
  },
});
