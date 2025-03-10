import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const PortfolioView = ({ portfolio = null, walletAddress = null }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [portfolioData, setPortfolioData] = useState(null);
  const [sortBy, setSortBy] = useState('value'); // 'value', 'profit', 'name'
  const [sortDirection, setSortDirection] = useState('desc'); // 'asc', 'desc'
  const [glitchActive, setGlitchActive] = useState(false);
  const [selectedToken, setSelectedToken] = useState(null);
  
  // Generate synthetic portfolio data if none provided
  useEffect(() => {
    // If we have portfolio data provided, use it
    if (portfolio) {
      setPortfolioData(portfolio);
      setIsLoading(false);
      return;
    }
    
    // Simulate loading delay
    setIsLoading(true);
    
    setTimeout(() => {
      const syntheticPortfolio = generateSyntheticPortfolio();
      setPortfolioData(syntheticPortfolio);
      setIsLoading(false);
    }, 1500);
  }, [portfolio]);
  
  // Sort portfolio holdings when sort parameters change
  useEffect(() => {
    if (!portfolioData) return;
    
    const sortedPortfolio = { ...portfolioData };
    
    sortedPortfolio.holdings = [...portfolioData.holdings].sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'value':
          comparison = a.currentValue - b.currentValue;
          break;
        case 'profit':
          comparison = (a.currentValue - a.initialValue) - (b.currentValue - b.initialValue);
          break;
        case 'name':
          comparison = a.tokenSymbol.localeCompare(b.tokenSymbol);
          break;
        default:
          comparison = a.currentValue - b.currentValue;
      }
      
      return sortDirection === 'asc' ? comparison : -comparison;
    });
    
    setPortfolioData(sortedPortfolio);
    
    // Trigger glitch effect
    setGlitchActive(true);
    setTimeout(() => setGlitchActive(false), 800);
  }, [sortBy, sortDirection]);
  
  // Generate synthetic portfolio data for demo purposes
  const generateSyntheticPortfolio = () => {
    // Sample tokens with fictional data
    const tokenHoldings = [
      {
        tokenId: '1',
        tokenSymbol: 'RMOON',
        tokenName: 'RetroMoon',
        amount: 1250000,
        initialValue: 0.12,
        currentValue: 0.18,
        price: 0.0000015,
        priceChange24h: 12.5,
        color: '#14F195' // green
      },
      {
        tokenId: '2',
        tokenSymbol: 'VAPOR',
        tokenName: 'WaveVapor',
        amount: 3500000,
        initialValue: 0.25,
        currentValue: 0.22,
        price: 0.00000078,
        priceChange24h: -3.7,
        color: '#FE53BB' // pink
      },
      {
        tokenId: '3',
        tokenSymbol: 'PXLP',
        tokenName: 'PixelPunk',
        amount: 420000,
        initialValue: 0.35,
        currentValue: 0.45,
        price: 0.0000095,
        priceChange24h: 26.8,
        color: '#9945FF' // purple
      },
      {
        tokenId: '4',
        tokenSymbol: 'SYNTH',
        tokenName: 'SynthSol',
        amount: 180000,
        initialValue: 0.08,
        currentValue: 0.15,
        price: 0.00001270,
        priceChange24h: 4.2,
        color: '#00C2FF' // blue
      },
      {
        tokenId: '5',
        tokenSymbol: 'GLCH',
        tokenName: 'GlitchToken',
        amount: 550000,
        initialValue: 0.09,
        currentValue: 0.05,
        price: 0.00000840,
        priceChange24h: -8.3,
        color: '#F5D300' // yellow
      }
    ];
    
    // Calculate total values
    const totalValue = tokenHoldings.reduce((sum, token) => sum + token.currentValue, 0);
    const totalInitialValue = tokenHoldings.reduce((sum, token) => sum + token.initialValue, 0);
    const totalProfit = totalValue - totalInitialValue;
    const totalProfitPercent = totalInitialValue > 0 
      ? ((totalValue - totalInitialValue) / totalInitialValue) * 100 
      : 0;
    
    return {
      totalValue,
      totalInitialValue,
      totalProfit,
      totalProfitPercent,
      holdings: tokenHoldings,
      lastUpdated: new Date().toISOString()
    };
  };
  
  // Toggle sort direction
  const toggleSort = (column) => {
    if (sortBy === column) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // Set new column and default to descending
      setSortBy(column);
      setSortDirection('desc');
    }
  };
  
  // Get profit/loss color based on value
  const getProfitLossColor = (value) => {
    if (value > 0) return 'text-green-400';
    if (value < 0) return 'text-red-400';
    return 'text-gray-400';
  };
  
  // Get sorting indicator
  const getSortIndicator = (column) => {
    if (sortBy !== column) return null;
    return sortDirection === 'asc' ? '▲' : '▼';
  };
  
  // Format percentage with sign
  const formatPercent = (value) => {
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };
  
  // Custom pie chart tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      
      return (
        <div className="bg-black/90 border border-purple-500/50 p-2 text-xs font-mono">
          <p className="text-cyan-400">{data.tokenName} ({data.tokenSymbol})</p>
          <p className="text-pink-400">Value: ${data.currentValue.toFixed(2)}</p>
          <p className={getProfitLossColor(data.currentValue - data.initialValue)}>
            Profit: ${(data.currentValue - data.initialValue).toFixed(2)} 
            ({((data.currentValue - data.initialValue) / data.initialValue * 100).toFixed(2)}%)
          </p>
        </div>
      );
    }
    
    return null;
  };
  
  // Format timestamp
  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch (error) {
      return 'Unknown';
    }
  };
  
  // Handle token selection
  const handleTokenSelect = (token) => {
    setSelectedToken(token === selectedToken ? null : token);
  };

  return (
    <div className="bg-black/80 border-2 border-purple-500/50 rounded-lg overflow-hidden shadow-lg shadow-purple-500/20 backdrop-blur-sm relative">
      {/* CRT Scanline Overlay */}
      <div className="absolute inset-0 pointer-events-none z-10 opacity-10 bg-scanline animate-scanline"></div>
      
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-900 to-indigo-900 px-4 py-2 flex justify-between items-center">
        <div className={`font-vcr text-cyan-300 tracking-wider ${glitchActive ? 'animate-glitch' : ''}`}>
          PORTFOLIO.DAT
        </div>
        
        {walletAddress && (
          <div className="flex items-center text-xs font-mono text-gray-300">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></span>
            <span>{walletAddress.substring(0, 6)}...{walletAddress.substring(walletAddress.length - 4)}</span>
          </div>
        )}
      </div>
      
      {/* Content */}
      <div className="p-4">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-64">
            <div className="text-xl font-vcr text-cyan-400 mb-4 animate-pulse">LOADING PORTFOLIO...</div>
            <div className="w-48 h-2 bg-black/60 border border-purple-500/50 rounded overflow-hidden">
              <div className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500 animate-load-progress"></div>
            </div>
          </div>
        ) : !portfolioData || portfolioData.holdings.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-xl font-vcr text-pink-400 mb-2">EMPTY PORTFOLIO</div>
            <div className="text-sm font-mono text-gray-400 mb-6">
              No tokens found in your portfolio.
            </div>
            <button className="px-4 py-2 bg-gradient-to-r from-purple-700 to-pink-600 text-white font-vcr rounded">
              ADD TOKENS
            </button>
          </div>
        ) : (
          <div>
            {/* Portfolio Summary */}
            <div className="mb-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left: Summary Stats */}
                <div className="space-y-3">
                  <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
                    <div className="text-gray-400 text-xs font-vcr mb-1">TOTAL VALUE</div>
                    <div className="text-2xl font-vcr text-cyan-400">${portfolioData.totalValue.toFixed(2)}</div>
                  </div>
                  
                  <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
                    <div className="text-gray-400 text-xs font-vcr mb-1">TOTAL PROFIT/LOSS</div>
                    <div className={`text-xl font-vcr flex items-center ${getProfitLossColor(portfolioData.totalProfit)}`}>
                      <span>
                        ${portfolioData.totalProfit > 0 ? '+' : ''}{portfolioData.totalProfit.toFixed(2)}
                      </span>
                      <span className="text-sm ml-2">
                        ({formatPercent(portfolioData.totalProfitPercent)})
                      </span>
                    </div>
                  </div>
                  
                  <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
                    <div className="text-gray-400 text-xs font-vcr mb-1">TOKENS HELD</div>
                    <div className="text-xl font-vcr text-pink-400">
                      {portfolioData.holdings.length}
                    </div>
                  </div>
                </div>
                
                {/* Right: Pie Chart */}
                <div className="bg-black/60 border border-purple-500/30 p-3 rounded h-64 flex flex-col">
                  <div className="text-gray-400 text-xs font-vcr mb-1">ALLOCATION</div>
                  <div className="flex-1">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={portfolioData.holdings}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={2}
                          dataKey="currentValue"
                          nameKey="tokenSymbol"
                          label={({ tokenSymbol }) => tokenSymbol}
                          labelLine={false}
                        >
                          {portfolioData.holdings.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
              
              <div className="text-xs text-gray-400 mt-2 text-right">
                Last updated: {formatTimestamp(portfolioData.lastUpdated)}
              </div>
            </div>
            
            {/* Holdings Table */}
            <div className="mt-6">
              <div className="text-sm font-vcr text-cyan-400 mb-2">TOKEN HOLDINGS</div>
              
              {/* Table Header */}
              <div className="bg-black/60 border border-purple-500/30 p-2 rounded-t grid grid-cols-6 text-xs font-vcr text-gray-400">
                <div 
                  className="cursor-pointer hover:text-pink-400 transition-colors"
                  onClick={() => toggleSort('name')}
                >
                  TOKEN {getSortIndicator('name')}
                </div>
                <div className="text-right">AMOUNT</div>
                <div className="text-right">PRICE</div>
                <div 
                  className="text-right cursor-pointer hover:text-pink-400 transition-colors"
                  onClick={() => toggleSort('value')}
                >
                  VALUE {getSortIndicator('value')}
                </div>
                <div className="text-right">24H</div>
                <div 
                  className="text-right cursor-pointer hover:text-pink-400 transition-colors"
                  onClick={() => toggleSort('profit')}
                >
                  PROFIT/LOSS {getSortIndicator('profit')}
                </div>
              </div>
              
              {/* Table Body */}
              <div className="space-y-1 max-h-64 overflow-y-auto pr-1 terminal-history">
                {portfolioData.holdings.map((token, index) => {
                  const profit = token.currentValue - token.initialValue;
                  const profitPercent = token.initialValue > 0 
                    ? (profit / token.initialValue) * 100
                    : 0;
                  
                  return (
                    <motion.div
                      key={token.tokenId}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                      className={`grid grid-cols-6 p-2 text-xs ${
                        selectedToken === token 
                          ? 'bg-purple-900/30 border border-purple-500/50 rounded'
                          : 'bg-black/40 hover:bg-black/60 border border-purple-900/30 rounded'
                      } cursor-pointer`}
                      onClick={() => handleTokenSelect(token)}
                    >
                      <div className="flex items-center">
                        <div 
                          className="w-3 h-3 rounded-full mr-2"
                          style={{ backgroundColor: token.color }}
                        ></div>
                        <div>
                          <div className="font-vcr text-cyan-400">{token.tokenSymbol}</div>
                          <div className="text-[10px] text-gray-500">{token.tokenName}</div>
                        </div>
                      </div>
                      
                      <div className="text-right text-gray-300">
                        {token.amount.toLocaleString()}
                      </div>
                      
                      <div className="text-right text-gray-300">
                        ${token.price.toFixed(8)}
                      </div>
                      
                      <div className="text-right text-pink-400">
                        ${token.currentValue.toFixed(2)}
                      </div>
                      
                      <div className={`text-right ${token.priceChange24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {token.priceChange24h > 0 ? '+' : ''}{token.priceChange24h.toFixed(2)}%
                      </div>
                      
                      <div className={`text-right ${getProfitLossColor(profit)}`}>
                        ${profit > 0 ? '+' : ''}{profit.toFixed(2)} ({formatPercent(profitPercent)})
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
            
            {/* Selected Token Details */}
            {selectedToken && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 bg-black/60 border border-purple-500/30 p-3 rounded"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-vcr text-lg text-cyan-400">{selectedToken.tokenName} ({selectedToken.tokenSymbol})</div>
                    <div className="text-xs text-gray-400 mt-1">Token ID: {selectedToken.tokenId}</div>
                  </div>
                  
                  <div className="flex space-x-2">
                    <button className="px-3 py-1 bg-gradient-to-r from-green-700 to-green-900 text-white text-xs font-vcr rounded">
                      BUY MORE
                    </button>
                    <button className="px-3 py-1 bg-gradient-to-r from-red-700 to-red-900 text-white text-xs font-vcr rounded">
                      SELL
                    </button>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                  <div className="bg-black/40 p-2 rounded">
                    <div className="text-gray-400 text-[10px]">AMOUNT</div>
                    <div className="text-white">{selectedToken.amount.toLocaleString()}</div>
                  </div>
                  <div className="bg-black/40 p-2 rounded">
                    <div className="text-gray-400 text-[10px]">PRICE</div>
                    <div className="text-white">${selectedToken.price.toFixed(8)}</div>
                  </div>
                  <div className="bg-black/40 p-2 rounded">
                    <div className="text-gray-400 text-[10px]">24H CHANGE</div>
                    <div className={selectedToken.priceChange24h >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {selectedToken.priceChange24h > 0 ? '+' : ''}{selectedToken.priceChange24h.toFixed(2)}%
                    </div>
                  </div>
                  <div className="bg-black/40 p-2 rounded">
                    <div className="text-gray-400 text-[10px]">PROFIT/LOSS</div>
                    <div className={getProfitLossColor(selectedToken.currentValue - selectedToken.initialValue)}>
                      ${(selectedToken.currentValue - selectedToken.initialValue).toFixed(2)}
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
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

export default PortfolioView;