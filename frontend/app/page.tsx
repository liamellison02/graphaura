import { GradientBackground } from "@/components/gradient-background"
import { LiquidGlassButton } from "@/components/liquid-glass-button"
import { Instrument_Serif } from "next/font/google"

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: ["400"],
  display: "swap",
})

export default function Home() {
  return (
    <main className="relative h-screen flex items-center justify-center overflow-hidden">
      <GradientBackground />
      <div className="absolute inset-0 -z-10 bg-black/20" />

        <div className="px-6 text-center">
        <h1
          className={`${instrumentSerif.className} text-white text-center text-balance font-normal tracking-tight text-8xl drop-shadow-lg mb-4`}
        >
          graphaura
        </h1>

        
        <div className="flex justify-center">
          <LiquidGlassButton>
            start reliving
          </LiquidGlassButton>
        </div>
      </div>
    </main>
  )
}
