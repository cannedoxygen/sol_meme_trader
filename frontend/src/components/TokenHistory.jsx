import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const TradeHistory = ({ trades = [] }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // 'all', 'buy', 'sell'
  const [filteredTrades, setFilteredTrades] = useState([]);
  const [isGlitching, setIsGlitching] = useState(false);
  
  // Generate sample trades if none provided
  useEffect(() => {
    // If we have trades provided, use those
    if (trades && trades.length > 0) {
      setFilteredTrades(filterTradesByType(trades, filter));
      setIsLoading(false);
      return;
    }
    
    // Simulate loading delay
    const timer = setTimeout(() => {
      // Generate sample trades if none provided
      const sampleTrades = generateSampleTrades();
      setFilteredTrades(filterTradesByType(sampleTrades, filter));
      setIsLoading(false);
    }, 1200);
    
    return () => clearTimeout(timer);
  }, [trades]);
  
  // Update filtered trades when filter changes
  useEffect(() => {
    if (trades.length > 0) {
      setFilteredTrades(filterTradesByType(trades, filter));
    } else {
      const sampleTrades = generateSampleTrades();
      setFilteredTrades(filterTradesByType(sampleTrades, filter));
    }
    
    // Trigger glitch effect on filter change
    setIsGlitching(true);
    setTimeout(() => setIsGlitching(false), 800);
  }, [filter]);
  
  // Filter trades by type
  const filterTradesByType = (tradeList, filterType) => {
    if (filterType === 'all') return tradeList;
    return tradeList.filter(trade => trade.type.toLowerCase() === filterType);
  };
  
  // Generate random sample trades for demo
  const generateSampleTrades = () => {
    const sampleTokens = [
      { symbol: 'RMOON', name: 'RetroMoon', price: 0.0000152 },
      { symbol: 'VAPOR', name: 'WaveVapor', price: 0.00000789 },
      { symbol: 'PXLP', name: 'PixelPunk', price: 0.0000935 },
      { symbol: 'SYNTH', name: 'SynthSol', price: 0.000127 }
    ];
    
    const sampleTrades = [];
    
    // Generate 10 random trades
    for (let i = 0; i < 10; i++) {
      const randomToken = sampleTokens[Math.floor(Math.random() * sampleTokens.length)];
      const isSuccessful = Math.random() > 0.2;
      const tradeType = Math.random() > 0.5 ? 'BUY' : 'SELL';
      const tradeAmount = (0.05 + Math.random() * 0.45).toFixed(3);
      const date = new Date();
      date.setHours(date.getHours() - Math.floor(Math.random() * 48));
      
      sampleTrades.push({
        id: `trade-${i}`,
        type: tradeType,
        tokenSymbol: randomToken.symbol,
        tokenName: randomToken.name,
        amount: tradeType === 'BUY' ? `${tradeAmount} SOL` : `${Math.floor(tradeAmount * 1000000)} ${randomToken.symbol}`,
        price: randomToken.price,
        value: tradeType === 'BUY' ? tradeAmount : (randomToken.price * Math.floor(tradeAmount * 1000000)),
        timestamp: date.toISOString(),
        status: isSuccessful ? 'SUCCESS' : 'FAILED',
        txHash: `${Math.random().toString(36).substring(2, 10)}...${Math.random().toString(36).substring(2, 6)}`
      });
    }
    
    // Sort by timestamp, newest first
    return sampleTrades.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  };
  
  // Format timestamp
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString(undefined, {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  };
  
  // Get status icon and color
  const getStatusInfo = (status) => {
    switch (status) {
      case 'SUCCESS':
        return { icon: '✓', color: 'text-green-400' };
      case 'FAILED':
        return { icon: '✗', color: 'text-red-400' };
      case 'PENDING':
        return { icon: '⧖', color: 'text-yellow-400' };
      default:
        return { icon: '?', color: 'text-gray-400' };
    }
  };
  
  // Get type color
  const getTypeColor = (type) => {
    switch (type.toUpperCase()) {
      case 'BUY':
        return 'text-green-400';
      case 'SELL':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className="bg-black/80 border-2 border-purple-500/50 rounded-lg overflow-hidden shadow-lg shadow-purple-500/20 backdrop-blur-sm relative">
      {/* CRT Scanline Overlay */}
      <div className="absolute inset-0 pointer-events-none z-10 opacity-10 bg-scanline animate-scanline"></div>
      
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-900 to-indigo-900 px-4 py-2 flex justify-between items-center">
        <div className="font-vcr text-cyan-300 tracking-wider">TRADE_HISTORY.LOG</div>
        
        {/* Filter controls */}
        <div className="flex space-x-2">
          <button 
            onClick={() => setFilter('all')}
            className={`px-2 py-0.5 text-xs font-vcr ${
              filter === 'all' 
                ? 'bg-purple-700/60 text-cyan-400 border border-cyan-500/50' 
                : 'text-gray-400 hover:text-pink-400'
            }`}
          >
            ALL
          </button>
          <button 
            onClick={() => setFilter('buy')}
            className={`px-2 py-0.5 text-xs font-vcr ${
              filter === 'buy' 
                ? 'bg-green-900/60 text-green-400 border border-green-500/50' 
                : 'text-gray-400 hover:text-green-400'
            }`}
          >
            BUY
          </button>
          <button 
            onClick={() => setFilter('sell')}
            className={`px-2 py-0.5 text-xs font-vcr ${
              filter === 'sell' 
                ? 'bg-red-900/60 text-red-400 border border-red-500/50' 
                : 'text-gray-400 hover:text-red-400'
            }`}
          >
            SELL
          </button>
        </div>
      </div>
      
      {/* Trade list */}
      <div className="p-4">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-64">
            <div className="text-xl font-vcr text-cyan-400 mb-4 animate-pulse">LOADING TRADE DATA...</div>
            <div className="w-48 h-2 bg-black/60 border border-purple-500/50 rounded overflow-hidden">
              <div className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500 animate-load-progress"></div>
            </div>
          </div>
        ) : filteredTrades.length === 0 ? (
          <div className="text-center py-8">
            <div className={`text-xl font-vcr text-pink-400 mb-2 ${isGlitching ? 'animate-glitch' : ''}`}>NO TRADE DATA</div>
            <div className="text-sm font-mono text-gray-400">No trade history found for the selected filter.</div>
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto pr-1 terminal-history">
            {filteredTrades.map((trade, index) => {
              const statusInfo = getStatusInfo(trade.status);
              
              return (
                <motion.div
                  key={trade.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  className="bg-black/60 border border-purple-500/30 p-3 rounded"
                >
                  <div className="flex justify-between items-start">
                    {/* Left: Token & Type */}
                    <div>
                      <div className="flex items-center">
                        <span className={`font-vcr ${getTypeColor(trade.type)}`}>{trade.type}</span>
                        <span className="mx-2 text-gray-500">|</span>
                        <span className="text-cyan-400 font-vcr">{trade.tokenSymbol}</span>
                      </div>
                      <div className="text-xs text-gray-400 mt-1">{trade.tokenName}</div>
                    </div>
                    
                    {/* Right: Status & Time */}
                    <div className="text-right">
                      <div className={`flex items-center justify-end ${statusInfo.color}`}>
                        <span className="mr-1">{trade.status}</span>
                        <span>{statusInfo.icon}</span>
                      </div>
                      <div className="text-xs text-gray-400 mt-1">{formatTimestamp(trade.timestamp)}</div>
                    </div>
                  </div>
                  
                  {/* Details */}
                  <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                    <div>
                      <div className="text-gray-500">Amount</div>
                      <div className="text-white">{trade.amount}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Price</div>
                      <div className="text-white">${trade.price.toFixed(8)}</div>
                    </div>
                  </div>
                  
                  {/* TX Hash */}
                  <div className="mt-2 pt-2 border-t border-purple-900/30 flex justify-between items-center text-xs">
                    <span className="text-gray-500">TX:</span>
                    <span className="font-mono text-pink-400">{trade.txHash}</span>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
        
        {/* Stats */}
        {!isLoading && filteredTrades.length > 0 && (
          <div className="mt-4 text-xs font-mono text-gray-400 flex justify-between border-t border-purple-900/30 pt-3">
            <div>Total trades: <span className="text-cyan-400">{filteredTrades.length}</span></div>
            <div>
              Success rate: <span className="text-cyan-400">
                {((filteredTrades.filter(t => t.status === 'SUCCESS').length / filteredTrades.length) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}
        
        {/* Terminal Line */}
        <div className="mt-3 flex items-center text-green-400 font-mono text-xs">
          <span className="mr-2">$</span>
          <span className="animate-pulse">_</span>
        </div>
      </div>
    </div>
  );
};

export default TradeHistory;