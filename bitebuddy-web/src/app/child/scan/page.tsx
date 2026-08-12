'use client';

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1'

export default function ScanFood() {
  const router = useRouter()
  const [imageUri, setImageUri] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [fileObj, setFileObj] = useState<File | null>(null)

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
      const token = session?.access_token || ''
      
      const formData = new FormData()
      formData.append('file', fileObj)

      const response = await fetch(`${API_URL}/scan/food/analyze`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      if (!response.ok) {
        let errorMsg = 'Gagal mendeteksi makanan.'
        try {
          const errRes = await response.json()
          if (errRes.detail) errorMsg = errRes.detail
        } catch(e) {}
        throw new Error(errorMsg)
      }
      
      const result = await response.json()

      // Convert ingredients array to string to pass via URL params (NextJS doesn't pass complex objects via router easily, so we can use localStorage or stringify)
      const ingredientsStr = JSON.stringify(result.data.ingredients || [])
      
      router.push(`/child/analysis?imageUri=${encodeURIComponent(result.data.photo_url || imageUri)}&ingredients=${encodeURIComponent(ingredientsStr)}`)
    } catch (error: any) {
      console.log(error)
      alert(error.message || 'Gagal mendeteksi makanan.')
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-[#374A71] relative font-sans overflow-hidden text-white">
      {/* Header */}
      <div className="flex justify-between items-center p-6 z-10">
        <button onClick={() => router.back()} className="text-3xl font-bold">{'<'}</button>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-6 z-10">
        <h1 className="text-2xl font-bold mb-8">Scan Your Food</h1>
        
        {loading ? (
          <div className="flex flex-col items-center">
            <div className="w-16 h-16 border-4 border-white border-t-transparent rounded-full animate-spin mb-4"></div>
            <p className="font-bold">AI is analyzing your food...</p>
          </div>
        ) : (
          <>
            <div className="w-64 h-64 bg-[#1e2a44] rounded-3xl flex items-center justify-center mb-8 overflow-hidden relative border-4 border-dashed border-gray-400">
              {imageUri ? (
                <img src={imageUri} className="w-full h-full object-cover" alt="Food" />
              ) : (
                <span className="text-6xl text-gray-500">📷</span>
              )}
              
              {/* Native File Input for Camera/Gallery */}
              <input 
                type="file" 
                accept="image/*" 
                capture="environment" 
                onChange={handleCapture}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
            </div>

            {imageUri && (
              <button onClick={uploadImage} className="w-full max-w-xs bg-[#FFC107] text-[#0C3638] font-bold text-lg py-4 rounded-full shadow-lg">
                Analyze Food
              </button>
            )}
            {!imageUri && (
              <p className="text-center text-sm text-gray-300">Tap the camera box to take a picture of your meal!</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
