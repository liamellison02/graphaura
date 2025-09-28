"use client"

import { useEffect, useState } from 'react'

export function AnimatedCircles({ className = "" }: { className?: string }) {
  const [isVisible, setIsVisible] = useState(true)

  return (
    <div className={`relative ${className}`}>
      <svg 
        width="100" 
        height="100" 
        viewBox="0 0 400 400" 
        xmlns="http://www.w3.org/2000/svg"
        className={`transition-opacity duration-1000 ${isVisible ? 'opacity-100' : 'opacity-0'}`}
      >
        <defs>
          <radialGradient id="blueGradient1" cx="0.3" cy="0.3" r="0.8">
            <stop offset="0%" style={{stopColor:'#87CEEB', stopOpacity:1}} />
            <stop offset="100%" style={{stopColor:'#4682B4', stopOpacity:1}} />
          </radialGradient>
          
          <radialGradient id="blueGradient2" cx="0.3" cy="0.3" r="0.8">
            <stop offset="0%" style={{stopColor:'#6495ED', stopOpacity:1}} />
            <stop offset="100%" style={{stopColor:'#4169E1', stopOpacity:1}} />
          </radialGradient>
          
          <radialGradient id="purpleGradient1" cx="0.3" cy="0.3" r="0.8">
            <stop offset="0%" style={{stopColor:'#DDA0DD', stopOpacity:1}} />
            <stop offset="100%" style={{stopColor:'#9370DB', stopOpacity:1}} />
          </radialGradient>
          
          <radialGradient id="purpleGradient2" cx="0.3" cy="0.3" r="0.8">
            <stop offset="0%" style={{stopColor:'#BA55D3', stopOpacity:1}} />
            <stop offset="100%" style={{stopColor:'#8A2BE2', stopOpacity:1}} />
          </radialGradient>

          {/* glow thing */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        <circle cx="120" cy="120" r="80" fill="url(#blueGradient1)" filter="url(#glow)">
          <animateTransform
            attributeName="transform"
            attributeType="XML"
            type="translate"
            values="0,0; 5,3; 0,0; -3,5; 0,0"
            dur="8s"
            repeatCount="indefinite"/>
          <animate
            attributeName="r"
            values="80; 85; 80; 78; 80"
            dur="6s"
            repeatCount="indefinite"/>
          <animate
            attributeName="opacity"
            values="0.8; 1; 0.8; 0.9; 0.8"
            dur="4s"
            repeatCount="indefinite"/>
        </circle>
        
        <circle cx="280" cy="140" r="55" fill="url(#purpleGradient1)" filter="url(#glow)">
          <animateTransform
            attributeName="transform"
            attributeType="XML"
            type="translate"
            values="0,0; -4,2; 0,0; 3,-4; 0,0"
            dur="7s"
            repeatCount="indefinite"/>
          <animate
            attributeName="r"
            values="55; 58; 55; 52; 55"
            dur="5s"
            repeatCount="indefinite"/>
          <animate
            attributeName="opacity"
            values="0.7; 0.9; 0.7; 1; 0.7"
            dur="6s"
            repeatCount="indefinite"/>
        </circle>
        
        <circle cx="80" cy="220" r="35" fill="url(#blueGradient2)" filter="url(#glow)">
          <animateTransform
            attributeName="transform"
            attributeType="XML"
            type="translate"
            values="0,0; 3,-2; 0,0; -2,4; 0,0"
            dur="9s"
            repeatCount="indefinite"/>
          <animate
            attributeName="r"
            values="35; 38; 35; 33; 35"
            dur="4s"
            repeatCount="indefinite"/>
          <animate
            attributeName="opacity"
            values="0.9; 0.7; 0.9; 0.8; 0.9"
            dur="3s"
            repeatCount="indefinite"/>
        </circle>
        
        <circle cx="150" cy="290" r="50" fill="url(#purpleGradient2)" filter="url(#glow)">
          <animateTransform
            attributeName="transform"
            attributeType="XML"
            type="translate"
            values="0,0; -3,4; 0,0; 4,-2; 0,0"
            dur="6s"
            repeatCount="indefinite"/>
          <animate
            attributeName="r"
            values="50; 53; 50; 47; 50"
            dur="7s"
            repeatCount="indefinite"/>
          <animate
            attributeName="opacity"
            values="0.8; 1; 0.8; 0.7; 0.8"
            dur="5s"
            repeatCount="indefinite"/>
        </circle>
        
        <circle cx="320" cy="280" r="75" fill="url(#blueGradient2)" filter="url(#glow)">
          <animateTransform
            attributeName="transform"
            attributeType="XML"
            type="translate"
            values="0,0; 2,-5; 0,0; -4,3; 0,0"
            dur="10s"
            repeatCount="indefinite"/>
          <animate
            attributeName="r"
            values="75; 78; 75; 72; 75"
            dur="8s"
            repeatCount="indefinite"/>
          <animate
            attributeName="opacity"
            values="0.7; 0.9; 0.7; 1; 0.7"
            dur="7s"
            repeatCount="indefinite"/>
        </circle>
      </svg>
    </div>
  )
}
