import React from 'react';

interface NewsLensLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showText?: boolean;
  showTagline?: boolean;
  variant?: 'dark' | 'light';
  className?: string;
}

export const NewsLensLogo: React.FC<NewsLensLogoProps> = ({
  size = 'md',
  showText = true,
  showTagline = true,
  variant = 'dark',
  className = '',
}) => {
  const pixelDimensions = {
    sm: { icon: 32, textClass: 'text-base', subClass: 'text-[9px]', indiaH: 14 },
    md: { icon: 42, textClass: 'text-lg', subClass: 'text-[11px]', indiaH: 16 },
    lg: { icon: 52, textClass: 'text-xl', subClass: 'text-xs', indiaH: 18 },
    xl: { icon: 64, textClass: 'text-2xl', subClass: 'text-sm', indiaH: 20 },
  }[size];

  const textColor = variant === 'dark' ? 'text-white' : 'text-[#0F172A]';
  const taglineColor = variant === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]';

  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* Precision Lens / Prism Emblem SVG */}
      <svg
        width={pixelDimensions.icon}
        height={pixelDimensions.icon}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 transition-transform duration-300 hover:scale-105"
      >
        <defs>
          <linearGradient id="logo-saffron" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFA133" />
            <stop offset="100%" stopColor="#EA580C" />
          </linearGradient>
          <linearGradient id="logo-cobalt" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#38BDF8" />
            <stop offset="50%" stopColor="#2563EB" />
            <stop offset="100%" stopColor="#1D4ED8" />
          </linearGradient>
          <linearGradient id="logo-emerald" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#34D399" />
            <stop offset="100%" stopColor="#059669" />
          </linearGradient>
          <radialGradient id="logo-iris" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.9" />
            <stop offset="70%" stopColor="#1E3A8A" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#0B132B" stopOpacity="1" />
          </radialGradient>
          <filter id="logo-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Outer Precision Barrel Ring with Ticks */}
        <circle
          cx="32"
          cy="32"
          r="27"
          stroke="#38BDF8"
          strokeWidth="1.8"
          strokeDasharray="4 2.5"
          opacity="0.85"
        />
        <circle cx="32" cy="32" r="23" stroke="#1E40AF" strokeWidth="1.2" opacity="0.6" />

        {/* Iris Base */}
        <circle cx="32" cy="32" r="19" fill="url(#logo-iris)" />

        {/* Aperture Refraction Facets (Tricolor + Optical Cyan) */}
        {/* Top Saffron Blade */}
        <path d="M 32 13 C 39 13, 44 17, 47 23 L 38 29 C 36 26, 34 23, 32 13 Z" fill="url(#logo-saffron)" />
        {/* Upper Right Cobalt Blade */}
        <path d="M 47 23 C 51 28, 51 35, 48 41 L 39 35 C 40 33, 40 30, 38 29 Z" fill="url(#logo-cobalt)" />
        {/* Lower Emerald Green Blade */}
        <path d="M 48 41 C 44 47, 38 51, 31 51 L 32 41 C 35 41, 37 38, 39 35 Z" fill="url(#logo-emerald)" />
        {/* Bottom Left Cyan Blade */}
        <path d="M 31 51 C 24 51, 19 46, 17 40 L 27 35 C 28 38, 30 41, 32 41 Z" fill="#0284C7" />
        {/* Upper Left Azure Blade */}
        <path d="M 17 40 C 13 34, 15 27, 18 22 L 27 29 C 26 31, 26 33, 27 35 Z" fill="#3B82F6" />
        {/* Top Left Saffron Accent */}
        <path d="M 18 22 C 23 16, 28 13, 32 13 L 32 24 C 29 24, 27 27, 27 29 Z" fill="#FB923C" />

        {/* Central Pupil / Crosshair Target */}
        <circle cx="32" cy="32" r="6.5" fill="#070D1E" stroke="#38BDF8" strokeWidth="1.6" />
        <circle cx="32" cy="32" r="2.8" fill="#38BDF8" filter="url(#logo-glow)" />

        {/* Precision Crosshair Marks */}
        <line x1="32" y1="18" x2="32" y2="22" stroke="#38BDF8" strokeWidth="1.4" strokeLinecap="round" />
        <line x1="32" y1="42" x2="32" y2="46" stroke="#38BDF8" strokeWidth="1.4" strokeLinecap="round" />
        <line x1="18" y1="32" x2="22" y2="32" stroke="#38BDF8" strokeWidth="1.4" strokeLinecap="round" />
        <line x1="42" y1="32" x2="46" y2="32" stroke="#38BDF8" strokeWidth="1.4" strokeLinecap="round" />
      </svg>

      {/* Typography Lockup */}
      {showText && (
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span
              className={`font-serif font-bold tracking-tight leading-none ${pixelDimensions.textClass} ${textColor}`}
            >
              News<span className="font-sans font-extrabold text-[#38BDF8]">Lens</span>
            </span>

            {/* India Badge with Tricolor Markers */}
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#1E293B]/90 border border-white/10 text-[9px] font-mono font-bold tracking-widest text-[#F8FAFC]">
              INDIA
              <span className="inline-flex items-center gap-0.5 ml-0.5">
                <span className="w-1 h-1 rounded-full bg-[#FF9933]"></span>
                <span className="w-1 h-1 rounded-full bg-white"></span>
                <span className="w-1 h-1 rounded-full bg-[#138808]"></span>
              </span>
            </span>
          </div>

          {showTagline && (
            <p className={`mt-1 font-sans ${pixelDimensions.subClass} ${taglineColor} leading-none font-medium`}>
              See coverage. Examine evidence.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default NewsLensLogo;
