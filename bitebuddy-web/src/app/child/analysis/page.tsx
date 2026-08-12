'use client';

import React, { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { supabase } from '@/lib/supabase'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1'

export default function AnalysisResult() {
  const router = useRouter()
  const searchParams = useSearchParams()
  
  const imageUri = searchParams.get('imageUri') || null
  const ingredientsStr = searchParams.get('ingredients') || '[]'
  
  const [ingredients, setIngredients] = useState<any[]>([])
  const [editableGrams, setEditableGrams] = useState(0)
  const [editableFoodName, setEditableFoodName] = useState('Detected Food')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    try {
      const parsed = JSON.parse(ingredientsStr)
      setIngredients(parsed)
      if (parsed.length > 0) {
        setEditableFoodName(parsed[0].ingredient || parsed[0].description || 'Unknown Food')
        const totalW = parsed.reduce((sum: number, i: any) => sum + (i.weight_g || 0), 0)
        setEditableGrams(totalW)
      }
    } catch(e) {}
  }, [ingredientsStr])

  const totalGrams = editableGrams
  // Using the exact formulas from mobile version
  const estimatedCalories = Math.round(totalGrams * 1.2)
  const estimatedSugar = Math.round(totalGrams * 0.04 * 10) / 10
  const estimatedCarbs = Math.round(totalGrams * 0.24 * 100) / 100
  const estimatedFiber = Math.round(totalGrams * 0.01 * 10) / 10
  const estimatedProtein = Math.round(totalGrams * 0.04 * 100) / 100
  const estimatedFat = Math.round(totalGrams * 0.007 * 100) / 100

  const sugarCategory = estimatedSugar < 5 ? 'low' : estimatedSugar < 15 ? 'medium' : 'high'
  const sugarCategoryColor = sugarCategory === 'low' ? '#10B981' : sugarCategory === 'medium' ? '#E03B38' : '#DC2626'

  const handleConfirm = async () => {
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return router.push('/')

      const payload = {
        child_id: session.user.id,
        logged_by: session.user.id,
        meal_type: 'lunch',
        public_url: imageUri || 'http://example.com/dummy.jpg',
        notes: '',
        ingredients: ingredients.length > 0 ? ingredients.map((i, index) => ({
          ...i,
          weight_g: index === 0 ? (editableGrams > 0 ? editableGrams : 1) : (i.weight_g > 0 ? i.weight_g : 1), 
          ingredient: index === 0 ? editableFoodName : i.ingredient,
          description: i.description || 'Simulated description'
        })) : [{
          ingredient: editableFoodName,
          description: editableFoodName,
          weight_g: editableGrams > 0 ? editableGrams : 1
        }]
      }

      const response = await fetch(`${API_URL}/scan/food/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Backend returned an error:', response.status, errorText);
        throw new Error('Confirm failed')
      }
      router.push('/child')
    } catch (e) {
      console.error(e)
      alert('Failed to confirm food')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col min-h-screen bg-[#F3FEF8] font-sans overflow-y-auto items-center pb-5 relative">
      {/* Back Button */}
      <button 
        onClick={() => router.back()} 
        className="bg-[#E03B38] text-white w-[37px] h-[37px] rounded-[7px] flex items-center justify-center absolute top-[50px] left-[35px] z-10 text-[18px] font-bold"
      >
        {'<'}
      </button>

      {/* Page Title */}
      <h1 className="text-[#0C3638] text-[32px] font-bold mt-[95px] mb-[15px]">
        Analysis Result
      </h1>

      {/* Main Card */}
      <div className="bg-[#374171] w-[calc(100%-70px)] max-w-[400px] rounded-[20px] shadow-[0_0_20px_rgba(55,65,113,0.25)] overflow-hidden">
        {/* Card Header */}
        <div className="bg-[#5282BB] w-full py-[15px] flex flex-col items-center">
          <span className="text-[#D9ECF3] text-[14px] font-semibold">AI detected</span>
          <input 
            type="text"
            value={editableFoodName}
            onChange={(e) => setEditableFoodName(e.target.value)}
            placeholder="Food Name"
            className="text-white text-[22px] font-bold text-center border-b border-white/30 min-w-[150px] bg-transparent focus:outline-none placeholder:text-gray-300"
          />
        </div>

        <p className="text-[#F9FDFF] text-[11px] font-semibold text-center mt-[12px] mb-[8px]">
          Estimated Sugar Content
        </p>

        {/* Sugar Content Badge */}
        <div className="bg-[#F3B73B] border-[4px] border-[#E8F4FF] rounded-[10px] w-[257px] h-[50px] mx-auto flex items-center justify-center relative z-0">
          <span className="text-[#FF6200] text-[22px] font-bold">{estimatedSugar} g/portion</span>
        </div>
        
        {/* Sugar Category Badge */}
        <div className="bg-[#E8F4FF] px-[14px] py-[3px] rounded-[20px] mx-auto -mt-[5px] z-10 relative flex justify-center w-max">
          <span className="text-[10px] font-semibold" style={{ color: sugarCategoryColor }}>
            Category: {sugarCategory}
          </span>
        </div>

        {/* Middle Section: Image & Portion */}
        <div className="flex flex-row justify-between px-[20px] mt-[15px]">
          {/* Image Box */}
          <div className="w-[133px] h-[170px] border-[4px] border-[#5282BB] rounded-[10px] overflow-hidden bg-[#CCC] flex items-center justify-center">
            {imageUri ? (
              <img src={imageUri} className="w-full h-full object-cover" alt="Food" />
            ) : (
              <div className="w-full h-full bg-[#D9D9D9] flex items-center justify-center text-[40px]">🍽️</div>
            )}
          </div>

          {/* Portion Box */}
          <div className="w-[113px] h-[170px] bg-white rounded-[10px] flex flex-col items-center justify-center py-[10px]">
            <span className="text-[#374171] text-[20px] font-bold text-center leading-tight mb-[5px]">
              Portion<br/>size
            </span>
            <input 
              type="number"
              value={editableGrams}
              onChange={(e) => setEditableGrams(parseInt(e.target.value) || 0)}
              className="text-[#0C3638] text-[36px] font-bold text-center border-b-[2px] border-[#CCC] min-w-[80px] max-w-[90px] p-0 m-0 bg-transparent focus:outline-none"
            />
            <span className="text-[#0C3638] text-[13px] font-bold -mt-[5px]">gram</span>
          </div>
        </div>

        {/* Detected Ingredients List */}
        {ingredients.length > 0 && (
          <div className="px-[25px] mt-[12px]">
            <h3 className="text-[#E8F4FF] text-[12px] font-bold mb-[4px]">Detected Ingredients:</h3>
            {ingredients.map((item, idx) => (
              <p key={idx} className="text-[#D9ECF3] text-[11px] font-medium">
                • {item.ingredient || item.description} ({item.weight_g}g)
              </p>
            ))}
          </div>
        )}

        {/* Nutrition Facts Bottom Block */}
        <div className="bg-[#D9ECF3] flex flex-row justify-between items-center px-[20px] py-[15px] mt-[15px]">
          <div className="flex-1">
            <h2 className="text-[#374171] text-[18px] font-bold mb-[5px]">Nutrition Facts</h2>
            <p className="text-[#5282BB] text-[12px] font-bold">Calories: {estimatedCalories} kkal</p>
            <p className="text-[#5282BB] text-[12px] font-bold">Carbs: {estimatedCarbs} gram</p>
            <p className="text-[#5282BB] text-[12px] font-bold">Fiber: {estimatedFiber} gram</p>
            <p className="text-[#5282BB] text-[12px] font-bold">Protein: {estimatedProtein} gram</p>
            <p className="text-[#5282BB] text-[12px] font-bold">Fat: {estimatedFat} gram</p>
          </div>
          <img src="/pet-glasses.png" alt="Pet Glasses" className="w-[90px] h-[90px] object-contain" />
        </div>
      </div>

      {/* Confirm Button */}
      <button 
        onClick={handleConfirm}
        disabled={loading}
        className="bg-[#374171] border-[3px] border-[#272E51] w-[calc(100%-70px)] max-w-[400px] h-[48px] rounded-[20px] flex items-center justify-center mx-auto mt-[20px] shadow-[0_3px_2px_rgba(55,65,113,0.5)] disabled:opacity-50"
      >
        <span className="text-[#E8F4FF] text-[22px] font-bold">
          {loading ? 'Confirming...' : 'Confirm'}
        </span>
      </button>

      <div className="h-[40px] w-full" />
    </div>
  )
}
