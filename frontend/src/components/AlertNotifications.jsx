import React, { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

// Alert type constants
const ALERT_TYPES = {
  BUY: 'buy',
  SELL: 'sell',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
  SUCCESS: 'success'
};

const AlertNotifications = ({ alerts = [], onDismiss, maxAlerts = 3 }) => {
  const [visibleAlerts, setVisibleAlerts] = useState([]);
  const [audioEnabled] = useState(true); // In a real app, this would come from user settings
  
  // Sound effects (would be implemented with actual audio files)
  const playAlertSound = (type) => {
    if (!audioEnabled) return;
    
    // In a real implementation, play the appropriate sound based on type
    console.log(`Playing ${type} sound effect`);
  };
  
  // Update visible alerts when alerts prop changes
  useEffect(() => {
    // Take only the most recent alerts up to maxAlerts
    const recentAlerts = [...alerts].slice(0, maxAlerts);
    setVisibleAlerts(recentAlerts);
    
    // Play sound for newest alert if it exists
    if (recentAlerts.length > 0 && recentAlerts[0] !== visibleAlerts[0]) {
      playAlertSound(recentAlerts[0].type);
    }
  }, [alerts, maxAlerts]);
  
  // Auto-dismiss alerts after timeout
  useEffect(() => {
    if (visibleAlerts.length === 0) return;
    
    // Set timeout to dismiss oldest alert
    const timer = setTimeout(() => {
      if (visibleAlerts.length > 0 && onDismiss) {
        onDismiss(visibleAlerts[visibleAlerts.length - 1].id);
      }
    }, 10000); // 10 seconds
    
    return () => clearTimeout(timer);
  }, [visibleAlerts, onDismiss]);

  // Get appropriate colors and icons for each alert type
  const getAlertStyle = (type) => {
    switch (type) {
      case ALERT_TYPES.BUY:
        return {
          bgColor: 'bg-gradient-to-r from-green-900/90 to-green-800/90',
          borderColor: 'border-green-500',
          textColor: 'text-green-400',
          icon: '🚀',
          glowColor: 'shadow-green-500/30'
        };
      case ALERT_TYPES.SELL:
        return {
          bgColor: 'bg-gradient-to-r from-red-900/90 to-red-800/90',
          borderColor: 'border-red-500',
          textColor: 'text-red-400',
          icon: '💰',
          glowColor: 'shadow-red-500/30'
        };
      case ALERT_TYPES.ERROR:
        return {
          bgColor: 'bg-gradient-to-r from-red-900/90 to-red-800/90',
          borderColor: 'border-red-500',
          textColor: 'text-red-400',
          icon: '⚠️',
          glowColor: 'shadow-red-500/30'
        };
      case ALERT_TYPES.WARNING:
        return {
          bgColor: 'bg-gradient-to-r from-yellow-900/90 to-yellow-800/90',
          borderColor: 'border-yellow-500',
          textColor: 'text-yellow-400',
          icon: '⚠️',
          glowColor: 'shadow-yellow-500/30'
        };
      case ALERT_TYPES.SUCCESS:
        return {
          bgColor: 'bg-gradient-to-r from-green-900/90 to-green-800/90',
          borderColor: 'border-green-500',
          textColor: 'text-green-400',
          icon: '✅',
          glowColor: 'shadow-green-500/30'
        };
      case ALERT_TYPES.INFO:
      default:
        return {
          bgColor: 'bg-gradient-to-r from-blue-900/90 to-indigo-800/90',
          borderColor: 'border-blue-500',
          textColor: 'text-blue-400',
          icon: 'ℹ️',
          glowColor: 'shadow-blue-500/30'
        };
    }
  };

  return (
    <div className="fixed top-5 right-5 z-50 flex flex-col items-end space-y-3 max-w-sm">
      <AnimatePresence>
        {visibleAlerts.map((alert, index) => {
          const { bgColor, borderColor, textColor, icon, glowColor } = getAlertStyle(alert.type);
          const isNew = index === 0;
          
          return (
            <motion.div
              key={alert.id}
              className={`w-full ${bgColor} border-l-4 ${borderColor} shadow-lg ${glowColor} backdrop-blur-sm rounded-l px-4 py-3 relative`}
              initial={{ x: 300, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 300, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 200, damping: 20 }}
            >
              {/* CRT Scanline Effect */}
              <div className="absolute inset-0 pointer-events-none z-10 opacity-10 bg-scanline animate-scanline rounded-l"></div>
              
              {/* Glitchy overlay effect for new alerts */}
              {isNew && (
                <div className="absolute inset-0 bg-white/5 animate-glitch-overlay z-0 rounded-l"></div>
              )}
              
              <div className="flex items-start">
                {/* Alert Icon */}
                <div className="mr-3 text-xl">{icon}</div>
                
                {/* Alert Content */}
                <div className="flex-1">
                  {/* Title */}
                  {alert.title && (
                    <h3 className={`text-sm font-vcr ${textColor} ${isNew ? 'animate-glitch-text' : ''}`}>
                      {alert.title}
                    </h3>
                  )}
                  
                  {/* Message */}
                  <p className="text-xs text-gray-200 font-mono mt-1">
                    {alert.message}
                  </p>
                  
                  {/* Additional Info */}
                  {alert.details && (
                    <div className="mt-1 text-[10px] text-gray-400">
                      {alert.details}
                    </div>
                  )}
                  
                  {/* Timestamp */}
                  <div className="mt-2 text-[10px] text-gray-500 font-mono">
                    {alert.timestamp || new Date().toLocaleTimeString()}
                  </div>
                </div>
                
                {/* Close Button */}
                <button
                  onClick={() => onDismiss && onDismiss(alert.id)}
                  className="ml-2 text-gray-400 hover:text-white transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              {/* Progress bar for auto dismiss */}
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-700">
                <div 
                  className={`h-full ${textColor.replace('text-', 'bg-')}`}
                  style={{ 
                    width: '100%',
                    animation: 'shrink 10s linear forwards'
                  }}
                ></div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
};

export default AlertNotifications;

// Add these to your CSS/tailwind config:
// @keyframes shrink {
//   from { width: 100%; }
//   to { width: 0%; }
// }
//
// @keyframes glitch-overlay {
//   0%, 100% { opacity: 0; }
//   20%, 80% { opacity: 0.03; }
//   50% { opacity: 0.10; }
// }
//
// @keyframes glitch-text {
//   0% { transform: translate(0); }
//   20% { transform: translate(-2px, 1px); }
//   40% { transform: translate(-1px, -1px); filter: hue-rotate(90deg); }
//   60% { transform: translate(1px, 1px); }
//   80% { transform: translate(1px, -1px); filter: hue-rotate(-90deg); }
//   100% { transform: translate(0); }
// }
//
// .animate-glitch-overlay {
//   animation: glitch-overlay 1s ease-in-out infinite;
// }
//
// .animate-glitch-text {
//   animation: glitch-text 1s ease-in-out infinite;
// }