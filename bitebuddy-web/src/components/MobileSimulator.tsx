import React from 'react'

export default function MobileSimulator({ children, role }: { children: React.ReactNode, role: 'child' | 'parent' }) {
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      {/* Mobile Device Frame */}
      <div className="relative w-full max-w-[400px] h-[850px] max-h-[90vh] bg-black rounded-[3rem] overflow-hidden border-[8px] border-gray-800 shadow-2xl flex flex-col">
        {/* Notch simulation */}
        <div className="absolute top-0 inset-x-0 h-6 flex justify-center z-50">
          <div className="w-32 h-6 bg-gray-800 rounded-b-2xl"></div>
        </div>

        {/* Header Indicator */}
        <div className="absolute top-8 w-full text-center z-50 pointer-events-none">
          <span className="bg-gray-800/80 text-white text-xs px-3 py-1 rounded-full uppercase tracking-wider font-semibold">
            {role} View
          </span>
        </div>

        {/* Content Area */}
        <div className="flex-1 bg-white overflow-y-auto overflow-x-hidden pt-8 relative">
          {children}
        </div>
      </div>
    </div>
  )
}
