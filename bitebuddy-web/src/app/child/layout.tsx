import MobileSimulator from '@/components/MobileSimulator'
import React from 'react'

export default function ChildLayout({ children }: { children: React.ReactNode }) {
  return (
    <MobileSimulator role="child">
      {children}
    </MobileSimulator>
  )
}
