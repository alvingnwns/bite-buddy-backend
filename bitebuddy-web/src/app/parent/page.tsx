'use client';

import React, { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1'

export default function ParentDashboard() {
  const router = useRouter()
  const [parent, setParent] = useState<any>(null)
  const [children, setChildren] = useState<any[]>([])
  const [selectedChild, setSelectedChild] = useState<any>(null)
  const [pet, setPet] = useState<any>(null)
  const [schedules, setSchedules] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  // New Schedule form state
  const [showAddForm, setShowAddForm] = useState(false)
  const [mealType, setMealType] = useState('breakfast')
  const [startTime, setStartTime] = useState('07:00:00')
  const [endTime, setEndTime] = useState('08:00:00')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      router.push('/')
      return
    }
    setParent(session.user)
    
    try {
      // Fetch children
      const resChild = await fetch(`${API_URL}/users/${session.user.id}/children`)
      if (resChild.ok) {
        const childData = await resChild.json()
        setChildren(childData)
        if (childData.length > 0) {
          const firstChild = childData[0]
          setSelectedChild(firstChild)
          fetchChildData(firstChild.id)
        }
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const fetchChildData = async (childId: string) => {
    try {
      // Fetch pet
      const resPet = await fetch(`${API_URL}/pets/${childId}`)
      if (resPet.ok) setPet(await resPet.json())
      
      // Fetch schedules
      const resSched = await fetch(`${API_URL}/schedules/${childId}`)
      if (resSched.ok) setSchedules(await resSched.json())
    } catch (e) {
      console.error(e)
    }
  }

  const handleAddSchedule = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedChild) return
    
    // Create today's date for start/end date
    const today = new Date().toISOString().split('T')[0]
    
    const payload = {
      child_id: selectedChild.id,
      meal_type: mealType,
      start_time: `${today}T${startTime}Z`,
      end_time: `${today}T${endTime}Z`,
      start_date: today,
      is_active: true
    }
    
    try {
      const res = await fetch(`${API_URL}/schedules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (res.ok) {
        setShowAddForm(false)
        fetchChildData(selectedChild.id)
      } else {
        alert('Failed to add schedule')
      }
    } catch(e) {
      console.error(e)
    }
  }

  if (loading) return <div className="p-6 text-center">Loading...</div>

  return (
    <div className="p-6 pb-24 text-gray-900">
      <h1 className="text-2xl font-bold mb-1">Parent Dashboard</h1>
      <p className="text-gray-500 text-sm mb-6">Monitoring: {selectedChild?.full_name || 'No child selected'}</p>
      
      {!selectedChild ? (
        <div className="bg-yellow-50 text-yellow-800 p-4 rounded-xl text-sm">
          You don't have any children assigned to your account. Please create a child account and set its parent_id to your ID.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Pet Status */}
          <div className="bg-blue-50 p-4 rounded-xl border border-blue-100 shadow-sm">
            <h2 className="font-semibold text-blue-800 mb-2">Virtual Pet Status</h2>
            {pet ? (
              <div className="flex justify-between items-center bg-white p-3 rounded-lg">
                <div>
                  <p className="font-bold">{pet.pet_name} (Lvl {pet.level})</p>
                  <p className="text-xs text-gray-500 capitalize">Status: {pet.current_status}</p>
                </div>
                <div className="text-right text-sm">
                  <p className="text-red-500 font-bold">HP: {pet.happiness}/100</p>
                  <p className="text-blue-500 font-bold">XP: {pet.experience_points}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500">No pet data available.</p>
            )}
          </div>
          
          {/* Schedules */}
          <div className="bg-white shadow-sm p-4 rounded-xl border border-gray-100">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-semibold text-gray-800">Schedules</h2>
              <button 
                onClick={() => setShowAddForm(!showAddForm)}
                className="bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full text-xs font-bold"
              >
                {showAddForm ? 'Cancel' : '+ Add'}
              </button>
            </div>
            
            {showAddForm && (
              <form onSubmit={handleAddSchedule} className="bg-gray-50 p-3 rounded-lg mb-4 space-y-3 text-sm">
                <div>
                  <label className="block text-gray-700 text-xs mb-1">Meal Type</label>
                  <select value={mealType} onChange={e => setMealType(e.target.value)} className="w-full border rounded p-2">
                    <option value="breakfast">Breakfast</option>
                    <option value="lunch">Lunch</option>
                    <option value="dinner">Dinner</option>
                    <option value="snack">Snack</option>
                  </select>
                </div>
                <div className="flex space-x-2">
                  <div className="flex-1">
                    <label className="block text-gray-700 text-xs mb-1">Start Time</label>
                    <input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} className="w-full border rounded p-2" required />
                  </div>
                  <div className="flex-1">
                    <label className="block text-gray-700 text-xs mb-1">End Time</label>
                    <input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} className="w-full border rounded p-2" required />
                  </div>
                </div>
                <button type="submit" className="w-full bg-indigo-600 text-white py-2 rounded-lg font-medium">Save Schedule</button>
              </form>
            )}

            <div className="space-y-2">
              {schedules.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-2">No schedules set.</p>
              ) : (
                schedules.map((s, idx) => (
                  <div key={idx} className="flex justify-between items-center p-3 border rounded-lg">
                    <div>
                      <p className="font-bold text-sm capitalize">{s.meal_type}</p>
                      <p className="text-xs text-gray-500">
                        {new Date(s.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} - 
                        {new Date(s.end_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </p>
                    </div>
                    <div className="px-2 py-1 bg-gray-100 rounded text-xs font-semibold">
                      {s.is_active ? 'Active' : 'Inactive'}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
