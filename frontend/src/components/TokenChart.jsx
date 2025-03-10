import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const TokenChart = ({ tokenData, timeframe = '24h' }) => {
  const [chartData, setChartData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [glitchActive, setGlitchActive] = useState(false);
  
  // Available timeframes
  const timeframes = ['1h', '24h', '7d', '30d'];
  
  // Generate synthetic data based on token and timeframe
  useEffect(() => {
    if (!tokenData) return;
    
    // Simulate loading
    setIsLoading(true);
    
    // Trigger glitch effect on timeframe change
    setGlitchActive(true);
    setTimeout(() => setGlitchActive(false), 800);
    
    // Generate synthetic chart data
    const generateChartData = () => {
      const now = new Date();
      const data = [];
      let numPoints = 24;
      let pointInterval = 60 * 60 * 1000; // 1 hour in milliseconds
      
      switch (timeframe) {
        case '1h':
          numPoints = 60;
          pointInterval = 60 * 1000; // 1 minute
          break;
        case '7d':
          numPoints = 7 * 24;
          break;
        case '30d':
          numPoints = 30;
          pointInterval = 24 * 60 * 60 * 1000; // 1 day
          break;
        default: // 24h
          numPoints = 24;
          break;
      }
      
      // Current price from token data
      const currentPrice = tokenData.priceUSD || 0.0001;
      
      // Volatility based on token data (use price change if available)
      const volatility = tokenData.priceChange24h
        ? Math.abs(tokenData.priceChange24h) / 100
        : 0.05;
        
      // Generate price trend with some randomness
      let price = currentPrice;
      
      // Work backwards from current time
      for (let i = numPoints - 1; i >= 0; i--) {
        const time = new Date(now.getTime() - (i * pointInterval));
        
        // Add some randomness to price
        const randomFactor = 1 + ((Math.random() - 0.5) * volatility);
        price = price * randomFactor;
        
        // Don't let price go to 0
        price = Math.max(price, 0.0000001);
        
        data.push({
          time: time.toISOString(),
          price: price,
          formattedTime: formatTime(time, timeframe)
        });
      }
      
      // Make sure the last point matches the current price
      if (data.length > 0) {
        data[data.length - 1].price = currentPrice;
      }
      
      return data;
    };
    
    const timer = setTimeout(() => {
      const newData = generateChartData();
      setChartData(newData);
      setIsLoading(false);
    }, 800);
    
    return () => clearTimeout(timer);
  }, [tokenData, timeframe]);
  
  // Format time based on timeframe
  const formatTime = (date, timeframe) => {
    switch (timeframe) {
      case '1h':
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      case '24h':
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      case '7d':
        return date.toLocaleDateString([], { weekday: 'short', hour: '2-digit' });
      case '30d':
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
      default:
        return date.toLocaleTimeString();
    }
  };
  
  // Custom tooltip component with retro style
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const dataPoint = payload[0].payload;
      
      return (
        <div className="bg-black/90 border border-purple-500/50 p-2 text-xs font-mono">
          <p className="text-cyan-400">{dataPoint.formattedTime}</p>
          <p className="text-pink-400">Price: ${dataPoint.price.toFixed(8)}</p>
        </div>
      );
    }
    
    return null;
  };
  
  // Custom tick format for Y axis
  const formatYAxis = (value) => {
    // For very small values (like meme coins) use scientific notation
    if (value < 0.00001) {
      return value.toExponential(2);
    }
    return value.toFixed(8);
  };
  
  // Function to determine color based on price trend
  const getChartColor = () => {
    if (chartData.length < 2) return "#9945FF"; // Default purple
    
    const startPrice = chartData[0].price;
    const endPrice = chartData[chartData.length - 1].price;
    
    if (endPrice > startPrice) {
      return "#14F195"; // Green for uptrend
    } else if (endPrice < startPrice) {
      return "#FE53BB"; // Pink for downtrend
    } else {
      return "#9945FF"; // Purple for neutral
    }
  };
  
  return (
    <div className="bg-black/80 border-2 border-purple-500/50 rounded-lg overflow-hidden shadow-lg shadow-purple-500/20 backdrop-blur-sm p-4 relative">
      {/* CRT Scanline Overlay */}
      <div className="absolute inset-0 pointer-events-none z-10 opacity-10 bg-scanline animate-scanline"></div>
      
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h3 className={`font-vcr text-lg ${glitchActive ? 'animate-glitch' : ''}`}>
          <span className="text-pink-500">{tokenData?.symbol || "UNKNOWN"}</span>
          <span className="text-cyan-400">.CHART</span>
        </h3>
        
        {/* Timeframe selector */}
        <div className="flex space-x-2">
          {timeframes.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-2 py-1 text-xs font-vcr transition-colors ${
                timeframe === tf 
                  ? 'bg-purple-900/50 text-cyan-400 border border-cyan-500/50' 
                  : 'text-gray-400 hover:text-pink-400 border border-transparent'
              }`}
            >
              {tf.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      
      {/* Chart */}
      <div className="h-64 w-full relative">
        {isLoading ? (
          <div className="absolute inset-0 flex justify-center items-center">
            <div className="text-lg font-vcr text-cyan-400 animate-pulse">LOADING DATA...</div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
            >
              <defs>
                <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={getChartColor()} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={getChartColor()} stopOpacity={0.2}/>
                </linearGradient>
              </defs>
              <CartesianGrid 
                stroke="rgba(139, 92, 246, 0.15)" 
                strokeDasharray="3 3" 
              />
              <XAxis 
                dataKey="formattedTime" 
                tick={{ fill: '#A78BFA', fontSize: 10, fontFamily: 'monospace' }}
                tickLine={{ stroke: '#A78BFA' }}
                axisLine={{ stroke: '#A78BFA' }}
                minTickGap={10}
              />
              <YAxis 
                tickFormatter={formatYAxis}
                tick={{ fill: '#A78BFA', fontSize: 10, fontFamily: 'monospace' }}
                tickLine={{ stroke: '#A78BFA' }}
                axisLine={{ stroke: '#A78BFA' }}
                width={80}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line 
                type="monotone" 
                dataKey="price" 
                stroke={getChartColor()} 
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: '#F5F3FF', strokeWidth: 1 }}
                animationDuration={500}
                fill="url(#gradient)"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
        
        {/* Price change indicator */}
        {!isLoading && chartData.length > 1 && (
          <div className="absolute top-0 right-0 px-2 py-1 font-mono text-xs">
            <div 
              className={`${
                chartData[chartData.length - 1].price > chartData[0].price
                  ? 'text-green-400'
                  : chartData[chartData.length - 1].price < chartData[0].price
                  ? 'text-red-400'
                  : 'text-yellow-400'
              }`}
            >
              {((chartData[chartData.length - 1].price - chartData[0].price) / chartData[0].price * 100).toFixed(2)}%
              {chartData[chartData.length - 1].price > chartData[0].price ? ' ▲' : chartData[chartData.length - 1].price < chartData[0].price ? ' ▼' : ' ◄►'}
            </div>
          </div>
        )}
      </div>
      
      {/* Stats at bottom */}
      <div className="grid grid-cols-3 gap-2 mt-4 text-xs font-mono">
        <div className="bg-black/60 p-2 rounded border border-purple-500/30">
          <div className="text-gray-400">Current</div>
          <div className="text-cyan-400">${tokenData?.priceUSD?.toFixed(8) || '0.00000000'}</div>
        </div>
        <div className="bg-black/60 p-2 rounded border border-purple-500/30">
          <div className="text-gray-400">Volume 24h</div>
          <div className="text-pink-400">${tokenData?.v24hUSD?.toLocaleString() || '0'}</div>
        </div>
        <div className="bg-black/60 p-2 rounded border border-purple-500/30">
          <div className="text-gray-400">Market Cap</div>
          <div className="text-purple-400">${tokenData?.marketCap?.toLocaleString() || 'Unknown'}</div>
        </div>
      </div>
      
      {/* Terminal Line */}
      <div className="mt-3 flex items-center text-green-400 font-mono text-xs">
        <span className="mr-2">$</span>
        <span className="animate-pulse">_</span>
      </div>
    </div>
  );
};

export default TokenChart;