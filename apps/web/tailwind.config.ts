import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        slatebase: "#10192A",
        seafoam: "#7FE7C4",
        amberline: "#FFB454"
      }
    }
  },
  plugins: [],
};

export default config;
