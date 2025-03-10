import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const SentimentWidget = ({ tokenData, sentiment }) => {
  // Default values if not provided by props
  const defaultSentiment = {
    sentiment_score: 0,
    sentiment_label: "neutral",
    confidence: 0.5,
    bullish_signals: [],
    bearish_signals: [],
    key_themes: [],
    engagement_level: "low",
    summary: "No sentiment data available."
  };

  const data = sentiment || defaultSentiment;
  
  // Calculate normalized sentiment score (0-100)
  const normalizedScore = Math.round((data.sentiment_score + 1) * 50);
  
  // State for glitch effect
  const [glitching, setGlitching] = useState(false);
  
  // Trigger glitch effect on score change
  useEffect(() => {
    setGlitching(true);
    const timer = setTimeout(() => setGlitching(false), 1000);
    return () => clearTimeout(timer);
  }, [data.sentiment_score]);

  // Color based on sentiment
  const getSentimentColor = () => {
    if (data.sentiment_label === "positive") return "text-green-400";
    if (data.sentiment_label === "negative") return "text-red-400";
    return "text-yellow-400";
  };

  // Emoji based on sentiment
  const getSentimentEmoji = () => {
    if (data.sentiment_label === "positive") return "🚀";
    if (data.sentiment_label === "negative") return "💥";
    return "⚖️";
  };

  return (
    <div className="bg-black/80 border-2 border-purple-500/50 rounded-lg overflow-hidden shadow-[0_0_15px_rgba(157,23,248,0.4)]">
      {/* Terminal Header */}
      <div className="bg-gradient-to-r from-purple-900 to-pink-900 px-4 py-2 flex justify-between items-center">
        <div className="font-vcr text-cyan-300 tracking-wider">SOCIAL_SENTIMENT.EXE</div>
        <div className="flex space-x-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
        </div>
      </div>
      
      {/* Terminal Body */}
      <div className="p-4 font-mono text-sm relative">
        {/* Scanline effect */}
        <div className="absolute inset-0 pointer-events-none z-10 opacity-20 bg-scanline animate-scanline"></div>
        
        {/* Main Content */}
        <div className="space-y-4">
          {/* Sentiment Score Meter */}
          <div className="mb-4">
            <div className="flex justify-between mb-1">
              <span className="text-gray-400">SENTIMENT_SCORE:</span>
              <span className={`${getSentimentColor()} ${glitching ? 'animate-glitch' : ''}`}>
                {normalizedScore}/100
              </span>
            </div>
            <div className="w-full bg-gray-800 h-4 rounded-sm overflow-hidden border border-purple-500/30">
              <motion.div 
                className={`h-full ${
                  data.sentiment_label === "positive" ? "bg-gradient-to-r from-green-600 to-green-400" :
                  data.sentiment_label === "negative" ? "bg-gradient-to-r from-red-600 to-red-400" :
                  "bg-gradient-to-r from-yellow-600 to-yellow-400"
                }`}
                initial={{ width: 0 }}
                animate={{ width: `${normalizedScore}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
              />
            </div>
          </div>
          
          {/* Sentiment Analysis */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left Column - Sentiment Overview */}
            <div className="space-y-3">
              <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
                <div className="text-gray-400">MARKET_MOOD:</div>
                <div className={`text-xl font-vcr ${getSentimentColor()} flex items-center space-x-2`}>
                  <span>{getSentimentEmoji()}</span>
                  <span className={glitching ? 'animate-glitch' : ''}>
                    {data.sentiment_label.toUpperCase()}
                  </span>
                  <span>{getSentimentEmoji()}</span>
                </div>
              </div>
              
              <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
                <div className="text-gray-400">ENGAGEMENT:</div>
                <div className="text-xl font-vcr text-cyan-400">
                  {data.engagement_level.toUpperCase()}
                </div>
              </div>
              
              <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
                <div className="text-gray-400">CONFIDENCE:</div>
                <div className="text-xl font-vcr text-pink-400">
                  {Math.round(data.confidence * 100)}%
                </div>
              </div>
            </div>
            
            {/* Right Column - Signals */}
            <div className="space-y-3">
              {/* Key Themes */}
              <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
                <div className="text-gray-400 mb-1">KEY_THEMES:</div>
                <div className="flex flex-wrap gap-2">
                  {data.key_themes.length > 0 ? (
                    data.key_themes.map((theme, index) => (
                      <span key={index} className="bg-purple-900/50 text-cyan-300 px-2 py-1 rounded text-xs">
                        #{theme}
                      </span>
                    ))
                  ) : (
                    <span className="text-gray-500 italic">No themes detected</span>
                  )}
                </div>
              </div>
              
              {/* Bullish Signals */}
              <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
                <div className="text-gray-400 mb-1">BULLISH_SIGNALS:</div>
                <div className="space-y-1 text-green-400 text-xs">
                  {data.bullish_signals.length > 0 ? (
                    data.bullish_signals.slice(0, 3).map((signal, index) => (
                      <div key={index} className="flex">
                        <span className="mr-1">+</span>
                        <span>{signal}</span>
                      </div>
                    ))
                  ) : (
                    <span className="text-gray-500 italic">No bullish signals detected</span>
                  )}
                </div>
              </div>
              
              {/* Bearish Signals */}
              <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
                <div className="text-gray-400 mb-1">BEARISH_SIGNALS:</div>
                <div className="space-y-1 text-red-400 text-xs">
                  {data.bearish_signals.length > 0 ? (
                    data.bearish_signals.slice(0, 3).map((signal, index) => (
                      <div key={index} className="flex">
                        <span className="mr-1">-</span>
                        <span>{signal}</span>
                      </div>
                    ))
                  ) : (
                    <span className="text-gray-500 italic">No bearish signals detected</span>
                  )}
                </div>
              </div>
            </div>
          </div>
          
          {/* Summary */}
          <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
            <div className="text-gray-400 mb-1">SUMMARY:</div>
            <div className="text-green-300 font-mono terminal-text">
              {data.summary}
            </div>
          </div>
          
          {/* Terminal Prompt */}
          <div className="flex items-center text-green-400">
            <span className="mr-2">$</span>
            <span className="animate-pulse">_</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SentimentWidget;

// Add these classes to your CSS or tailwind config:
// .terminal-text {
//   overflow: hidden;
//   border-right: 0.15em solid green;
//   white-space: nowrap;
//   letter-spacing: 0.05em;
//   animation: typing 3.5s steps(40, end), blink-caret 0.75s step-end infinite;
// }
// 
// @keyframes typing {
//   from { width: 0 }
//   to { width: 100% }
// }
// 
// @keyframes blink-caret {
//   from, to { border-color: transparent }
//   50% { border-color: rgba(16, 185, 129, 0.75) }
// }