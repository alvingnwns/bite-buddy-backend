'use client';

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const [isRegister, setIsRegister] = useState(false)
  
  const handleAuth = async (e: React.FormEvent, role: string) => {
    e.preventDefault()
    setLoading(true)
    
    if (isRegister) {
      // For register, we also need to store metadata for role
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { role: role }
        }
      })
      if (error) {
        alert(error.message)
        setLoading(false)
        return
      }
      alert('Registration successful (Check your email or just login if auto-confirm is on). Please login now.')
      setIsRegister(false)
      setLoading(false)
      return
    }

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      alert(error.message)
      setLoading(false)
      return
    }

    if (role === 'child') router.push('/child')
    else if (role === 'parent') router.push('/parent')
    else router.push('/doctor')
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-gray-900">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <h2 className="text-3xl font-extrabold text-[#0C3638]">BiteBuddy Web Test</h2>
        <p className="mt-2 text-sm text-gray-600">{isRegister ? 'Register a test account' : 'Login to your test account'}</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6">
            <div>
              <label className="block text-sm font-medium">Email address</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium">Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
            </div>

            <div className="space-y-3 pt-4">
              <p className="text-xs text-center text-gray-500">{isRegister ? 'Register as:' : 'Login as:'}</p>
              <button onClick={(e) => handleAuth(e, 'child')} disabled={loading} className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#0C3638] hover:bg-[#124b4e]">
                Child
              </button>
              <button onClick={(e) => handleAuth(e, 'parent')} disabled={loading} className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700">
                Parent
              </button>
              <button onClick={(e) => handleAuth(e, 'doctor')} disabled={loading} className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700">
                Doctor
              </button>
            </div>
            
            <div className="mt-4 text-center">
              <button type="button" onClick={() => setIsRegister(!isRegister)} className="text-sm text-indigo-600 hover:text-indigo-500">
                {isRegister ? 'Already have an account? Login' : 'Need an account? Register'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
