'use client';

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1'

export default function ChildDashboard() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [pet, setPet] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      router.push('/')
      return
    }
    setUser(session.user)
    
    try {
      const res = await fetch(`${API_URL}/pets/${session.user.id}`)
      if (res.ok) {
        setPet(await res.json())
      } else {
        // Mock fallback if backend fails (e.g., auto-create failed or server off)
        setPet({ health: 100, experience_points: 0, level: 1 })
      }
    } catch (e) {
      console.error(e)
      setPet({ health: 100, experience_points: 0, level: 1 })
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="flex-1 flex justify-center items-center h-full"><p>Loading...</p></div>

  const hp = pet?.happiness ?? 100
  const xp = pet?.experience_points ?? 0
  const level = pet?.level ?? 1

  return (
    <div className="relative flex flex-col h-full bg-[#374A71] overflow-hidden font-sans">
      {/* Background Stripes */}
      <div className="absolute inset-0 z-0 flex flex-row space-x-12 opacity-20">
        <div className="w-[8%] h-full bg-[#1e2a44]"></div>
        <div className="w-[8%] h-full bg-[#1e2a44]"></div>
        <div className="w-[8%] h-full bg-[#1e2a44]"></div>
        <div className="w-[8%] h-full bg-[#1e2a44]"></div>
        <div className="w-[8%] h-full bg-[#1e2a44]"></div>
      </div>

      {/* Floor */}
      <div className="absolute bottom-[120px] left-0 right-0 h-[60px] bg-[#C4A882] z-0"></div>

      {/* Header */}
      <div className="relative z-10 flex justify-between px-6 pt-12">
        <button className="w-14 h-14 bg-[#D9ECF3] border-4 border-[#0C3638] rounded-xl flex items-center justify-center shadow">
          <span className="text-2xl">⚙️</span>
        </button>
        <button className="w-14 h-14 bg-[#D9ECF3] border-4 border-[#0C3638] rounded-xl flex items-center justify-center shadow">
          <span className="text-2xl">🔔</span>
        </button>
      </div>

      {/* Level Badge */}
      <div className="relative z-10 bg-white px-5 py-2 rounded-t-2xl mt-4 self-center shadow">
        <span className="text-[#0C3638] text-xl font-bold">Level {level}</span>
      </div>

      {/* Stats Card */}
      <div className="relative z-10 bg-white w-[90%] self-center rounded-b-2xl rounded-tr-2xl p-5 shadow-lg flex flex-col">
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-bold text-[#0C3638]">HP</span>
          <span className="text-xs text-[#0C3638] font-semibold">{hp}/100</span>
        </div>
        <div className="w-full bg-[#D7E3E5] rounded-full h-3 mb-4">
          <div className="bg-[#E03B38] h-full rounded-full" style={{ width: `${hp}%` }}></div>
        </div>

        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-bold text-[#0C3638]">XP</span>
          <span className="text-xs text-[#0C3638] font-semibold">{xp}/100</span>
        </div>
        <div className="w-full bg-[#D7E3E5] rounded-full h-3">
          <div className="bg-[#41B9F5] h-full rounded-full" style={{ width: `${Math.min(100, xp)}%` }}></div>
        </div>
      </div>

      {/* Streak */}
      <div className="relative z-10 bg-white px-5 py-2 rounded-full self-center mt-6 shadow border-2 border-gray-100 flex items-center space-x-2">
        <span className="text-xl">🔥</span>
        <span className="text-[#0C3638] font-bold">12 Days</span>
      </div>

      {/* Pet Character */}
      <div className="relative z-10 flex-1 flex justify-center items-center pb-20">
        <img src="/pet-happy.png" alt="Pet" className="w-[80%] max-w-[250px] object-contain" />
      </div>

      {/* Bottom Nav */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[90%] bg-[#0C3638] h-24 rounded-full flex flex-row justify-between items-center px-8 z-20 shadow-2xl">
        <button onClick={() => router.push('/child/schedule')} className="flex flex-col items-center group">
          <div className="w-12 h-12 flex items-center justify-center">
            <span className="text-3xl">📅</span>
          </div>
          <span className="text-white text-xs mt-1 font-semibold group-hover:text-blue-300">Schedule</span>
        </button>

        <button onClick={() => router.push('/child/scan')} className="relative -top-8 flex flex-col items-center">
          <div className="w-20 h-20 bg-[#F3FEF8] rounded-full flex flex-col items-center justify-center shadow-lg border-4 border-[#0C3638]">
            <span className="text-3xl">🍲</span>
          </div>
          <span className="text-white text-xs mt-1 font-semibold">Feed</span>
        </button>

        <button onClick={() => router.push('/child/meds')} className="flex flex-col items-center group">
          <div className="w-12 h-12 flex items-center justify-center">
            <span className="text-3xl">💊</span>
          </div>
          <span className="text-white text-xs mt-1 font-semibold group-hover:text-blue-300">Heal</span>
        </button>
      </div>
    </div>
  )
}
