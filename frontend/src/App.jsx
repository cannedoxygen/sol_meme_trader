import React, { useState, useEffect } from 'react';
import { Routes, Route, useLocation, Link } from 'react-router-dom';
import { motion } from 'framer-motion';

// Import pages
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';

// Custom cursor effect for retro feel
const CursorEffect = () => {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [visible, setVisible] = useState(false);
  const [clicked, setClicked] = useState(false);

  useEffect(() => {
    const updatePosition = (e) => {
      setPosition({ x: e.clientX, y: e.clientY });
      setVisible(true);
    };

    const handleMouseDown = () => setClicked(true);
    const handleMouseUp = () => setClicked(false);
    const handleMouseLeave = () => setVisible(false);
    const handleMouseEnter = () => setVisible(true);

    window.addEventListener('mousemove', updatePosition);
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('mouseenter', handleMouseEnter);

    return () => {
      window.removeEventListener('mousemove', updatePosition);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('mouseenter', handleMouseEnter);
    };
  }, []);

  if (!visible) return null;

  return (
    <>
      {/* Outer glow */}
      <div 
        className="fixed pointer-events-none z-50 rounded-full mix-blend-screen"
        style={{
          left: position.x - 20,
          top: position.y - 20,
          width: clicked ? '30px' : '40px',
          height: clicked ? '30px' : '40px',
          backgroundColor: 'transparent',
          boxShadow: `0 0 ${clicked ? '10px' : '20px'} rgba(138, 43, 226, 0.5)`,
          transition: 'width 0.1s, height 0.1s, box-shadow 0.1s',
          opacity: 0.8
        }}
      />
      {/* Inner cursor */}
      <div 
        className="fixed pointer-events-none z-50 rounded-full"
        style={{
          left: position.x - 4,
          top: position.y - 4,
          width: '8px',
          height: '8px',
          backgroundColor: clicked ? '#fe53bb' : '#08f7fe',
          transition: 'background-color 0.1s'
        }}
      />
    </>
  );
};

// Loading screen with retro look
const LoadingScreen = () => (
  <div className="fixed inset-0 bg-black z-50 flex flex-col items-center justify-center">
    <div className="text-5xl font-vcr text-cyan-400 mb-8 animate-glitch">LOADING...</div>
    <div className="w-64 h-4 bg-black/60 border border-purple-500/50 rounded overflow-hidden">
      <div className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500 animate-load-progress"></div>
    </div>
    
    <div className="mt-12 font-mono text-green-400 max-w-md text-center">
      <div className="terminal-text">INITIALIZING SYSTEM...</div>
    </div>
    
    {/* CRT Scanline effect */}
    <div className="absolute inset-0 pointer-events-none z-10 opacity-20 bg-scanline animate-scanline"></div>
    <div className="absolute inset-0 pointer-events-none z-10 opacity-10 crt-overlay"></div>
  </div>
);

// 404 page with retro aesthetic
const NotFound = () => (
  <div className="min-h-screen bg-black/90 flex flex-col items-center justify-center relative">
    {/* Retro grid background */}
    <div className="absolute inset-0 z-0 bg-grid-pattern opacity-20"></div>
    
    {/* CRT Scanline Overlay */}
    <div className="absolute inset-0 pointer-events-none z-10 opacity-20 bg-scanline animate-scanline"></div>
    
    <div className="text-8xl font-vcr text-pink-500 animate-glitch mb-8">404</div>
    <div className="text-2xl font-vcr text-cyan-400 mb-12">FILE_NOT_FOUND.EXE</div>
    
    <div className="font-mono text-green-400 max-w-md text-center mb-12">
      > ERROR: The requested file cannot be located.<br />
      > SYSTEM: Please check your coordinates and try again.<br />
      > STATUS: Return to main directory advised.
    </div>
    
    <Link 
      to="/" 
      className="px-8 py-3 bg-gradient-to-r from-purple-700 to-pink-600 font-vcr text-white rounded shadow-synthwave hover:from-purple-600 hover:to-pink-500 transition-all duration-300"
    >
      RETURN HOME
    </Link>
    
    {/* Bottom retro sun/horizon effect */}
    <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-purple-900/30 to-transparent z-0"></div>
    <div className="absolute -bottom-20 left-1/2 transform -translate-x-1/2 w-full max-w-2xl h-40 rounded-full bg-gradient-to-t from-pink-600 to-purple-700 blur-3xl opacity-20 z-0"></div>
  </div>
);

const App = () => {
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [walletBalance, setWalletBalance] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [alerts, setAlerts] = useState([]);

  // Simulate initial loading
  useEffect(() => {
    setTimeout(() => {
      setLoading(false);
    }, 2000);
  }, []);
  
  // Page transition effect
  useEffect(() => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
    }, 800);
  }, [location.pathname]);

  // Wallet connection handler
  const handleConnectWallet = () => {
    setIsConnected(true);
    setWalletBalance(1.234);
    
    addAlert({
      id: Date.now(),
      type: 'success',
      title: 'WALLET CONNECTED',
      message: 'Successfully connected to wallet',
      details: 'Balance: 1.234 SOL',
      timestamp: new Date().toLocaleTimeString()
    });
  };

  // Add alert
  const addAlert = (alert) => {
    setAlerts(prev => [alert, ...prev].slice(0, 5));
  };

  // Dismiss alert
  const dismissAlert = (id) => {
    setAlerts(prev => prev.filter(alert => alert.id !== id));
  };

  return (
    <>
      {loading && <LoadingScreen />}
      
      <div className="min-h-screen bg-black/90 overflow-x-hidden">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </div>
      
      {/* Custom cursor */}
      <CursorEffect />
    </>
  );
};

export default App;