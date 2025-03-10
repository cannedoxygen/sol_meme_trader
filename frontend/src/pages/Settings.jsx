import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const Settings = () => {
  // Sample settings with default values
  const [settings, setSettings] = useState({
    // Trading settings
    autoTrading: false,
    tradeSize: 0.1,
    maxDailyTrades: 10,
    slippageBps: 50,
    
    // Risk settings
    riskLevel: 'medium',
    stopLossPercent: 15,
    takeProfitPercent: 30,
    
    // Notification settings
    telegramNotifications: false,
    telegramChatId: '',
    soundAlerts: true,
    
    // API keys
    openaiApiKey: '',
    birdeyeApiKey: '',
    twitterBearerToken: '',
    
    // Display settings
    theme: 'synthwave',
    glitchEffects: true,
    showCrtScanlines: true
  });
  
  // Form state
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);
  const [currentTab, setCurrentTab] = useState('trading');
  const [glitchActive, setGlitchActive] = useState(false);
  
  // Trigger glitch effect on tab change
  useEffect(() => {
    setGlitchActive(true);
    const timer = setTimeout(() => setGlitchActive(false), 800);
    return () => clearTimeout(timer);
  }, [currentTab]);
  
  // Handle input change
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };
  
  // Handle number input change with validation
  const handleNumberChange = (e) => {
    const { name, value } = e.target;
    const numValue = parseFloat(value);
    
    if (!isNaN(numValue)) {
      setSettings(prev => ({
        ...prev,
        [name]: numValue
      }));
    }
  };
  
  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    setIsSaving(true);
    
    // Simulate API call
    setTimeout(() => {
      setIsSaving(false);
      setSaveStatus('success');
      
      // Clear status after 3 seconds
      setTimeout(() => setSaveStatus(null), 3000);
    }, 1500);
  };
  
  return (
    <div className="min-h-screen bg-black/90 pt-6 pb-16 relative">
      {/* CRT Scanline Overlay */}
      <div className="absolute inset-0 pointer-events-none z-10 opacity-20 bg-scanline animate-scanline"></div>
      
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <h1 className={`text-3xl font-vcr text-center ${glitchActive ? 'animate-glitch' : ''}`}>
            <span className="text-pink-500">SYSTEM</span>
            <span className="text-cyan-400">.CONFIG</span>
          </h1>
        </motion.div>
        
        {/* Settings Container */}
        <div className="bg-black/70 border-2 border-purple-500/50 rounded-lg shadow-lg shadow-purple-500/20 backdrop-blur-sm overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-purple-900/50">
            {['trading', 'risk', 'notifications', 'api', 'display'].map((tab) => (
              <button
                key={tab}
                onClick={() => setCurrentTab(tab)}
                className={`px-4 py-3 font-vcr text-sm transition-all ${
                  currentTab === tab
                    ? 'bg-purple-900/40 text-cyan-400 border-b-2 border-cyan-400'
                    : 'text-gray-400 hover:text-pink-400 hover:bg-purple-900/20'
                }`}
              >
                {tab.toUpperCase()}
              </button>
            ))}
          </div>
          
          {/* Settings Form */}
          <form onSubmit={handleSubmit} className="p-6">
            {/* Trading Settings */}
            {currentTab === 'trading' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="space-y-6"
              >
                <h2 className="text-xl font-vcr text-pink-400 mb-4">Trading Settings</h2>
                
                {/* Auto Trading Toggle */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center">
                      <span className="font-mono text-gray-300 mr-3">Auto-Trading</span>
                      <div className={`w-12 h-6 rounded-full p-1 transition-colors ${settings.autoTrading ? 'bg-cyan-700' : 'bg-gray-700'}`}>
                        <div className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform ${settings.autoTrading ? 'translate-x-6' : 'translate-x-0'}`}></div>
                      </div>
                    </label>
                    <div className="text-xs text-gray-500">Enable autonomous trading</div>
                  </div>
                </div>
                
                {/* Trade Size */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <div className="flex flex-col">
                    <div className="flex justify-between items-center mb-2">
                      <label className="font-mono text-gray-300">Trade Size (SOL)</label>
                      <span className="text-cyan-400 font-mono">{settings.tradeSize} SOL</span>
                    </div>
                    <input
                      type="range"
                      name="tradeSize"
                      min="0.01"
                      max="1"
                      step="0.01"
                      value={settings.tradeSize}
                      onChange={handleNumberChange}
                      className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>0.01 SOL</span>
                      <span>1 SOL</span>
                    </div>
                  </div>
                </div>
                
                {/* Max Daily Trades */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <div className="flex items-center justify-between">
                    <label className="font-mono text-gray-300">Max Daily Trades</label>
                    <input
                      type="number"
                      name="maxDailyTrades"
                      min="1"
                      max="50"
                      value={settings.maxDailyTrades}
                      onChange={handleNumberChange}
                      className="bg-black border border-purple-500/50 rounded px-3 py-1 w-24 text-cyan-400 font-mono"
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Limit total trades per 24-hour period</div>
                </div>
                
                {/* Slippage */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <div className="flex items-center justify-between">
                    <label className="font-mono text-gray-300">Slippage Tolerance</label>
                    <div className="flex items-center">
                      <input
                        type="number"
                        name="slippageBps"
                        min="10"
                        max="300"
                        value={settings.slippageBps}
                        onChange={handleNumberChange}
                        className="bg-black border border-purple-500/50 rounded px-3 py-1 w-20 text-cyan-400 font-mono"
                      />
                      <span className="ml-2 text-gray-400 font-mono">bps</span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">1 bps = 0.01% (50 bps = 0.5%)</div>
                </div>
              </motion.div>
            )}
            
            {/* Risk Settings */}
            {currentTab === 'risk' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="space-y-6"
              >
                <h2 className="text-xl font-vcr text-pink-400 mb-4">Risk Management</h2>
                
                {/* Risk Level */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <label className="font-mono text-gray-300 block mb-2">Risk Level</label>
                  <div className="grid grid-cols-3 gap-3">
                    {['low', 'medium', 'high'].map((level) => (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setSettings({ ...settings, riskLevel: level })}
                        className={`py-2 px-4 rounded font-vcr text-sm ${
                          settings.riskLevel === level
                            ? level === 'low'
                              ? 'bg-green-900/50 border-2 border-green-500 text-green-400'
                              : level === 'medium'
                              ? 'bg-yellow-900/50 border-2 border-yellow-500 text-yellow-400'
                              : 'bg-red-900/50 border-2 border-red-500 text-red-400'
                            : 'bg-gray-900/50 border border-gray-700 text-gray-400 hover:border-purple-500/50'
                        }`}
                      >
                        {level.toUpperCase()}
                      </button>
                    ))}
                  </div>
                  <div className="text-xs text-gray-500 mt-2">Controls trade filtering and entry criteria</div>
                </div>
                
                {/* Stop Loss */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <div className="flex flex-col">
                    <div className="flex justify-between items-center mb-2">
                      <label className="font-mono text-gray-300">Stop Loss</label>
                      <span className="text-red-400 font-mono">-{settings.stopLossPercent}%</span>
                    </div>
                    <input
                      type="range"
                      name="stopLossPercent"
                      min="5"
                      max="30"
                      step="1"
                      value={settings.stopLossPercent}
                      onChange={handleNumberChange}
                      className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>-5%</span>
                      <span>-30%</span>
                    </div>
                  </div>
                </div>
                
                {/* Take Profit */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <div className="flex flex-col">
                    <div className="flex justify-between items-center mb-2">
                      <label className="font-mono text-gray-300">Take Profit</label>
                      <span className="text-green-400 font-mono">+{settings.takeProfitPercent}%</span>
                    </div>
                    <input
                      type="range"
                      name="takeProfitPercent"
                      min="10"
                      max="100"
                      step="5"
                      value={settings.takeProfitPercent}
                      onChange={handleNumberChange}
                      className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>+10%</span>
                      <span>+100%</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
            
            {/* Notification Settings */}
            {currentTab === 'notifications' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="space-y-6"
              >
                <h2 className="text-xl font-vcr text-pink-400 mb-4">Notification Settings</h2>
                
                {/* Telegram Notifications */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <div className="flex items-center justify-between mb-3">
                    <label className="flex items-center">
                      <span className="font-mono text-gray-300 mr-3">Telegram Alerts</span>
                      <div className={`w-12 h-6 rounded-full p-1 transition-colors ${settings.telegramNotifications ? 'bg-cyan-700' : 'bg-gray-700'}`}>
                        <div className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform ${settings.telegramNotifications ? 'translate-x-6' : 'translate-x-0'}`}></div>
                      </div>
                    </label>
                  </div>
                  
                  {settings.telegramNotifications && (
                    <div className="mt-3">
                      <label className="font-mono text-gray-300 text-sm block mb-1">Telegram Chat ID</label>
                      <input
                        type="text"
                        name="telegramChatId"
                        value={settings.telegramChatId}
                        onChange={handleChange}
                        placeholder="e.g. -1001234567890"
                        className="bg-black border border-purple-500/50 rounded px-3 py-2 w-full text-cyan-400 font-mono"
                      />
                      <div className="text-xs text-gray-500 mt-1">The Chat ID where alerts will be sent</div>
                    </div>
                  )}
                </div>
                
                {/* Sound Alerts */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center">
                      <span className="font-mono text-gray-300 mr-3">Sound Alerts</span>
                      <div className={`w-12 h-6 rounded-full p-1 transition-colors ${settings.soundAlerts ? 'bg-cyan-700' : 'bg-gray-700'}`}>
                        <div className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform ${settings.soundAlerts ? 'translate-x-6' : 'translate-x-0'}`}></div>
                      </div>
                    </label>
                    <div className="text-xs text-gray-500">Play sounds for trades and notifications</div>
                  </div>
                </div>
              </motion.div>
            )}
            
            {/* API Keys Settings */}
            {currentTab === 'api' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="space-y-6"
              >
                <h2 className="text-xl font-vcr text-pink-400 mb-4">API Configuration</h2>
                
                {/* OpenAI API Key */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <label className="font-mono text-gray-300 text-sm block mb-1">OpenAI API Key</label>
                  <input
                    type="password"
                    name="openaiApiKey"
                    value={settings.openaiApiKey}
                    onChange={handleChange}
                    placeholder="sk-..."
                    className="bg-black border border-purple-500/50 rounded px-3 py-2 w-full text-cyan-400 font-mono"
                  />
                  <div className="text-xs text-gray-500 mt-1">Required for AI analysis</div>
                </div>
                
                {/* Birdeye API Key */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <label className="font-mono text-gray-300 text-sm block mb-1">Birdeye API Key</label>
                  <input
                    type="password"
                    name="birdeyeApiKey"
                    value={settings.birdeyeApiKey}
                    onChange={handleChange}
                    placeholder="Enter API key..."
                    className="bg-black border border-purple-500/50 rounded px-3 py-2 w-full text-cyan-400 font-mono"
                  />
                  <div className="text-xs text-gray-500 mt-1">Required for token data</div>
                </div>
                
                {/* Twitter Bearer Token */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <label className="font-mono text-gray-300 text-sm block mb-1">Twitter Bearer Token</label>
                  <input
                    type="password"
                    name="twitterBearerToken"
                    value={settings.twitterBearerToken}
                    onChange={handleChange}
                    placeholder="Enter token..."
                    className="bg-black border border-purple-500/50 rounded px-3 py-2 w-full text-cyan-400 font-mono"
                  />
                  <div className="text-xs text-gray-500 mt-1">Optional for sentiment analysis</div>
                </div>
              </motion.div>
            )}
            
            {/* Display Settings */}
            {currentTab === 'display' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="space-y-6"
              >
                <h2 className="text-xl font-vcr text-pink-400 mb-4">Display Settings</h2>
                
                {/* Theme Selector */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <label className="font-mono text-gray-300 block mb-2">Theme</label>
                  <div className="grid grid-cols-3 gap-3">
                    {['synthwave', 'cyberpunk', 'vaporwave'].map((theme) => (
                      <button
                        key={theme}
                        type="button"
                        onClick={() => setSettings({ ...settings, theme })}
                        className={`py-2 px-4 rounded font-vcr text-sm ${
                          settings.theme === theme
                            ? theme === 'synthwave'
                              ? 'bg-gradient-to-r from-purple-900/70 to-pink-900/70 border-2 border-purple-500 text-cyan-400'
                              : theme === 'cyberpunk'
                              ? 'bg-gradient-to-r from-yellow-900/70 to-red-900/70 border-2 border-yellow-500 text-cyan-400'
                              : 'bg-gradient-to-r from-pink-900/70 to-cyan-900/70 border-2 border-pink-500 text-cyan-400'
                            : 'bg-gray-900/50 border border-gray-700 text-gray-400 hover:border-purple-500/50'
                        }`}
                      >
                        {theme.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Glitch Effects */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center">
                      <span className="font-mono text-gray-300 mr-3">Glitch Effects</span>
                      <div className={`w-12 h-6 rounded-full p-1 transition-colors ${settings.glitchEffects ? 'bg-cyan-700' : 'bg-gray-700'}`}>
                        <div className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform ${settings.glitchEffects ? 'translate-x-6' : 'translate-x-0'}`}></div>
                      </div>
                    </label>
                    <div className="text-xs text-gray-500">Enable glitch animations</div>
                  </div>
                </div>
                
                {/* CRT Scanlines */}
                <div className="bg-black/50 p-4 rounded border border-purple-500/30">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center">
                      <span className="font-mono text-gray-300 mr-3">CRT Scanlines</span>
                      <div className={`w-12 h-6 rounded-full p-1 transition-colors ${settings.showCrtScanlines ? 'bg-cyan-700' : 'bg-gray-700'}`}>
                        <div className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform ${settings.showCrtScanlines ? 'translate-x-6' : 'translate-x-0'}`}></div>
                      </div>
                    </label>
                    <div className="text-xs text-gray-500">Show CRT monitor scanline effect</div>
                  </div>
                </div>
              </motion.div>
            )}
            
            {/* Submit Button */}
            <div className="mt-8 flex items-center justify-between">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                type="submit"
                disabled={isSaving}
                className={`px-6 py-2 bg-gradient-to-r from-purple-700 to-pink-600 rounded font-vcr text-white relative overflow-hidden ${
                  isSaving ? 'opacity-70 cursor-not-allowed' : 'hover:from-purple-600 hover:to-pink-500'
                }`}
              >
                {isSaving ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    SAVING...
                  </span>
                ) : 'SAVE SETTINGS'}
                
                {/* Button scanline effect */}
                <div className="absolute inset-0 pointer-events-none z-10 opacity-10 bg-scanline animate-scanline"></div>
              </motion.button>
              
              {/* Status message */}
              {saveStatus && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={`font-vcr ${saveStatus === 'success' ? 'text-green-400' : 'text-red-400'}`}
                >
                  {saveStatus === 'success' ? 'SETTINGS SAVED' : 'ERROR SAVING'}
                </motion.div>
              )}
            </div>
          </form>
        </div>
        
        {/* Terminal-style footer note */}
        <div className="mt-8 text-center font-mono text-xs text-gray-500">
          <div>SYSTEM.CONFIG v1.04 | LAST UPDATED: {new Date().toLocaleDateString()}</div>
          <div className="mt-1">WARNING: MODIFYING THESE SETTINGS MAY AFFECT BOT PERFORMANCE</div>
        </div>
      </div>
    </div>
  );
};

export default Settings;