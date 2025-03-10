import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const Home = () => {
  const [glitchActive, setGlitchActive] = useState(false);
  
  // Create periodic glitch effect
  useEffect(() => {
    const glitchInterval = setInterval(() => {
      setGlitchActive(true);
      setTimeout(() => setGlitchActive(false), 1000);
    }, 8000);
    
    return () => clearInterval(glitchInterval);
  }, []);
  
  return (
    <div className="min-h-screen bg-black relative overflow-hidden">
      {/* Retro grid background */}
      <div className="absolute inset-0 z-0 bg-grid-pattern opacity-40"></div>
      
      {/* Scanline overlay */}
      <div className="absolute inset-0 pointer-events-none z-10 opacity-20 bg-scanline animate-scanline"></div>
      
      {/* Stars background */}
      <div className="absolute inset-0 z-0">
        <div className="stars-sm"></div>
        <div className="stars-md"></div>
        <div className="stars-lg"></div>
      </div>
      
      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24">
        <div className="text-center">
          {/* Hero Title with Glitch Effect */}
          <motion.div
            initial={{ y: -50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="relative inline-block mb-6"
          >
            <h1 className={`text-5xl md:text-7xl font-vcr tracking-tight ${glitchActive ? 'animate-glitch' : ''}`}>
              <span className="text-cyan-400">MEME</span>
              <span className="text-purple-400">COIN</span>
              <span className="text-pink-500">TRADER</span>
            </h1>
            
            {glitchActive && (
              <>
                <div className="absolute inset-0 text-5xl md:text-7xl font-vcr tracking-tight text-red-500 opacity-70 left-0.5 top-0.5 z-0">
                  <span>MEME</span>
                  <span>COIN</span>
                  <span>TRADER</span>
                </div>
                <div className="absolute inset-0 text-5xl md:text-7xl font-vcr tracking-tight text-blue-500 opacity-70 -left-0.5 -top-0.5 z-0">
                  <span>MEME</span>
                  <span>COIN</span>
                  <span>TRADER</span>
                </div>
              </>
            )}
          </motion.div>
          
          {/* Subtitle */}
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="max-w-xl mx-auto text-lg text-gray-300 font-mono"
          >
            A.I. powered trading system for Solana meme coins
          </motion.p>
          
          {/* CRT-style decorative line */}
          <motion.div 
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="w-full max-w-lg mx-auto h-px bg-gradient-to-r from-transparent via-purple-500 to-transparent my-8"
          ></motion.div>
          
          {/* Feature boxes */}
          <motion.div 
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.7 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12"
          >
            {/* AI Analysis */}
            <div className="bg-black/80 border border-purple-500/40 rounded-lg p-6 backdrop-blur-sm shadow-lg hover:shadow-purple-500/20 transition-all">
              <div className="text-cyan-400 text-3xl mb-4">🧠</div>
              <h3 className="text-xl font-vcr text-pink-400 mb-2">AI ANALYSIS</h3>
              <p className="text-sm text-gray-300">Advanced GPT analysis of token fundamentals, risk, and potential</p>
            </div>
            
            {/* Sentiment Tracking */}
            <div className="bg-black/80 border border-purple-500/40 rounded-lg p-6 backdrop-blur-sm shadow-lg hover:shadow-purple-500/20 transition-all">
              <div className="text-cyan-400 text-3xl mb-4">📊</div>
              <h3 className="text-xl font-vcr text-pink-400 mb-2">SENTIMENT</h3>
              <p className="text-sm text-gray-300">Real-time social media sentiment tracking to spot early opportunities</p>
            </div>
            
            {/* Automated Trading */}
            <div className="bg-black/80 border border-purple-500/40 rounded-lg p-6 backdrop-blur-sm shadow-lg hover:shadow-purple-500/20 transition-all">
              <div className="text-cyan-400 text-3xl mb-4">🤖</div>
              <h3 className="text-xl font-vcr text-pink-400 mb-2">AUTO-TRADE</h3>
              <p className="text-sm text-gray-300">Set up automated trading with customizable risk parameters</p>
            </div>
          </motion.div>
          
          {/* CTA Section */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 1 }}
            className="mt-16"
          >
            <div className="inline-block relative group">
              <Link
                to="/dashboard"
                className="bg-gradient-to-r from-purple-700 to-pink-600 hover:from-purple-600 hover:to-pink-500 text-white font-vcr py-3 px-8 rounded-md shadow-lg hover:shadow-purple-500/50 transition-all text-lg"
              >
                LAUNCH DASHBOARD
              </Link>
              
              {/* Button glow effect */}
              <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg blur opacity-30 group-hover:opacity-70 transition duration-1000 group-hover:duration-200 animate-pulse"></div>
            </div>
            
            <div className="mt-10 text-xs text-gray-500 font-mono">
              *CONNECT YOUR WALLET TO ACCESS ALL FEATURES
            </div>
          </motion.div>
          
          {/* Stats Section */}
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8, delay: 1.2 }}
            className="mt-20 pt-10 border-t border-purple-900/30"
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-2xl text-cyan-400 font-vcr">500+</div>
                <div className="text-xs text-gray-400">TOKENS MONITORED</div>
              </div>
              <div className="text-center">
                <div className="text-2xl text-cyan-400 font-vcr">24/7</div>
                <div className="text-xs text-gray-400">MARKET ANALYSIS</div>
              </div>
              <div className="text-center">
                <div className="text-2xl text-cyan-400 font-vcr">3.2M+</div>
                <div className="text-xs text-gray-400">TRADES EXECUTED</div>
              </div>
              <div className="text-center">
                <div className="text-2xl text-cyan-400 font-vcr">65%</div>
                <div className="text-xs text-gray-400">AVERAGE SUCCESS RATE</div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
      
      {/* Bottom retro sun/horizon effect */}
      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-purple-900/30 to-transparent z-0"></div>
      <div className="absolute -bottom-20 left-1/2 transform -translate-x-1/2 w-full max-w-2xl h-40 rounded-full bg-gradient-to-t from-pink-600 to-purple-700 blur-3xl opacity-20 z-0"></div>
    </div>
  );
};

