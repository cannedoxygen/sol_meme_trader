import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import TradeDashboard from '../components/TradeDashboard';
import RiskAssessment from '../components/RiskAssessment';
import SentimentWidget from '../components/SentimentWidget';
import AlertNotifications from '../components/AlertNotifications';
import Header from '../components/Header';
import Footer from '../components/Footer';

const Dashboard = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [tokens, setTokens] = useState([]);
  const [activeToken, setActiveToken] = useState(null);
  const [walletBalance, setWalletBalance] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [glitchActive, setGlitchActive] = useState(false);
  const [statsVisible, setStatsVisible] = useState(false);

  // Simulate loading data
  useEffect(() => {
    const loadData = async () => {
      // Pretend to fetch data
      setTimeout(() => {
        // Sample tokens data
        const sampleTokens = [
          {
            address: "token1",
            name: "RetroMoon",
            symbol: "RMOON",
            priceUSD: 0.0000152,
            priceChange24h: 12.5,
            v24hUSD: 125000,
            liquidity: 45000,
            holders: 420
          },
          {
            address: "token2",
            name: "WaveVapor",
            symbol: "VAPOR",
            priceUSD: 0.00000789,
            priceChange24h: -3.7,
            v24hUSD: 98500,
            liquidity: 32000,
            holders: 310
          },
          {
            address: "token3",
            name: "PixelPunk",
            symbol: "PXLP",
            priceUSD: 0.0000935,
            priceChange24h: 26.8,
            v24hUSD: 214000,
            liquidity: 76000,
            holders: 540
          },
          {
            address: "token4",
            name: "SynthSol",
            symbol: "SYNTH",
            priceUSD: 0.000127,
            priceChange24h: 4.2,
            v24hUSD: 145000,
            liquidity: 58000,
            holders: 385
          }
        ];

        setTokens(sampleTokens);
        setActiveToken(sampleTokens[0]);
        setWalletBalance(1.234);
        setIsConnected(true);
        setIsLoading(false);

        // Add sample alert
        addAlert({
          id: Date.now(),
          type: 'info',
          title: 'DASHBOARD INITIALIZED',
          message: 'System connected to Solana network',
          details: 'All components operational',
          timestamp: new Date().toLocaleTimeString()
        });

        // Show stats after a delay
        setTimeout(() => {
          setStatsVisible(true);
        }, 800);
      }, 2500);
    };

    loadData();

    // Trigger glitch effect periodically
    const glitchInterval = setInterval(() => {
      setGlitchActive(true);
      setTimeout(() => setGlitchActive(false), 800);
    }, 15000);

    return () => clearInterval(glitchInterval);
  }, []);

  // Handle wallet connection
  const handleConnectWallet = () => {
    // Simulate wallet connection
    if (!isConnected) {
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
    }
  };

  // Handle token selection
  const handleTokenSelect = (token) => {
    setActiveToken(token);
    
    // Trigger glitch effect on token change
    setGlitchActive(true);
    setTimeout(() => setGlitchActive(false), 800);
    
    addAlert({
      id: Date.now(),
      type: 'info',
      title: `SELECTED ${token.symbol}`,
      message: `Analyzing ${token.name}`,
      details: `Price: $${token.priceUSD.toFixed(8)}`,
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

  // Sample sentiment data
  const sentimentData = {
    sentiment_score: 0.7,
    sentiment_label: "positive",
    confidence: 0.8,
    bullish_signals: [
      "Increasing Twitter mentions",
      "Positive community sentiment",
      "Recent partnership announcement"
    ],
    bearish_signals: [
      "Some profit taking expected"
    ],
    key_themes: [
      "launch", "solana", "memecoin", "moon"
    ],
    engagement_level: "high",
    summary: "Overall bullish sentiment with strong community engagement. Social mentions have increased 3x in the last 24 hours."
  };

  // Sample risk data
  const riskData = {
    passes_filters: true,
    risk_score: 35,
    risk_level: "medium",
    risk_reason: "Acceptable risk profile with good liquidity and distribution",
    liquidity_usd: 45000,
    holders_count: 420,
    top_holders_concentration: 45,
    liquidity_locked: 22000,
    contract_verification: true,
    honeypot_risk: false,
    max_tax: 5,
    age_hours: 72,
    assessments: {
      liquidity: { result: "passed", details: "Sufficient liquidity" },
      rugcheck: { result: "passed", details: "No rug pull indicators" },
      distribution: { result: "warning", details: "Moderate holder concentration" },
      holders: { result: "passed", details: "Sufficient holder count" },
      tax: { result: "passed", details: "Reasonable tax rate" }
    }
  };

  return (
    <div className="min-h-screen bg-black relative overflow-hidden">
      {/* Retro grid background */}
      <div className="absolute inset-0 z-0 bg-grid-pattern opacity-20"></div>
      
      {/* Stars background */}
      <div className="absolute inset-0 z-0">
        <div className="stars-sm"></div>
        <div className="stars-md"></div>
        <div className="stars-lg"></div>
      </div>
      
      {/* CRT Overlay */}
      <div className="absolute inset-0 pointer-events-none z-50 crt-overlay opacity-10"></div>
      
      {/* Header */}
      <Header 
        walletBalance={walletBalance} 
        isConnected={isConnected} 
        onConnectWallet={handleConnectWallet} 
      />
      
      {/* Main Content */}
      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {isLoading ? (
          /* Loading Screen with Retro Look */
          <div className="flex flex-col items-center justify-center h-96">
            <div className="text-4xl font-vcr text-cyan-400 mb-6 animate-pulse">LOADING...</div>
            <div className="w-64 h-4 bg-black/60 border border-purple-500/50 rounded overflow-hidden">
              <div className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500 animate-load-progress"></div>
            </div>
            
            {/* Fake terminal loading text */}
            <div className="mt-8 font-mono text-sm text-green-400 max-w-lg glitch-text">
              > INITIALIZING SYSTEM...<br />
              > CONNECTING TO SOLANA NETWORK...<br />
              > LOADING MEMECOIN DATABASE...<br />
              > ACTIVATING AI ANALYSIS MODULES...<br />
              > ESTABLISHING SECURE CONNECTION...
            </div>
          </div>
        ) : (
          /* Dashboard Content */
          <div className="space-y-8">
            {/* Stats Bar */}
            <motion.div 
              initial={{ opacity: 0, y: -20 }}
              animate={{ 
                opacity: statsVisible ? 1 : 0, 
                y: statsVisible ? 0 : -20 
              }}
              transition={{ duration: 0.5 }}
              className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8"
            >
              {/* Market Stats */}
              <div className="bg-black/60 border border-purple-500/30 rounded-lg p-4 backdrop-blur-sm shadow-lg flex flex-col">
                <div className="text-xs text-gray-400 font-vcr">SOLANA PRICE</div>
                <div className="text-xl font-vcr text-green-400 mt-1">$123.45</div>
                <div className="text-xs text-green-500 mt-1">▲ 2.3%</div>
              </div>
              
              <div className="bg-black/60 border border-purple-500/30 rounded-lg p-4 backdrop-blur-sm shadow-lg flex flex-col">
                <div className="text-xs text-gray-400 font-vcr">24H VOLUME</div>
                <div className="text-xl font-vcr text-cyan-400 mt-1">$1.2B</div>
                <div className="text-xs text-gray-400 mt-1">ACROSS ECOSYSTEM</div>
              </div>
              
              <div className="bg-black/60 border border-purple-500/30 rounded-lg p-4 backdrop-blur-sm shadow-lg flex flex-col">
                <div className="text-xs text-gray-400 font-vcr">NEW TOKENS</div>
                <div className="text-xl font-vcr text-pink-400 mt-1">16</div>
                <div className="text-xs text-gray-400 mt-1">LAST 24 HOURS</div>
              </div>
              
              <div className="bg-black/60 border border-purple-500/30 rounded-lg p-4 backdrop-blur-sm shadow-lg flex flex-col">
                <div className="text-xs text-gray-400 font-vcr">MARKET SENTIMENT</div>
                <div className="text-xl font-vcr text-cyan-400 mt-1">BULLISH</div>
                <div className="text-xs text-green-500 mt-1">▲ RISING</div>
              </div>
            </motion.div>

            {/* Main Dashboard Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column - Trade Dashboard */}
              <div className="lg:col-span-2">
                <TradeDashboard 
                  tokens={tokens}
                  activeToken={activeToken}
                  onTokenSelect={handleTokenSelect}
                  walletBalance={walletBalance}
                />
              </div>
              
              {/* Right Column - Analysis Tools */}
              <div className="space-y-6">
                {/* Sentiment Analysis */}
                <SentimentWidget 
                  tokenData={activeToken}
                  sentiment={sentimentData}
                />
                
                {/* Risk Assessment */}
                <RiskAssessment 
                  tokenData={activeToken}
                  riskData={riskData}
                />
              </div>
            </div>
            
            {/* Bottom Terminal Section */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mt-8 bg-black/80 border border-purple-500/30 rounded-lg p-4 font-mono text-sm text-green-400"
            >
              <div className="flex items-center mb-2">
                <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse mr-2"></div>
                <div className="text-gray-400 font-vcr">SYSTEM.TERMINAL</div>
              </div>
              
              <div className="space-y-1 max-h-32 overflow-y-auto terminal-history">
                <div>> SYSTEM INITIALIZED AT {new Date().toLocaleTimeString()}</div>
                <div>> CONNECTED TO SOLANA MAINNET</div>
                <div>> WATCHING {tokens.length} TOKENS</div>
                <div>> AI ANALYSIS MODULE ACTIVE</div>
                <div>> AWAITING INPUT...</div>
              </div>
              
              <div className="flex items-center mt-3">
                <span className="mr-2">$</span>
                <input 
                  type="text" 
                  placeholder="Type a command..." 
                  className="bg-transparent border-none outline-none text-green-400 w-full"
                />
              </div>
            </motion.div>
          </div>
        )}
      </main>
      
      {/* Footer with retro design */}
      <Footer 
        systemStatus="online"
        uptime="12h 34m 56s" 
        version="1.0.4" 
      />
      
      {/* Alerts */}
      <AlertNotifications 
        alerts={alerts} 
        onDismiss={dismissAlert} 
      />
      
      {/* Bottom retro sun/horizon effect */}
      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-purple-900/30 to-transparent z-1"></div>
      <div className="absolute -bottom-20 left-1/2 transform -translate-x-1/2 w-full max-w-2xl h-40 rounded-full bg-gradient-to-t from-pink-600 to-purple-700 blur-3xl opacity-20 z-1"></div>
    </div>
  );
};

export default Dashboard;