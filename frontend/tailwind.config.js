/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        crimson: {
          DEFAULT: "#7A0019",
          deep: "#4A000F",
          bright: "#990033",
        },
        cream: "#F4EFE6",
        parchment: "#E8DFD0",
        ink: "#1C1410",
        gold: "#C4A35A",
      },
      fontFamily: {
        display: ['"Fraunces"', "Georgia", "serif"],
        sans: ['"Figtree"', "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        card: "0 18px 40px -24px rgba(74, 0, 15, 0.45)",
      },
    },
  },
  plugins: [],
};
