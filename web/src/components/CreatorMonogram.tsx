import React from 'react'
import { getCreatorMonogram } from '../utils/formatters'

interface MonogramProps {
  name: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export const CreatorMonogram: React.FC<MonogramProps> = ({
  name,
  size = 'md',
  className = '',
}) => {
  const { initials, hue } = getCreatorMonogram(name)

  const sizeStyles = {
    sm: {
      dimension: 36,
      fontSize: '0.85rem',
      borderWidth: '1px',
    },
    md: {
      dimension: 48,
      fontSize: '1.05rem',
      borderWidth: '1.5px',
    },
    lg: {
      dimension: 72,
      fontSize: '1.5rem',
      borderWidth: '2px',
    },
    xl: {
      dimension: 96,
      fontSize: '2.1rem',
      borderWidth: '2px',
    },
  }[size]

  // Harmonious deep tones: low saturation, dignified value
  // Uses hue from hash with low saturation (12-18%) and deep luminosity (16-24%)
  const bg = `hsl(${hue}, 16%, 20%)`
  const goldTone = `hsl(${hue}, 35%, 72%)`

  return (
    <div
      className={`monogram-seal ${className}`}
      style={{
        width: sizeStyles.dimension,
        height: sizeStyles.dimension,
        minWidth: sizeStyles.dimension,
        minHeight: sizeStyles.dimension,
        borderRadius: size === 'xl' ? '18px' : size === 'lg' ? '14px' : '10px',
        backgroundColor: bg,
        border: `${sizeStyles.borderWidth} solid rgba(213, 208, 197, 0.4)`,
        boxShadow: 'inset 0 1px 2px rgba(255, 255, 255, 0.08), 0 2px 5px rgba(26, 34, 31, 0.12)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#FBFAF7',
        fontFamily: "'Cormorant Garamond', 'Noto Sans Thai', Georgia, serif",
        fontWeight: 600,
        fontSize: sizeStyles.fontSize,
        position: 'relative',
        userSelect: 'none',
        overflow: 'hidden',
      }}
      aria-hidden="true"
    >
      {/* Delicate inner border for an archival bookplate / seal feel */}
      <div
        style={{
          position: 'absolute',
          inset: size === 'sm' ? '2px' : '3px',
          border: '1px solid rgba(233, 222, 199, 0.22)',
          borderRadius: size === 'xl' ? '14px' : size === 'lg' ? '11px' : '7px',
          pointerEvents: 'none',
        }}
      />
      <span
        style={{
          color: goldTone,
          letterSpacing: '0.02em',
          transform: 'translateY(-1px)',
        }}
      >
        {initials}
      </span>
    </div>
  )
}
