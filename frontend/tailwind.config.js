/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#1e3a5f',
        accent:  '#e63946',
        surface: '#0f172a',
        card:    '#1e293b',
        border:  '#334155',
      },
    },
  },
  plugins: [],
}
