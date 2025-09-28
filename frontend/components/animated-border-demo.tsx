"use client"

interface AnimatedBorderDemoProps {
  className?: string
}

export function AnimatedBorderDemo({ className = "" }: AnimatedBorderDemoProps) {
  return (
    <div className={`flex flex-col sm:flex-row gap-6 items-center justify-center ${className}`}>
      {/* Standard Border */}
      <div className="animated-border rounded-xl p-6 bg-slate-900/50 backdrop-blur-sm">
        <h3 className="text-white font-medium mb-2">Standard</h3>
        <p className="text-slate-300 text-sm">4s animation cycle</p>
      </div>

      {/* Premium Border */}
      <div className="animated-border-premium rounded-xl p-6 bg-white/5 backdrop-blur-sm">
        <h3 className="text-white font-medium mb-2">Premium</h3>
        <p className="text-slate-300 text-sm">6s animation cycle</p>
      </div>

      {/* Subtle Border */}
      <div className="animated-border-subtle rounded-xl p-6 bg-slate-800/50 backdrop-blur-sm">
        <h3 className="text-white font-medium mb-2">Subtle</h3>
        <p className="text-slate-300 text-sm">8s animation cycle</p>
      </div>
    </div>
  )
}
