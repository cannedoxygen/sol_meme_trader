import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import './index.css'

// Add retro console log on startup
console.log(`
%c===============================================
%c█▀▄▀█ █▀▀ █▀▄▀█ █▀▀ █▀▀ █▀█ █ █▄░█   ▀█▀ █▀█ ▄▀█ █▀▄ █▀▀ █▀█
%c█░▀░█ ██▄ █░▀░█ ██▄ █▄▄ █▄█ █ █░▀█   ░█░ █▀▄ █▀█ █▄▀ ██▄ █▀▄
%c===============================================
%cInitializing... System Online
`, 
'color: cyan; font-weight: bold;', 
'color: #ff00ff; font-weight: bold;', 
'color: #ff00ff; font-weight: bold;', 
'color: cyan; font-weight: bold;',
'color: #00ff9f; font-style: italic;'
);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)