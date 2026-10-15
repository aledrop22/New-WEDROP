/** @type {import('tailwindcss').Config} */
export default {
  // O modo escuro segue o tema escolhido no painel (classe "dark" no <html>), não o sistema operacional
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  // As classes de tema são montadas em tempo de execução (theme-${id}); sem isso o Tailwind
  // apaga as regras CSS delas e todos os temas caem no tema claro padrão.
  safelist: [
    'theme-light-wedrop',
    'theme-light-emerald',
    'theme-light-amber',
    'theme-dark-onyx',
    'theme-dark-black',
    'theme-dark-midnight',
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
