/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {
        colors: {
          // Retro synthwave custom color palette
          synthwave: {
            100: '#f0b3ff', // Light pink
            200: '#d580ff', // Lighter purple
            300: '#b84dff', // Medium purple
            400: '#9932cc', // Dark orchid
            500: '#8a2be2', // Blueviolet
            600: '#800080', // Purple
            700: '#660066', // Dark purple
            800: '#4b0082', // Indigo
            900: '#330033'  // Deep purple
          },
    plugins: [
      // Add custom plugin for CRT screen effects
      function({ addUtilities }) {
        const newUtilities = {
          '.crt': {
            '&::before': {
              content: '""',
              display: 'block',
              position: 'absolute',
              top: '0',
              left: '0',
              bottom: '0',
              right: '0',
              background: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))',
              'z-index': '2',
              'background-size': '100% 2px, 3px 100%',
              'pointer-events': 'none',
              opacity: '0.15'
            }
          },
          '.glitch-text': {
            'position': 'relative',
            '&::before, &::after': {
              content: 'attr(data-text)',
              position: 'absolute',
              top: '0',
              left: '0',
              width: '100%',
              height: '100%'
            },
            '&::before': {
              left: '2px',
              text: 'blue',
              clip: 'rect(44px, 450px, 56px, 0)'
            },
            '&::after': {
              left: '-2px',
              text: 'red',
              clip: 'rect(44px, 450px, 46px, 0)'
            },
            'animation': 'glitch-text 1s ease-in-out infinite'
          },
          '.text-glow-cyan': {
            'text-shadow': '0 0 5px rgba(6, 182, 212, 0.7), 0 0 10px rgba(6, 182, 212, 0.5)'
          },
          '.text-glow-pink': {
            'text-shadow': '0 0 5px rgba(219, 39, 119, 0.7), 0 0 10px rgba(219, 39, 119, 0.5)'
          },
          '.text-glow-purple': {
            'text-shadow': '0 0 5px rgba(147, 51, 234, 0.7), 0 0 10px rgba(147, 51, 234, 0.5)'
          }
        }
        addUtilities(newUtilities, ['responsive', 'hover'])
      }
    ],
          // Neon accents
          neon: {
            cyan: '#08f7fe',   // Bright cyan
            pink: '#fe53bb',   // Hot pink
            purple: '#7b25fb', // Electric purple
            blue: '#3677ff',   // Electric blue
            green: '#00ff9f',  // Neon green
            yellow: '#ffff00', // Bright yellow
            orange: '#ff9900', // Neon orange
            red: '#ff0000'     // Neon red
          },
          // Base colors extension
          black: {
            DEFAULT: '#000000',
            light: '#121212',
            pure: '#000000'
          },
        },
        fontFamily: {
          // Font families
          mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
          vcr: ['VCR OSD Mono', 'monospace']
        },
        backgroundImage: {
          'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
          'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
          'grid-pattern': 'linear-gradient(rgba(128, 90, 213, 0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(128, 90, 213, 0.2) 1px, transparent 1px)',
          'scanline': 'linear-gradient(transparent 50%, rgba(0, 0, 0, 0.25) 50%)',
          'noise': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='1'/%3E%3C/svg%3E\")",
          'synthwave-grid': 'linear-gradient(to bottom, #2c1654 0%, transparent 40%), radial-gradient(ellipse at bottom, #5d278b 0%, transparent 80%), linear-gradient(rgba(128, 90, 213, 0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(128, 90, 213, 0.2) 1px, transparent 1px)',
          'crt-overlay': 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))'
        },
        keyframes: {
          glitch: {
            '0%': { transform: 'translate(0)' },
            '20%': { transform: 'translate(-5px, 5px)' },
            '40%': { transform: 'translate(-5px, -5px)' },
            '60%': { transform: 'translate(5px, 5px)' },
            '80%': { transform: 'translate(5px, -5px)' },
            '100%': { transform: 'translate(0)' }
          },
          'glitch-overlay': {
            '0%, 100%': { opacity: 0 },
            '20%, 80%': { opacity: 0.03 },
            '50%': { opacity: 0.10 }
          },
          'glitch-text': {
            '0%': { transform: 'translate(0)' },
            '20%': { transform: 'translate(-2px, 1px)' },
            '40%': { transform: 'translate(-1px, -1px)', filter: 'hue-rotate(90deg)' },
            '60%': { transform: 'translate(1px, 1px)' },
            '80%': { transform: 'translate(1px, -1px)', filter: 'hue-rotate(-90deg)' },
            '100%': { transform: 'translate(0)' }
          },
          scanline: {
            '0%': { backgroundPosition: '0 0' },
            '100%': { backgroundPosition: '0 100%' }
          },
          typing: {
            'from': { width: '0' },
            'to': { width: '100%' }
          },
          'blink-caret': {
            'from, to': { borderColor: 'transparent' },
            '50%': { borderColor: 'rgba(16, 185, 129, 0.75)' }
          },
          shrink: {
            'from': { width: '100%' },
            'to': { width: '0%' }
          },
          'load-progress': {
            '0%': { backgroundPosition: '0% 0' },
            '50%': { backgroundPosition: '100% 0' },
            '100%': { backgroundPosition: '0% 0' }
          },
          'terminal-blink': {
            '0%, 100%': { opacity: 1 },
            '50%': { opacity: 0.7 }
          },
          noise: {
            '0%, 100%': { backgroundPosition: '0 0' },
            '10%': { backgroundPosition: '-5% -10%' },
            '20%': { backgroundPosition: '-15% 5%' },
            '30%': { backgroundPosition: '7% -25%' },
            '40%': { backgroundPosition: '20% 25%' },
            '50%': { backgroundPosition: '-25% 10%' },
            '60%': { backgroundPosition: '15% 5%' },
            '70%': { backgroundPosition: '0% 15%' },
            '80%': { backgroundPosition: '25% 35%' },
            '90%': { backgroundPosition: '-10% 10%' }
          },
          scrolling: {
            '0%': { transform: 'translateX(100%)' },
            '100%': { transform: 'translateX(-100%)' }
          },
          'star-animation-sm': {
            '0%': { transform: 'translateY(0px)' },
            '50%': { transform: 'translateY(-1px)' },
            '100%': { transform: 'translateY(0px)' }
          },
          'star-animation-md': {
            '0%': { transform: 'translateY(0px)' },
            '50%': { transform: 'translateY(-2px)' },
            '100%': { transform: 'translateY(0px)' }
          },
          'star-animation-lg': {
            '0%': { transform: 'translateY(0px)' },
            '50%': { transform: 'translateY(-3px)' },
            '100%': { transform: 'translateY(0px)' }
          }
        },
        animation: {
          'glitch': 'glitch 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94) both infinite',
          'glitch-overlay': 'glitch-overlay 1s ease-in-out infinite',
          'glitch-text': 'glitch-text 1s ease-in-out infinite',
          'scanline': 'scanline 8s linear infinite',
          'typing': 'typing 3.5s steps(40, end), blink-caret 0.75s step-end infinite',
          'shrink': 'shrink 10s linear forwards',
          'load-progress': 'load-progress 2.5s linear infinite',
          'terminal-blink': 'terminal-blink 1s step-end infinite',
          'noise': 'noise 0.5s infinite',
          'scrolling': 'scrolling 20s linear infinite',
          'star-sm': 'star-animation-sm 3s ease-in-out infinite',
          'star-md': 'star-animation-md 5s ease-in-out infinite',
          'star-lg': 'star-animation-lg 7s ease-in-out infinite',
          'pulse-glow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
        },
        boxShadow: {
          // Neon glow shadows
          'neon-cyan': '0 0 5px rgba(8, 247, 254, 0.5), 0 0 20px rgba(8, 247, 254, 0.3)',
          'neon-pink': '0 0 5px rgba(254, 83, 187, 0.5), 0 0 20px rgba(254, 83, 187, 0.3)',
          'neon-purple': '0 0 5px rgba(123, 37, 251, 0.5), 0 0 20px rgba(123, 37, 251, 0.3)',
          'neon-green': '0 0 5px rgba(0, 255, 159, 0.5), 0 0 20px rgba(0, 255, 159, 0.3)',
          'synthwave': '0 0 10px rgba(139, 92, 246, 0.5), 0 0 30px rgba(139, 92, 246, 0.3)',
          'crt': 'inset 0 0 30px rgba(0, 0, 0, 0.5)',
          'screen': 'inset 0 0 10px rgba(139, 92, 246, 0.3), 0 0 20px rgba(139, 92, 246, 0.3)',
          'button-glow': '0 0 5px theme("colors.purple.500"), 0 0 20px theme("colors.purple.500")',
          'text-glow': '0 0 2px currentColor'