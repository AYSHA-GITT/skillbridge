module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ['Space Grotesk', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
      colors: {
        base: {
          950: '#060a12',
          900: '#0d1420',
          800: '#141b28',
          700: '#1b2333',
        },
        accent: {
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
        },
      },
      boxShadow: {
        glow: '0 0 40px -10px rgba(45, 212, 191, 0.35)',
      },
    },
  },
  plugins: [],
}