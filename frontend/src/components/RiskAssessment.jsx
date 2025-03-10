import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const RiskAssessment = ({ tokenData, riskData }) => {
  const [glitchActive, setGlitchActive] = useState(false);
  
  // Default risk data if not provided
  const defaultRiskData = {
    passes_filters: true,
    risk_score: 50,
    risk_level: "medium",
    risk_reason: "Default risk assessment",
    liquidity_usd: 5000,
    holders_count: 100,
    top_holders_concentration: 45,
    liquidity_locked: 1000,
    contract_verification: true,
    honeypot_risk: false,
    max_tax: 5,
    age_hours: 48,
    assessments: {
      liquidity: { result: "passed", details: "Sufficient liquidity" },
      rugcheck: { result: "passed", details: "No rug pull indicators" },
      distribution: { result: "warning", details: "Moderate holder concentration" },
      holders: { result: "passed", details: "Sufficient holder count" },
      tax: { result: "passed", details: "Reasonable tax rate" }
    }
  };

  const risk = riskData || defaultRiskData;
  
  // Calculate a normalized risk score (0-100, where lower is better)
  const normalizedRiskScore = risk.risk_score;
  
  // Trigger glitch effect on component mount and risk change
  useEffect(() => {
    setGlitchActive(true);
    const timer = setTimeout(() => setGlitchActive(false), 1200);
    return () => clearTimeout(timer);
  }, [risk.risk_score]);
  
  // Get color based on risk level
  const getRiskColor = () => {
    switch(risk.risk_level) {
      case "low": return "text-green-400";
      case "medium": return "text-yellow-400";
      case "high": return "text-orange-400";
      case "extreme": return "text-red-500";
      default: return "text-yellow-400";
    }
  };
  
  // Get color for progress bar based on value
  const getProgressColor = (value, inverted = false) => {
    // For inverted scales (where higher is worse)
    if (inverted) {
      if (value >= 80) return "bg-red-500";
      if (value >= 60) return "bg-orange-500";
      if (value >= 40) return "bg-yellow-500";
      return "bg-green-500";
    } 
    // For regular scales (where higher is better)
    else {
      if (value >= 80) return "bg-green-500";
      if (value >= 60) return "bg-yellow-500";
      if (value >= 40) return "bg-orange-500";
      return "bg-red-500";
    }
  };
  
  // Get result icon
  const getResultIcon = (result) => {
    switch(result) {
      case "passed": return "✓";
      case "warning": return "⚠";
      case "failed": return "✗";
      default: return "?";
    }
  };
  
  // Get result color
  const getResultColor = (result) => {
    switch(result) {
      case "passed": return "text-green-400";
      case "warning": return "text-yellow-400";
      case "failed": return "text-red-400";
      default: return "text-gray-400";
    }
  };

  return (
    <div className="bg-black/80 border-2 border-purple-500/50 rounded-lg overflow-hidden shadow-[0_0_15px_rgba(157,23,248,0.4)]">
      {/* Security Header */}
      <div className="bg-gradient-to-r from-purple-900 to-indigo-900 px-4 py-2 flex justify-between items-center">
        <div className="font-vcr text-cyan-300 tracking-wider">TOKEN_SECURITY_SCAN.EXE</div>
        <div className="flex items-center">
          <div className={`w-2 h-2 rounded-full ${risk.passes_filters ? 'bg-green-500 animate-pulse' : 'bg-red-500'} mr-2`}></div>
          <div className="text-xs text-gray-300 font-vcr">{risk.passes_filters ? 'SECURE' : 'CAUTION'}</div>
        </div>
      </div>
      
      {/* Risk Display */}
      <div className="p-4 relative">
        {/* Scanline effect */}
        <div className="absolute inset-0 pointer-events-none z-10 opacity-20 bg-scanline animate-scanline"></div>
        
        {/* Risk Score Gauge */}
        <div className="mb-6">
          <div className="flex justify-between mb-1">
            <span className="text-gray-400 font-vcr text-sm">RISK_SCORE</span>
            <span className={`${getRiskColor()} font-vcr text-sm ${glitchActive ? 'animate-glitch' : ''}`}>
              {normalizedRiskScore}/100
            </span>
          </div>
          
          <div className="relative w-full h-8 bg-black/40 border border-purple-500/30 rounded-sm overflow-hidden">
            <motion.div 
              className={`h-full ${getProgressColor(normalizedRiskScore, true)}`}
              initial={{ width: 0 }}
              animate={{ width: `${normalizedRiskScore}%` }}
              transition={{ duration: 1, ease: "easeOut" }}
            />
            
            {/* Risk level markers */}
            <div className="absolute top-0 left-0 w-full h-full flex">
              <div className="border-r border-gray-600 h-full flex-1 flex items-end justify-end">
                <span className="text-[8px] text-gray-400 mr-1 mb-1">LOW</span>
              </div>
              <div className="border-r border-gray-600 h-full flex-1 flex items-end justify-end">
                <span className="text-[8px] text-gray-400 mr-1 mb-1">MED</span>
              </div>
              <div className="border-r border-gray-600 h-full flex-1 flex items-end justify-end">
                <span className="text-[8px] text-gray-400 mr-1 mb-1">HIGH</span>
              </div>
              <div className="h-full flex-1 flex items-end justify-end">
                <span className="text-[8px] text-gray-400 mr-1 mb-1">EXTREME</span>
              </div>
            </div>
          </div>
          
          {/* Risk Status */}
          <div className={`text-center mt-2 ${getRiskColor()} font-vcr`}>
            {risk.risk_level.toUpperCase()} RISK
          </div>
        </div>
        
        {/* Risk Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Left Column */}
          <div className="space-y-3">
            {/* Liquidity */}
            <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
              <div className="flex justify-between mb-1">
                <span className="text-gray-400 text-xs">LIQUIDITY:</span>
                <span className="text-cyan-300 text-xs">${risk.liquidity_usd.toLocaleString()}</span>
              </div>
              <div className="w-full bg-gray-800 h-2 rounded-sm overflow-hidden">
                <div 
                  className={`h-full ${getProgressColor(Math.min(risk.liquidity_usd / 10000 * 100, 100))}`} 
                  style={{ width: `${Math.min(risk.liquidity_usd / 10000 * 100, 100)}%` }}
                ></div>
              </div>
            </div>
            
            {/* Holder Count */}
            <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
              <div className="flex justify-between mb-1">
                <span className="text-gray-400 text-xs">HOLDERS:</span>
                <span className="text-cyan-300 text-xs">{risk.holders_count}</span>
              </div>
              <div className="w-full bg-gray-800 h-2 rounded-sm overflow-hidden">
                <div 
                  className={`h-full ${getProgressColor(Math.min(risk.holders_count / 200 * 100, 100))}`} 
                  style={{ width: `${Math.min(risk.holders_count / 200 * 100, 100)}%` }}
                ></div>
              </div>
            </div>
            
            {/* Token Age */}
            <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
              <div className="flex justify-between mb-1">
                <span className="text-gray-400 text-xs">TOKEN_AGE:</span>
                <span className="text-cyan-300 text-xs">{risk.age_hours.toFixed(1)} hours</span>
              </div>
              <div className="w-full bg-gray-800 h-2 rounded-sm overflow-hidden">
                <div 
                  className={`h-full ${getProgressColor(Math.min(risk.age_hours / 168 * 100, 100))}`} 
                  style={{ width: `${Math.min(risk.age_hours / 168 * 100, 100)}%` }}
                ></div>
              </div>
            </div>
          </div>
          
          {/* Right Column */}
          <div className="space-y-3">
            {/* Top Holder Concentration */}
            <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
              <div className="flex justify-between mb-1">
                <span className="text-gray-400 text-xs">HOLDER_CONCENTRATION:</span>
                <span className="text-cyan-300 text-xs">{risk.top_holders_concentration}%</span>
              </div>
              <div className="w-full bg-gray-800 h-2 rounded-sm overflow-hidden">
                <div 
                  className={`h-full ${getProgressColor(100 - risk.top_holders_concentration)}`} 
                  style={{ width: `${risk.top_holders_concentration}%` }}
                ></div>
              </div>
            </div>
            
            {/* Liquidity Locked */}
            <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
              <div className="flex justify-between mb-1">
                <span className="text-gray-400 text-xs">LIQUIDITY_LOCKED:</span>
                <span className="text-cyan-300 text-xs">${risk.liquidity_locked.toLocaleString()}</span>
              </div>
              <div className="w-full bg-gray-800 h-2 rounded-sm overflow-hidden">
                <div 
                  className={`h-full ${getProgressColor(Math.min(risk.liquidity_locked / risk.liquidity_usd * 100, 100))}`} 
                  style={{ width: `${Math.min(risk.liquidity_locked / risk.liquidity_usd * 100, 100)}%` }}
                ></div>
              </div>
            </div>
            
            {/* Max Tax */}
            <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
              <div className="flex justify-between mb-1">
                <span className="text-gray-400 text-xs">MAX_TAX:</span>
                <span className="text-cyan-300 text-xs">{risk.max_tax}%</span>
              </div>
              <div className="w-full bg-gray-800 h-2 rounded-sm overflow-hidden">
                <div 
                  className={`h-full ${getProgressColor(100 - risk.max_tax * 5, true)}`} 
                  style={{ width: `${Math.min(risk.max_tax * 5, 100)}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Security Checks */}
        <div className="bg-black/60 border border-purple-500/30 p-3 rounded mb-4">
          <div className="text-gray-400 text-xs mb-2 font-vcr">SECURITY_CHECKS</div>
          <div className="space-y-2 text-xs">
            {risk.assessments && Object.entries(risk.assessments).map(([key, assessment], index) => (
              <div key={index} className="flex items-center">
                <div className={`w-5 text-center ${getResultColor(assessment.result)}`}>
                  {getResultIcon(assessment.result)}
                </div>
                <div className="text-white flex-1">{key.toUpperCase()}</div>
                <div className={`text-right ${getResultColor(assessment.result)}`}>
                  {assessment.details}
                </div>
              </div>
            ))}
            
            {/* Extra security checks that might not be in assessments */}
            <div className="flex items-center">
              <div className={`w-5 text-center ${risk.contract_verification ? 'text-green-400' : 'text-red-400'}`}>
                {risk.contract_verification ? '✓' : '✗'}
              </div>
              <div className="text-white flex-1">CONTRACT_VERIFICATION</div>
              <div className={`text-right ${risk.contract_verification ? 'text-green-400' : 'text-red-400'}`}>
                {risk.contract_verification ? 'Verified' : 'Unverified'}
              </div>
            </div>
            
            <div className="flex items-center">
              <div className={`w-5 text-center ${!risk.honeypot_risk ? 'text-green-400' : 'text-red-400'}`}>
                {!risk.honeypot_risk ? '✓' : '✗'}
              </div>
              <div className="text-white flex-1">HONEYPOT_CHECK</div>
              <div className={`text-right ${!risk.honeypot_risk ? 'text-green-400' : 'text-red-400'}`}>
                {!risk.honeypot_risk ? 'Not a honeypot' : 'Possible honeypot'}
              </div>
            </div>
          </div>
        </div>
        
        {/* Risk Reason */}
        <div className="bg-black/60 border border-purple-500/30 p-3 rounded">
          <div className="text-gray-400 text-xs mb-1 font-vcr">SUMMARY</div>
          <div className={`text-sm ${getRiskColor()} font-mono terminal-text`}>
            {risk.risk_reason || "No specific risk factors identified."}
          </div>
        </div>
        
        {/* Terminal Line */}
        <div className="mt-3 flex items-center text-green-400 font-mono text-sm">
          <span className="mr-2">$</span>
          <span className="animate-pulse">_</span>
        </div>
      </div>
    </div>
  );
};

export default RiskAssessment;

// CSS animations to add to your stylesheet
// @keyframes glitch-horizontal {
//   0% {
//     -webkit-clip-path: polygon(0% 0%, 100% 0%, 100% 35%, 0% 35%, 0% 50%, 100% 50%, 100% 65%, 0% 65%, 0% 85%, 100% 85%, 100% 100%, 0% 100%);
//     clip-path: polygon(0% 0%, 100% 0%, 100% 35%, 0% 35%, 0% 50%, 100% 50%, 100% 65%, 0% 65%, 0% 85%, 100% 85%, 100% 100%, 0% 100%);
//   }
//   50% {
//     -webkit-clip-path: polygon(0% 15%, 100% 15%, 100% 40%, 0% 40%, 0% 55%, 100% 55%, 100% 70%, 0% 70%, 0% 85%, 100% 85%, 100% 90%, 0% 90%);
//     clip-path: polygon(0% 15%, 100% 15%, 100% 40%, 0% 40%, 0% 55%, 100% 55%, 100% 70%, 0% 70%, 0% 85%, 100% 85%, 100% 90%, 0% 90%);
//   }
//   100% {
//     -webkit-clip-path: polygon(0% 0%, 100% 0%, 100% 35%, 0% 35%, 0% 50%, 100% 50%, 100% 65%, 0% 65%, 0% 85%, 100% 85%, 100% 100%, 0% 100%);
//     clip-path: polygon(0% 0%, 100% 0%, 100% 35%, 0% 35%, 0% 50%, 100% 50%, 100% 65%, 0% 65%, 0% 85%, 100% 85%, 100% 100%, 0% 100%);
//   }
// }