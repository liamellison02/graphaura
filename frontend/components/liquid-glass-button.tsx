"use client"

import { useState } from 'react'

interface LiquidGlassButtonProps {
  children: React.ReactNode
  onClick?: () => void
  className?: string
}

export function LiquidGlassButton({ children, onClick, className = "" }: LiquidGlassButtonProps) {
  const [isHovered, setIsHovered] = useState(false)
  const [isPressed, setIsPressed] = useState(false)

  const handleClick = () => {
    if (onClick) {
      onClick()
    } else {
      console.log('GraphAura button clicked!')
    }
  }

  return (
    <button
      className={`
        relative overflow-hidden
        px-6 py-3 
        backdrop-blur-md 
        bg-white/10 
        animated-border-subtle
        rounded-xl
        text-white font-medium text-base
        transition-all duration-300 ease-out
        hover:bg-white/15
        hover:shadow-2xl hover:shadow-blue-500/20
        active:scale-95
        group
        ${className}
      `}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onMouseDown={() => setIsPressed(true)}
      onMouseUp={() => setIsPressed(false)}
      onClick={handleClick}
    >
      {/* Liquid animation background */}
      <div 
        className={`
          absolute inset-0 -z-10
          bg-gradient-to-r from-blue-400/20 via-purple-400/20 to-cyan-400/20
          transition-all duration-500 ease-out
          ${isHovered ? 'scale-110 rotate-12' : 'scale-100 rotate-0'}
          ${isPressed ? 'scale-95' : ''}
        `}
        style={{
          background: isHovered 
            ? 'radial-gradient(circle at center, rgba(59, 130, 246, 0.3) 0%, rgba(147, 51, 234, 0.2) 50%, rgba(6, 182, 212, 0.3) 100%)'
            : 'radial-gradient(circle at center, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.1) 50%, rgba(6, 182, 212, 0.1) 100%)'
        }}
      />
      
      {/* Liquid blob animations */}
      <div className="absolute inset-0 overflow-hidden rounded-2xl">
        <div 
          className={`
            absolute w-32 h-32 -top-16 -left-16
            bg-gradient-to-br from-blue-400/30 to-transparent
            rounded-full
            transition-all duration-700 ease-out
            ${isHovered ? 'scale-150 translate-x-8 translate-y-8' : 'scale-100'}
          `}
        />
        <div 
          className={`
            absolute w-24 h-24 -bottom-12 -right-12
            bg-gradient-to-tl from-purple-400/30 to-transparent
            rounded-full
            transition-all duration-500 ease-out delay-100
            ${isHovered ? 'scale-125 -translate-x-4 -translate-y-4' : 'scale-100'}
          `}
        />
      </div>
      
      {/* Shimmer effect */}
      <div 
        className={`
          absolute inset-0
          bg-gradient-to-r from-transparent via-white/10 to-transparent
          -translate-x-full
          transition-transform duration-1000 ease-out
          ${isHovered ? 'translate-x-full' : '-translate-x-full'}
        `}
      />
      
      {/* Button content */}
      <span className="relative z-10 flex items-center justify-center gap-2">
        {children}
      </span>
    </button>
  )
}
