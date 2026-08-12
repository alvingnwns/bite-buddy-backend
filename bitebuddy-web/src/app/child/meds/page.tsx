'use client';

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1'

export default function MedsPage() {
  const router = useRouter()
  const [imageUri, setImageUri] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [fileObj, setFileObj] = useState<File | null>(null)

  const [dosage, setDosage] = useState<string>('1')
  const [dosageUnit, setDosageUnit] = useState<string>('pill')

  const handleCapture = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setFileObj(file)
      setImageUri(URL.createObjectURL(file))
    }
  }

  const uploadImage = async () => {
    if (!fileObj || !imageUri) return
    setLoading(true)
    
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return router.push('/')
      const token = session.access_token
      
      const formData = new FormData()
      formData.append('file', fileObj)
      formData.append('child_id', session.user.id)
      formData.append('administered_by', session.user.id)
      formData.append('dosage', dosage)
      formData.append('dosage_unit', dosageUnit)
      formData.append('route', dosageUnit === 'pill' ? 'oral' : 'subcutaneous')

      const response = await fetch(`${API_URL}/scan/medicine`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      if (!response.ok) {
        let errorMsg = 'Gagal mendeteksi obat.'
        try {
          const errRes = await response.json()
          if (errRes.detail) errorMsg = errRes.detail
        } catch(e) {}
        throw new Error(errorMsg)
      }
      
      const result = await response.json()
      
      alert(`Berhasil mencatat obat: ${result.data?.medication_detected} (${dosage} ${dosageUnit})`)
      router.push('/child')
    } catch (error: any) {
      console.log(error)
      alert(error.message || 'Gagal mendeteksi obat.')
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-[#F3FEF8] relative font-sans overflow-hidden text-[#0C3638]">
      {/* Top Header Background */}
      <div className="bg-[#5282BB] w-full h-[40%] absolute top-0 rounded-b-[40px] z-0"></div>

      {/* Header Content */}
      <div className="relative z-10 flex flex-col p-6 pt-10">
        <button onClick={() => router.back()} className="w-10 h-10 bg-[#E03B38] text-white rounded-lg flex items-center justify-center font-bold text-xl shadow mb-4">
          {'<'}
        </button>
        
        {/* Schedule Card Inline */}
        <div className="bg-white rounded-xl w-full p-4 shadow-lg mb-6">
          <h2 className="text-lg font-bold text-[#0C3638] mb-2">Today's Schedule</h2>
          <div className="flex flex-row items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-5 h-5 bg-[#D9ECF3] rounded-full"></div>
              <span className="text-sm font-semibold text-gray-700">pills (07:00-08:00)</span>
            </div>
            <div className="px-3 py-1 rounded-full text-white text-xs font-bold bg-[#F59E0B]">
              Not Yet
            </div>
          </div>
        </div>

        <h1 className="text-2xl font-bold text-white text-center mb-8">Take a picture of your pills</h1>
      </div>

      <div className="flex-1 flex flex-col items-center p-6 relative z-10 mt-10">
        {loading ? (
          <div className="flex flex-col items-center text-gray-700">
            <div className="w-16 h-16 border-4 border-[#0C3638] border-t-transparent rounded-full animate-spin mb-4"></div>
            <p className="font-bold">Analyzing medicine...</p>
          </div>
        ) : (
          <>
            <div className="w-64 h-64 bg-[#e6e6e6] rounded-[40px] flex flex-col items-center justify-center mb-8 overflow-hidden relative shadow-lg border-4 border-white">
              {imageUri ? (
                <img src={imageUri} className="w-full h-full object-cover" alt="Meds" />
              ) : (
                <div className="w-full h-full bg-black/10 flex items-center justify-center text-5xl">📷</div>
              )}
              
              <input 
                type="file" 
                accept="image/*" 
                capture="environment" 
                onChange={handleCapture}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
            </div>

            {imageUri && (
              <div className="w-full max-w-xs flex flex-col space-y-4 mb-6">
                <div>
                  <label className="text-sm font-bold text-gray-700 block mb-1">Dosis Obat</label>
                  <input
                    type="number"
                    value={dosage}
                    onChange={(e) => setDosage(e.target.value)}
                    className="w-full px-4 py-2 rounded-xl border-2 border-[#0C3638] bg-white text-gray-800 font-bold outline-none focus:ring-2 focus:ring-[#5282BB]"
                    placeholder="Contoh: 1, 0.5, 10"
                    min="0.1"
                    step="0.1"
                  />
                </div>
                <div>
                  <label className="text-sm font-bold text-gray-700 block mb-1">Satuan</label>
                  <select
                    value={dosageUnit}
                    onChange={(e) => setDosageUnit(e.target.value)}
                    className="w-full px-4 py-2 rounded-xl border-2 border-[#0C3638] bg-white text-gray-800 font-bold outline-none focus:ring-2 focus:ring-[#5282BB]"
                  >
                    <option value="pill">Pill / Tablet</option>
                    <option value="IU">IU (Insulin Unit)</option>
                    <option value="ml">ml (Mililiter)</option>
                    <option value="mg">mg (Miligram)</option>
                  </select>
                </div>
              </div>
            )}

            {imageUri && (
              <div className="flex space-x-4 w-full justify-center">
                <button onClick={() => setImageUri(null)} className="bg-gray-300 text-gray-800 font-bold px-6 py-3 rounded-full">
                  Retake
                </button>
                <button onClick={uploadImage} className="bg-[#0C3638] text-white font-bold px-8 py-3 rounded-full shadow-lg">
                  Confirm
                </button>
              </div>
            )}
            {!imageUri && (
              <button className="bg-[#0C3638] text-white font-bold px-8 py-4 rounded-full shadow-lg flex items-center space-x-2 relative pointer-events-none">
                <span>Confirm Meds!</span>
              </button>
            )}
            
            {!imageUri && (
              <p className="mt-6 text-sm text-gray-500 font-bold underline">Tap the box to open camera/gallery</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
