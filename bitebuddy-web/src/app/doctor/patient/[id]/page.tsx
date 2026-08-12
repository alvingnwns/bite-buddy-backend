'use client';

import React, { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { supabase } from '@/lib/supabase'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1'

export default function PatientDetail() {
  const router = useRouter()
  const params = useParams()
  const patientId = params.id as string

  const [doctor, setDoctor] = useState<any>(null)
  const [patient, setPatient] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Form state
  const [weight, setWeight] = useState(30)
  const [height, setHeight] = useState(130)
  const [diabetesType, setDiabetesType] = useState('type1')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      router.push('/')
      return
    }
    setDoctor(session.user)

    try {
      // In a real app we'd fetch patient details from GET /users/{id}
      // For now we just mock the patient name or use an endpoint if available
      // Let's assume we can fetch patients of the doctor again and find the match
      const res = await fetch(`${API_URL}/users/${session.user.id}/patients`)
      if (res.ok) {
        const patients = await res.json()
        const found = patients.find((p: any) => p.id === patientId)
        if (found) setPatient(found)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    
    try {
      const payload = {
        child_id: patientId,
        recorded_by: doctor.id,
        height_cm: height,
        weight_kg: weight,
        diabetes_type: diabetesType
      }
      
      const res = await fetch(`${API_URL}/clinical/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      
      if (res.ok) {
        const result = await res.json()
        alert(`Clinical parameters saved!
Target Calories: ${result.target_daily_calories} kcal
Target Carbs: ${result.target_daily_carbs} g
Max Sugar Intake: ${result.max_sugar_intake_g} g`)
        router.push('/doctor')
      } else {
        const err = await res.json()
        alert('Failed to save: ' + JSON.stringify(err))
      }
    } catch(e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="p-8">Loading...</div>

  return (
    <div className="p-8 bg-gray-50 min-h-screen text-gray-900">
      <button onClick={() => router.back()} className="text-indigo-600 mb-6 font-medium">← Back to Patient List</button>
      
      <h1 className="text-2xl font-bold mb-1">Patient Details</h1>
      <p className="text-gray-500 mb-8">{patient?.full_name || 'Patient'} ({patient?.email})</p>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 max-w-2xl">
        <h2 className="text-lg font-bold mb-4 border-b pb-2">Clinical Parameters</h2>
        <form onSubmit={handleSave} className="space-y-4">
          
          <div className="flex space-x-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Weight (kg)</label>
              <input 
                type="number" 
                value={weight} 
                onChange={(e) => setWeight(parseFloat(e.target.value))}
                className="w-full border rounded-lg p-2" 
                required 
                min="1" max="300" 
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Height (cm)</label>
              <input 
                type="number" 
                value={height} 
                onChange={(e) => setHeight(parseFloat(e.target.value))}
                className="w-full border rounded-lg p-2" 
                required 
                min="20" max="250" 
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Diabetes Type</label>
            <select 
              value={diabetesType} 
              onChange={(e) => setDiabetesType(e.target.value)}
              className="w-full border rounded-lg p-2"
            >
              <option value="type1">Type 1</option>
              <option value="type2">Type 2</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">System will auto-calculate target calories and max sugar based on this.</p>
          </div>

          <div className="pt-4">
            <button 
              type="submit" 
              disabled={saving}
              className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save & Calculate Plan'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
