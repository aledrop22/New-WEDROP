/** @type {import('tailwindcss').Config} */
export default {
  // O modo escuro segue o tema escolhido no painel (classe "dark" no <html>), não o sistema operacional
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        wedrop: {
          primary: '#e02424',
          accent: '#ff4b4b',
          dark: '#1e293b',
          light: '#f8fafc',
        }
      }
    },
  },
  plugins: [],
}
