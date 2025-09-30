/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mia: {
          red: '#D00603',
          pink: '#F189CB',
          green: '#82EBA1',
          yellow: '#C9F84A',
          cyan: '#3CDDF9',
          purple: '#9A3698',
          'deep-purple': '#2A3698',
        },
        neutral: {
          black: '#000000',
          white: '#FFFFFF',
          grey: '#E8E8E8',
          'dark-grey': '#666666',
          'light-grey': '#F5F5F5',
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      animation: {
        'gradient': 'gradient 8s ease infinite',
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
      },
      keyframes: {
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        }
      }
    },
  },
  plugins: [],
}