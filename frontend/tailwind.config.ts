import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        navy: "#172a4e",
        brand: "#2878f0",
        mist: "#f4f7fb",
      },
    },
  },
  plugins: [],
};

export default config;
