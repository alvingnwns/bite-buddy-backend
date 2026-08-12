import MobileSimulator from '@/components/MobileSimulator'
import React from 'react'

export default function ParentLayout({ children }: { children: React.ReactNode }) {
  return (
    <MobileSimulator role="parent">
      {children}
    </MobileSimulator>
  )
}
