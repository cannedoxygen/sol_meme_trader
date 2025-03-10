import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';

const Header = ({ walletBalance, isConnected, onConnectWallet }) => {
  const location = useLocation();
  const [glitchActive, setGlitchActive] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  
  // Trigger glitch effect occasionally
  useEffect(() => {
    const glitchInterval = setInterval(() => {
      setGlitchActive(true);
      setTimeout(() => setGlitchActive(false), 800);
    }, 15000);
    
    return () => clearInterval(glitchInterval);
  }, []);
  
  // Update time
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);
  
  // Format time in retro digital clock style
  const formattedTime = currentTime.toLocaleTimeString('en-US', { 
    hour12: false, 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  });
  
  // Navigation links
  const navLinks = [
    { path: '/', label: 'HOME' },
    { path: '/dashboard', label: 'DASHBOARD' },
    { path: '/settings', label: 'SETTINGS' }
  ];

  return (
    <header className="bg-black/90 border-b-2 border-purple-500/50 shadow-lg shadow-purple-500/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex-shrink-0 flex items-center">
            <Link to="/" className={`flex items-center ${glitchActive ? 'animate-glitch' : ''}`}>
              {/* Glitchy Logo */}
              <div className="relative mr-2">
                <div className="text-3xl font-vcr relative z-10">
                  <span className="text-cyan-400">MEME</span>
                  <span className="text-pink-500">COIN</span>
                </div>
                {glitchActive && (
                  <>
                    <div className="text-3xl font-vcr absolute top-0 left-0.5 text-red-500 opacity-70 z-0">
                      <span>MEME</span>
                      <span>COIN</span>
                    </div>
                    <div className="text-3xl font-vcr absolute top-0 -left-0.5 text-blue-500 opacity-70 z-0">
                      <span>MEME</span>
                      <span>COIN</span>
                    </div>
                  </>
                )}
              </div>
              <div className="text-sm text-gray-400 font-mono ml-1">v1.0</div>
            </Link>
          </div>
          
          {/* Navigation */}
          <nav className="hidden md:flex space-x-8">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`font-vcr px-3 py-1 text-sm transition-all duration-300 ${
                  location.pathname === link.path
                    ? 'text-cyan-400 border-b-2 border-cyan-400'
                    : 'text-gray-300 hover:text-pink-400'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          
          {/* Right side - Wallet & Time */}
          <div className="flex items-center space-x-4">
            {/* Current Time */}
            <div className="hidden md:flex px-3 py-1 bg-gradient-to-r from-purple-900/40 to-indigo-900/40 rounded border border-purple-500/30">
              <div className="font-mono text-green-400">{formattedTime}</div>
            </div>
            
            {/* Wallet Status */}
            <div className="relative">
              {isConnected ? (
                <div className="flex items-center px-3 py-1 bg-gradient-to-r from-purple-900/40 to-indigo-900/40 rounded border border-purple-500/30">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
                  <div className="font-vcr text-green-400">{walletBalance ? `${walletBalance} SOL` : 'CONNECTED'}</div>
                </div>
              ) : (
                <motion.button
                  onClick={onConnectWallet}
                  className="flex items-center px-4 py-1.5 bg-gradient-to-r from-purple-800 to-pink-700 hover:from-purple-700 hover:to-pink-600 rounded font-vcr text-white border border-purple-500"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  CONNECT WALLET
                </motion.button>
              )}
              
              {/* Scanline effect on button/wallet indicator */}
              <div className="absolute inset-0 pointer-events-none z-10 opacity-20 bg-scanline animate-scanline rounded"></div>
            </div>
            
            {/* Mobile menu button */}
            <div className="md:hidden">
              <button className="p-1 rounded-md text-gray-300 hover:text-white hover:bg-purple-800">
                <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" />
                </button>
              </div>
          </div>
        </div>
      </div>
      
      {/* Static noise overlay - subtle */}
      <div className="absolute inset-x-0 top-0 h-16 pointer-events-none opacity-5 z-50">
        <div className="w-full h-full bg-noise"></div>
      </div>
    </header>
  );
};

export default Header;

// Add these elements to your CSS/tailwind config:
// @keyframes noise {
//   0%, 100% { background-position: 0 0; }
//   10% { background-position: -5% -10%; }
//   20% { background-position: -15% 5%; }
//   30% { background-position: 7% -25%; }
//   40% { background-position: 20% 25%; }
//   50% { background-position: -25% 10%; }
//   60% { background-position: 15% 5%; }
//   70% { background-position: 0% 15%; }
//   80% { background-position: 25% 35%; }
//   90% { background-position: -10% 10%; }
// }
//
// .bg-noise {
//   background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='1'/%3E%3C/svg%3E");
//   background-repeat: repeat;
//   animation: noise 0.5s infinite;
// }