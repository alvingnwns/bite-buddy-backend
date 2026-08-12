import React from 'react'

export default function DoctorLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-indigo-900 text-white flex flex-col">
        <div className="p-4 text-xl font-bold border-b border-indigo-800">
          Doctor Dashboard
        </div>
        <div className="flex-1 p-4 space-y-2">
          <a href="#" className="block p-2 bg-indigo-800 rounded">Patients List</a>
          <a href="#" className="block p-2 hover:bg-indigo-800 rounded">Alerts</a>
          <a href="#" className="block p-2 hover:bg-indigo-800 rounded">Settings</a>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {children}
      </div>
    </div>
  )
}
