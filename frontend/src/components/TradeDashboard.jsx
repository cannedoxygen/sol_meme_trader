import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

// Import any other components you might need
// import { RiskAssessment } from './RiskAssessment';
// import { SentimentWidget } from './SentimentWidget';

const TradeDashboard = ({ tokens, activeToken, onTokenSelect, walletBalance }) => {
  const [glitchActive, setGlitchActive] = useState(false);
  const [priceChange, setPriceChange] = useState(0);
  
  // Trigger glitch effect when price changes significantly
  useEffect(() => {
    if (activeToken && activeToken.priceChange24h) {
      setPriceChange(activeToken.priceChange24h);
      
      if (Math.abs(activeToken.priceChange24h) > 5) {
        setGlitchActive(true);
        setTimeout(() => setGlitchActive(false), 1500);
      }
    }
  }, [activeToken]);

  return (
    <div className="relative w-full rounded-lg overflow-hidden">
      {/* CRT Scanline Overlay */}
      <div className="absolute inset-0 pointer-events-none z-10 opacity-20 bg-scanline animate-scanline"></div>
      
      {/* Main Dashboard Container with CRT Glow Effect */}
      <div className="bg-black/80 border-2 border-purple-500/50 p-6 rounded-lg shadow-[0_0_15px_rgba(157,23,248,0.4)] backdrop-blur-sm">
        <header className="flex justify-between items-center mb-6">
          <div className={`text-3xl font-vcr tracking-widest ${glitchActive ? 'animate-glitch' : ''}`}>
            <span className="text-cyan-400">RETRO</span>
            <span className="text-pink-500">TRADE</span>
          </div>
          
          <div className="px-4 py-2 bg-gradient-to-r from-purple-900/40 to-pink-900/40 rounded border border-purple-500/50">
            <div className="text-sm text-green-400 font-vcr">WALLET BALANCE</div>
            <div className="text-xl text-green-300 font-vcr">{walletBalance} SOL</div>
          </div>
        </header>
        
        {/* Token Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {tokens && tokens.slice(0, 4).map((token, index) => (
            <motion.div 
              key={token.address || index}
              className={`p-4 rounded cursor-pointer transition-all ${
                activeToken && activeToken.address === token.address 
                  ? 'bg-gradient-to-r from-purple-900/60 to-indigo-900/60 border-2 border-cyan-500' 
                  : 'bg-black/40 border border-purple-500/30 hover:border-pink-500/50'
              }`}
              onClick={() => onTokenSelect(token)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="flex justify-between">
                <div className="font-vcr text-xl text-cyan-300">{token.symbol}</div>
                <div className={`font-vcr ${
                  (token.priceChange24h || 0) >= 0 
                    ? 'text-green-400' 
                    : 'text-red-400'
                }`}>
                  {(token.priceChange24h || 0) >= 0 ? '▲' : '▼'} 
                  {Math.abs(token.priceChange24h || 0).toFixed(2)}%
                </div>
              </div>
              
              <div className="mt-1 text-sm text-gray-400 truncate">{token.name}</div>
              
              <div className="mt-2 font-mono text-xl text-white">
                ${Number(token.priceUSD || 0).toFixed(8)}
              </div>
              
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                <div className="bg-black/60 p-2 rounded">
                  <div className="text-gray-400">Volume 24h</div>
                  <div className="text-white">${Number(token.v24hUSD || 0).toLocaleString()}</div>
                </div>
                <div className="bg-black/60 p-2 rounded">
                  <div className="text-gray-400">Liquidity</div>
                  <div className="text-white">${Number(token.liquidity || 0).toLocaleString()}</div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
        
        {/* Active Token Details */}
        {activeToken && (
          <div className="relative mt-8 border-2 border-purple-500/30 rounded-lg p-6 bg-gradient-to-b from-black/60 to-purple-900/20">
            {/* "Monitor" frame effect */}
            <div className="absolute inset-0 border-t-8 border-l-4 border-r-4 border-b-8 border-gray-800 rounded-lg pointer-events-none"></div>
            
            <h2 className={`text-2xl font-vcr mb-4 ${glitchActive ? 'animate-glitch' : ''}`}>
              <span className="text-pink-500">{activeToken.name}</span> 
              <span className="text-cyan-400 ml-2">({activeToken.symbol})</span>
            </h2>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Price Display */}
              <div className="bg-black/40 p-4 rounded-lg border border-purple-500/30">
                <div className="text-gray-400 mb-2 font-vcr">CURRENT PRICE</div>
                <div className={`text-3xl font-mono ${glitchActive ? 'animate-glitch' : ''}`}>
                  ${Number(activeToken.priceUSD || 0).toFixed(8)}
                </div>
                <div className={`mt-2 ${
                  priceChange >= 0 
                    ? 'text-green-400' 
                    : 'text-red-400'
                } font-vcr`}>
                  {priceChange >= 0 ? '▲' : '▼'} {Math.abs(priceChange).toFixed(2)}%
                </div>
              </div>
              
              {/* Trade Controls */}
              <div className="bg-black/40 p-4 rounded-lg border border-purple-500/30">
                <div className="text-gray-400 mb-2 font-vcr">TRADE</div>
                <div className="flex gap-2 mb-3">
                  <input 
                    type="number" 
                    placeholder="Amount (SOL)"
                    className="bg-black/60 border border-purple-500/50 rounded px-3 py-2 text-white w-full focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button className="bg-gradient-to-r from-green-600 to-green-800 text-white py-2 px-4 rounded font-vcr hover:from-green-500 hover:to-green-700 transition-all">
                    BUY
                  </button>
                  <button className="bg-gradient-to-r from-red-600 to-red-800 text-white py-2 px-4 rounded font-vcr hover:from-red-500 hover:to-red-700 transition-all">
                    SELL
                  </button>
                </div>
              </div>
              
              {/* AI Assessment */}
              <div className="bg-black/40 p-4 rounded-lg border border-purple-500/30">
                <div className="text-gray-400 mb-2 font-vcr">AI ASSESSMENT</div>
                <div className="flex items-center">
                  <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse mr-2"></div>
                  <div className="text-green-300 font-vcr">BUY</div>
                </div>
                <div className="mt-2 text-sm text-white">
                  Confidence: <span className="text-cyan-400 font-bold">8.2/10</span>
                </div>
                <div className="mt-2 text-sm text-white">
                  Risk: <span className="text-pink-400 font-bold">3.5/10</span>
                </div>
              </div>
            </div>
            
            {/* Risk & Sentiment Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
              <div className="bg-black/40 p-4 rounded-lg border border-purple-500/30">
                <div className="text-gray-400 mb-2 font-vcr">RISK FACTORS</div>
                {/* Risk Assessment Component would go here */}
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <div className="text-white">Liquidity</div>
                    <div className="text-green-400">LOW RISK</div>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div className="bg-green-500 h-2 rounded-full" style={{ width: '25%' }}></div>
                  </div>
                  
                  <div className="flex justify-between">
                    <div className="text-white">Holder Concentration</div>
                    <div className="text-yellow-400">MODERATE</div>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '50%' }}></div>
                  </div>
                  
                  <div className="flex justify-between">
                    <div className="text-white">Smart Contract</div>
                    <div className="text-green-400">VERIFIED</div>
                  </div>
                </div>
              </div>
              
              <div className="bg-black/40 p-4 rounded-lg border border-purple-500/30">
                <div className="text-gray-400 mb-2 font-vcr">SOCIAL SENTIMENT</div>
                {/* Sentiment Widget Component would go here */}
                <div className="flex items-center justify-center space-x-2 mb-4">
                  <div className="text-2xl">🔥</div>
                  <div className="text-xl text-pink-400 font-vcr">BULLISH</div>
                  <div className="text-2xl">🔥</div>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="bg-black/60 p-2 rounded">
                    <span className="text-cyan-400">@trader1:</span> This token is going to moon! 🚀
                  </div>
                  <div className="bg-black/60 p-2 rounded">
                    <span className="text-cyan-400">@cryptofan:</span> Just loaded up my bags 💰
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TradeDashboard;

// CSS to add to your stylesheet or tailwind config
// @keyframes scanline {
//   0% { background-position: 0 0; }
//   100% { background-position: 0 100%; }
// }
// 
// @keyframes glitch {
//   0% { transform: translate(0); }
//   20% { transform: translate(-5px, 5px); }
//   40% { transform: translate(-5px, -5px); }
//   60% { transform: translate(5px, 5px); }
//   80% { transform: translate(5px, -5px); }
//   100% { transform: translate(0); }
// }
// 
// .animate-scanline {
//   animation: scanline 2s linear infinite;
//   background-image: linear-gradient(transparent 50%, rgba(0, 0, 0, 0.25) 50%);
//   background-size: 100% 4px;
// }
// 
// .animate-glitch {
//   animation: glitch 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94) both infinite;
//   text-shadow: 0 0 8px rgba(0, 255, 255, 0.6), 0 0 12px rgba(255, 0, 255, 0.6);
// }
// 
// .font-vcr {
//   font-family: 'VCR OSD Mono', monospace;
// }