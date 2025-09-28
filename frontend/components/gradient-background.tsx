"use client"

export function GradientBackground() {
  return (
    <div className="absolute inset-0 -z-10">
      <div
        className="h-full w-full"
        style={{
          background: `
            radial-gradient(circle at 20% 80%, hsla(193, 85%, 66%, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, hsla(196, 100%, 83%, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 40% 40%, hsla(195, 100%, 50%, 0.2) 0%, transparent 50%),
            linear-gradient(135deg, hsl(0, 0%, 0%) 0%, hsl(210, 20%, 8%) 100%)
          `
        }}
      />
    </div>
  )
}