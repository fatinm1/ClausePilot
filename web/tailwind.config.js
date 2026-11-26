/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#000000',
          raised: '#0a0a0a',
          panel: '#121212',
          well: '#181818',
        },
        fg: {
          DEFAULT: '#ffffff',
          2: '#a6a6a6',
          3: '#7a7a7a',
        },
        line: {
          DEFAULT: 'rgba(255,255,255,0.12)',
          strong: 'rgba(255,255,255,0.35)',
        },
        metal: {
          peak: '#ffffff',
          bright: '#f6f7f9',
          mid: '#cbced2',
          shade: '#a9acb1',
          floor: '#8e9196',
        },
        redline: {
          DEFAULT: '#b04545',
          text: '#e58a8a',
          wash: 'rgba(176,69,69,0.14)',
        },
        ok: {
          DEFAULT: '#7fb39a',
          wash: 'rgba(127,179,154,0.12)',
        },
        warn: '#d9b56f',
      },
      fontFamily: {
        display: ['"Libre Caslon Display"', 'Georgia', 'serif'],
        sans: ['"Inter Variable"', 'Inter', 'system-ui', 'sans-serif'],
      },
      maxWidth: {
        content: '1600px',
      },
      transitionTimingFunction: {
        standard: 'cubic-bezier(.4,0,.2,1)',
        out: 'cubic-bezier(.16,1,.3,1)',
      },
    },
  },
  plugins: [],
}
