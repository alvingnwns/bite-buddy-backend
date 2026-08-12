'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1'

export default function SchedulePage() {
  const router = useRouter();
  const [schedules, setSchedules] = useState<any[]>([]);

  useEffect(() => {
    fetchSchedules();
  }, []);

  const fetchSchedules = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return router.push('/');
      
      const res = await fetch(`${API_URL}/schedules/${session.user.id}`);
      if (res.ok) {
        setSchedules(await res.json());
      } else {
        throw new Error('Fetch failed');
      }
    } catch (e) {
      console.log('Error fetching schedules', e);
      // Dummy data fallback matching Figma
      setSchedules([
        { id: 1, meal_type: 'breakfast', status: 'done', start_time: '2026-08-12T06:00:00Z', end_time: '2026-08-12T08:00:00Z' },
        { id: 2, meal_type: 'pills', status: 'missed', start_time: '2026-08-12T07:00:00Z', end_time: '2026-08-12T08:00:00Z' },
        { id: 3, meal_type: 'lunch', status: 'late', start_time: '2026-08-12T11:50:00Z', end_time: '2026-08-12T13:00:00Z' },
        { id: 4, meal_type: 'dinner', status: 'pending', start_time: '2026-08-12T17:00:00Z', end_time: '2026-08-12T19:00:00Z' },
      ]);
    }
  };

  const getStatusStyle = (status: string) => {
    // We simulate status based on times if not explicitly set, but for now just use dummy mapping or fallback to 'pending'
    switch(status) {
      case 'done': return { bg: '#10B981', text: 'Done' };
      case 'missed': return { bg: '#E03B38', text: 'Skipped' };
      case 'late': return { bg: '#F59E0B', text: 'Late' };
      default: return { bg: '#5282BB', text: 'Not Yet' };
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#F3FEF8] relative font-sans overflow-hidden">
      {/* Back Button */}
      <div className="p-6 pt-10">
        <button onClick={() => router.back()} className="w-10 h-10 bg-[#E03B38] text-white rounded-lg flex items-center justify-center font-bold text-xl shadow">
          {'<'}
        </button>
      </div>

      <h1 className="text-3xl font-bold text-[#0C3638] px-8 mb-6 mt-4">Daily Tasks</h1>

      <div className="flex-1 overflow-y-auto px-8 pb-10">
        
        {/* Stats Card */}
        <div className="bg-[#374A71] rounded-2xl w-full p-5 mb-6 shadow-lg text-white">
          <p className="text-sm font-semibold mb-1 text-gray-200">Current streak</p>
          <div className="flex justify-between items-center mb-4">
            <span className="text-2xl font-bold">🔥 12 Days</span>
            <span className="bg-[#719FC6] px-3 py-1 rounded-full text-xs font-bold">45 XP</span>
          </div>
          
          <p className="text-xs text-center text-gray-300 mb-4">Mon, Mar 22</p>
          
          {/* Mock Chart Area */}
          <div className="h-24 border-y border-[#596977] py-2 flex flex-col justify-between">
            <div className="flex-1 flex flex-row items-end justify-around px-2">
              <div className="w-6 bg-white rounded-md" style={{ height: '80%' }}></div>
              <div className="w-6 bg-white rounded-md" style={{ height: '50%' }}></div>
              <div className="w-6 bg-[#719FC6] rounded-md" style={{ height: '100%' }}></div>
              <div className="w-6 bg-white rounded-md" style={{ height: '40%' }}></div>
              <div className="w-6 bg-white rounded-md" style={{ height: '70%' }}></div>
            </div>
            <div className="flex flex-row justify-around mt-2 text-[#596977] text-xs">
              <span>9h</span>
              <span>7h</span>
              <span>5h</span>
              <span>3h</span>
              <span>1h</span>
            </div>
          </div>
        </div>

        {/* Schedule List */}
        <div className="bg-white rounded-2xl w-full p-5 shadow">
          <h2 className="text-xl font-bold text-[#0C3638] mb-4">Today's Schedule</h2>
          
          <div className="flex flex-col space-y-4">
            {schedules.map((s, i) => {
              const statusStyle = getStatusStyle(s.status || 'pending');
              const timeStr = s.start_time 
                ? `${new Date(s.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}-${new Date(s.end_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`
                : s.target_time;
                
              return (
                <div key={i} className="flex flex-row items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-6 h-6 bg-[#D9ECF3] rounded-full"></div>
                    <span className="text-sm font-semibold text-gray-700 capitalize">{s.meal_type} ({timeStr})</span>
                  </div>
                  <div className="px-3 py-1 rounded-full text-white text-xs font-bold" style={{ backgroundColor: statusStyle.bg }}>
                    {statusStyle.text}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        
      </div>
    </div>
  );
}
