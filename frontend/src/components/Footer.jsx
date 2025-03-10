import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const Footer = ({ systemStatus = "online", uptime = "24h 32m 18s", version = "1.0.3" }) => {
  const [scrollText, setScrollText] = useState("");
  const [marqueeIndex, setMarqueeIndex] = useState(0);
  
  // Example performance stats - in a real app these would come from props or context
  const stats = {
    tokens_analyzed: 582,
    trades_executed: 47,
    profitable_trades: 31,
    success_rate: "65.9%"
  };
  
  // Scrolling text messages for the ticker
  const marqueeTexts = [
    ">> TRADING AT YOUR OWN RISK // NOT FINANCIAL ADVICE // DYOR <<",
    ">> POWERED BY SOLANA // AI-DRIVEN ANALYSIS // REAL-TIME SENTIMENT <<",
    ">> AUTO-TRADING MODE REQUIRES CONFIGURATION // CHECK SETTINGS <<",
    ">> MONITORING 500+ TOKENS // UPDATED EVERY 60 SECONDS <<"
  ];
  
  // Rotate marquee text
  useEffect(() => {
    setScrollText(marqueeTexts[marqueeIndex]);
    
    const interval = setInterval(() => {
      setMarqueeIndex((prevIndex) => (prevIndex + 1) % marqueeTexts.length);
    }, 10000);
    
    return () => clearInterval(interval);
  }, [marqueeIndex]);
  
  useEffect(() => {
    setScrollText(marqueeTexts[marqueeIndex]);
  }, [marqueeIndex]);

  return (
    <footer className="bg-black/90 border-t-2 border-purple-500/50 text-gray-300 py-2 relative">
      {/* CRT Scanline Overlay */}
      <div className="absolute inset-0 pointer-events-none z-10 opacity-10 bg-scanline animate-scanline"></div>
      
      {/* Main Footer Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row justify-between">
          {/* Left Section - System Status */}
          <div className="flex items-center mb-2 md:mb-0">
            <div className="font-vcr text-xs text-gray-400 mr-3">SYSTEM:</div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center">
                <div className={`w-2 h-2 rounded-full ${systemStatus === "online" ? "bg-green-500 animate-pulse" : "bg-red-500"} mr-1`}></div>
                <span className="text-xs font-mono">{systemStatus.toUpperCase()}</span>
              </div>
              
              <div className="hidden sm:flex items-center">
                <div className="text-xs text-gray-400 mr-1">UPTIME:</div>
                <div className="text-xs font-mono text-cyan-400">{uptime}</div>
              </div>
              
              <div className="hidden sm:flex items-center">
                <div className="text-xs text-gray-400 mr-1">VERSION:</div>
                <div className="text-xs font-mono text-pink-400">{version}</div>
              </div>
            </div>
          </div>
          
          {/* Center - Scrolling Text */}
          <div className="overflow-hidden mb-2 md:mb-0 relative max-w-md mx-auto">
            <div className="marquee-container w-full overflow-hidden bg-black/60 border border-purple-500/30 rounded px-2 py-1">
              <div className="font-vcr text-xs text-green-400 whitespace-nowrap animate-scrolling">
                {scrollText}
              </div>
            </div>
          </div>
          
          {/* Right Section - Stats */}
          <div className="flex space-x-4 justify-center md:justify-end">
            <div className="hidden sm:block text-xs">
              <span className="text-gray-400 font-vcr">ANALYSIS:</span>
              <span className="ml-1 font-mono text-cyan-400">{stats.tokens_analyzed}</span>
            </div>
            
            <div className="text-xs">
              <span className="text-gray-400 font-vcr">TRADES:</span>
              <span className="ml-1 font-mono text-cyan-400">{stats.trades_executed}</span>
            </div>
            
            <div className="text-xs">
              <span className="text-gray-400 font-vcr">SUCCESS:</span>
              <span className="ml-1 font-mono text-green-400">{stats.success_rate}</span>
            </div>
          </div>
        </div>
        
        {/* Bottom Links */}
        <div className="mt-2 pt-2 border-t border-purple-900/50 flex justify-between items-center text-[10px] text-gray-500">
          <div>
            © {new Date().getFullYear()} MEMECOIN TRADER // AI-POWERED TRADING
          </div>
          
          <div className="flex space-x-4">
            <Link to="/terms" className="hover:text-pink-400 transition-colors">TERMS</Link>
            <Link to="/privacy" className="hover:text-pink-400 transition-colors">PRIVACY</Link>
            <Link to="/docs" className="hover:text-pink-400 transition-colors">DOCS</Link>
            <a href="https://github.com/yourusername/memecoin-trader" target="_blank" rel="noopener noreferrer" className="hover:text-pink-400 transition-colors">GITHUB</a>
          </div>
        </div>
      </div>
      
      {/* Bottom Border Glow */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500 to-transparent opacity-50"></div>
    </footer>
  );
};

export default Footer;

// Add these to your CSS/tailwind config:
// @keyframes scrolling {
//   0% { transform: translateX(100%); }
//   100% { transform: translateX(-100%); }
// }
//
// .animate-scrolling {
//   animation: scrolling 20s linear infinite;
// }