export default Home;

// Add these to your CSS/tailwind config:
// .bg-grid-pattern {
//   background-image: linear-gradient(rgba(128, 90, 213, 0.2) 1px, transparent 1px), 
//                     linear-gradient(90deg, rgba(128, 90, 213, 0.2) 1px, transparent 1px);
//   background-size: 40px 40px;
//   background-position: center center;
// }
//
// @keyframes star-animation-sm {
//   0% { transform: translateY(0px); }
//   50% { transform: translateY(-1px); }
//   100% { transform: translateY(0px); }
// }
//
// @keyframes star-animation-md {
//   0% { transform: translateY(0px); }
//   50% { transform: translateY(-2px); }
//   100% { transform: translateY(0px); }
// }
//
// @keyframes star-animation-lg {
//   0% { transform: translateY(0px); }
//   50% { transform: translateY(-3px); }
//   100% { transform: translateY(0px); }
// }
//
// .stars-sm {
//   position: absolute;
//   width: 1px;
//   height: 1px;
//   background: white;
//   box-shadow: 50px 30px 1px white, 100px 80px 1px white, 150px 50px 1px white, 
//               200px 100px 1px white, 250px 50px 1px white, 300px 200px 1px white,
//               /* Add more stars as needed */;
//   animation: star-animation-sm 3s ease-in-out infinite;
// }
//
// .stars-md {
//   position: absolute;
//   width: 2px;
//   height: 2px;
//   background: white;
//   box-shadow: 75px 100px 1px white, 125px 300px 1px white, 175px 150px 1px white, 
//               225px 200px 1px white, 275px 350px 1px white, 325px 275px 1px white,
//               /* Add more stars as needed */;
//   animation: star-animation-md 5s ease-in-out infinite;
// }
//
// .stars-lg {
//   position: absolute;
//   width: 3px;
//   height: 3px;
//   background: white;
//   box-shadow: 125px 150px 1.5px white, 175px 350px 1.5px white, 225px 200px 1.5px white, 
//               275px 250px 1.5px white, 325px 400px 1.5px white, 375px 300px 1.5px white,
//               /* Add more stars as needed */;
//   animation: star-animation-lg 7s ease-in-out infinite;
// }