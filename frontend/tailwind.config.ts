import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        navy: "#172a4e",
        // Named `brand`, not `blue`: assigning a bare string to `blue` replaces Tailwind's
        // whole blue scale, which silently voids every bg-blue-600 / text-blue-700 / ring-blue-200
        // utility used across the UI.
        brand: "#2878f0",
        mist: "#f4f7fb",
      },
    },
  },
  plugins: [],
};

export default config;
