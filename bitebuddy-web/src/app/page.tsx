"use client";

import React, { useState, useEffect } from "react";
import { Users, LayoutDashboard, Settings, LogOut, CheckCircle, Stethoscope, Clock, Activity, FileText } from "lucide-react";
import { api } from "@/lib/api";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<any>(null);

  // States for Clinical
  const [weight, setWeight] = useState("30");
  const [diabetesType, setDiabetesType] = useState("Type 1");
  const [clinicalLoading, setClinicalLoading] = useState(false);
  const [clinicalResult, setClinicalResult] = useState<any>(null);

  // States for Schedules & Logs
  const [schedules, setSchedules] = useState<any[]>([]);
  const [foodLogs, setFoodLogs] = useState<any[]>([]);

  // Fetch dummy children on mount
  useEffect(() => {
    // In real app, we fetch from /users/me first, then get children
    // Using a dummy parent ID to fetch children for demo
    const dummyParentId = "00000000-0000-0000-0000-000000000000"; 
    api.get(`/users/${dummyParentId}/children`)
      .then(res => {
        if (res.data && res.data.length > 0) {
          setPatients(res.data);
          setSelectedPatient(res.data[0]);
        } else {
          // Fallback if DB is empty
          const fallback = [
            { id: "11111111-1111-1111-1111-111111111111", full_name: "Leo (Test Child)", age: 8, gender: "Male" }
          ];
          setPatients(fallback);
          setSelectedPatient(fallback[0]);
        }
      })
      .catch(() => {
        const fallback = [
            { id: "11111111-1111-1111-1111-111111111111", full_name: "Leo (Mock Data DB Error)", age: 8, gender: "Male" }
        ];
        setPatients(fallback);
        setSelectedPatient(fallback[0]);
      });
  }, []);

  // Fetch Schedules & Logs whenever selectedPatient or tab changes
  useEffect(() => {
    if (!selectedPatient) return;

    if (activeTab === "schedules") {
      api.get(`/schedules/${selectedPatient.id}`)
        .then(res => setSchedules(res.data))
        .catch(err => console.error("Schedules fetch error", err));
    } else if (activeTab === "logs") {
      api.get(`/logs/food/${selectedPatient.id}`)
        .then(res => setFoodLogs(res.data))
        .catch(err => console.error("Logs fetch error", err));
    }
  }, [activeTab, selectedPatient]);

  const handleUpdateClinical = async (e: React.FormEvent) => {
    e.preventDefault();
    setClinicalLoading(true);
    setClinicalResult(null);

    try {
      const payload = {
        child_id: selectedPatient.id,
        weight_kg: parseFloat(weight),
        height_cm: 120,
        diabetes_type: diabetesType
      };

      const res = await api.post("/clinical/", payload);
      setClinicalResult({ type: "success", data: res.data });
    } catch (err: any) {
      setClinicalResult({ type: "error", msg: err.message || "Gagal update" });
    } finally {
      setClinicalLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 text-gray-800">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-100 flex items-center gap-3">
          <Stethoscope className="text-blue-600" />
          <h1 className="text-xl font-bold text-gray-800">Doctor Panel</h1>
        </div>
        <nav className="flex-1 p-4 space-y-2">
          <button onClick={() => setActiveTab("dashboard")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition ${activeTab === 'dashboard' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}>
            <LayoutDashboard size={20} /> Dashboard
          </button>
          <button onClick={() => setActiveTab("clinical")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition ${activeTab === 'clinical' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}>
            <Activity size={20} /> Clinical Targets
          </button>
          <button onClick={() => setActiveTab("schedules")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition ${activeTab === 'schedules' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}>
            <Clock size={20} /> Meal Schedules
          </button>
          <button onClick={() => setActiveTab("logs")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition ${activeTab === 'logs' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}>
            <FileText size={20} /> Food Logs
          </button>
        </nav>
        <div className="p-4 border-t border-gray-100">
          <button className="flex items-center gap-3 px-4 py-3 w-full text-red-600 hover:bg-red-50 rounded-lg transition">
            <LogOut size={20} /> Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto flex flex-col">
        <header className="bg-white border-b border-gray-200 p-6 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">BiteBuddy Dashboard v2</h2>
            <p className="text-gray-500">Real-time data integration with Backend API.</p>
          </div>
          
          {/* Patient Selector Dropdown */}
          <div className="flex items-center gap-4 bg-gray-50 p-2 rounded-lg border border-gray-200">
            <Users size={20} className="text-gray-500" />
            <select 
              className="bg-transparent font-medium outline-none text-gray-700 cursor-pointer"
              value={selectedPatient?.id || ""}
              onChange={(e) => {
                const pat = patients.find(p => p.id === e.target.value);
                if (pat) setSelectedPatient(pat);
              }}
            >
              {patients.map(p => (
                <option key={p.id} value={p.id}>{p.full_name}</option>
              ))}
            </select>
          </div>
        </header>

        <main className="p-6">
          
          {/* TAB: DASHBOARD */}
          {activeTab === "dashboard" && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                <h3 className="text-gray-500 font-medium">Total Pasien</h3>
                <p className="text-3xl font-bold text-blue-600 mt-2">{patients.length}</p>
              </div>
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                <h3 className="text-gray-500 font-medium">Pasien Aktif</h3>
                <p className="text-3xl font-bold text-green-600 mt-2">{selectedPatient?.full_name}</p>
              </div>
            </div>
          )}

          {/* TAB: CLINICAL */}
          {activeTab === "clinical" && selectedPatient && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-2xl">
              <h3 className="text-xl font-bold text-gray-800 mb-4">Pengaturan Klinis: {selectedPatient.full_name}</h3>
              
              <form onSubmit={handleUpdateClinical} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Berat Badan (kg)</label>
                    <input
                      type="number"
                      value={weight}
                      onChange={(e) => setWeight(e.target.value)}
                      className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tipe Diabetes</label>
                    <select
                      value={diabetesType}
                      onChange={(e) => setDiabetesType(e.target.value)}
                      className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                    >
                      <option value="Type 1">Type 1</option>
                      <option value="Type 2">Type 2</option>
                    </select>
                  </div>
                </div>

                <div className="pt-4">
                  <button
                    type="submit"
                    disabled={clinicalLoading}
                    className="bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50"
                  >
                    {clinicalLoading ? "Menyimpan..." : "Kalkulasi & Simpan Target Nutrisi (AI)"}
                  </button>
                </div>
              </form>

              {clinicalResult && (
                <div className={`mt-6 p-4 rounded-lg border ${clinicalResult.type === "success" ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                  <h4 className={`font-bold ${clinicalResult.type === "success" ? "text-green-800" : "text-red-800"}`}>
                    {clinicalResult.type === "success" ? "Berhasil Diperbarui!" : "Terjadi Kesalahan"}
                  </h4>
                  {clinicalResult.type === "success" ? (
                    <div className="mt-2 text-sm text-green-700 space-y-1">
                      <p><strong>Target Kalori (BMR):</strong> {clinicalResult.data.target_daily_calories} kkal</p>
                      <p><strong>Batas Gula (Max Sugar):</strong> {clinicalResult.data.max_sugar_intake_g} gram</p>
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-red-600">{clinicalResult.msg}</p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB: SCHEDULES */}
          {activeTab === "schedules" && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="p-4 bg-gray-50 border-b border-gray-200">
                <h3 className="font-bold text-gray-700">Jadwal Makan Anak</h3>
              </div>
              {schedules.length === 0 ? (
                <p className="p-6 text-gray-500 text-center">Belum ada jadwal yang terdaftar di database.</p>
              ) : (
                <ul className="divide-y divide-gray-100">
                  {schedules.map((s, idx) => (
                    <li key={idx} className="p-4 hover:bg-gray-50">
                      <p className="font-semibold text-gray-800">{s.meal_type}</p>
                      <p className="text-sm text-gray-500">Pukul: {s.start_time} - {s.end_time}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* TAB: LOGS */}
          {activeTab === "logs" && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="p-4 bg-gray-50 border-b border-gray-200">
                <h3 className="font-bold text-gray-700">Riwayat Scan Makanan</h3>
              </div>
              {foodLogs.length === 0 ? (
                <p className="p-6 text-gray-500 text-center">Belum ada makanan yang di-scan.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
                  {foodLogs.map((log, idx) => (
                    <div key={idx} className="border border-gray-200 rounded-lg p-4 flex flex-col gap-2">
                      {log.photo_url && <img src={log.photo_url} alt="Food" className="w-full h-32 object-cover rounded-md" />}
                      <h4 className="font-bold text-gray-800">{log.food_name || "Unknown Food"}</h4>
                      <p className="text-sm text-gray-600">Kalori: {log.calories_kcal} kcal</p>
                      <p className="text-sm text-gray-600">Gula: {log.sugar_g} g</p>
                      <p className="text-xs text-gray-400 mt-2">{new Date(log.consumed_at).toLocaleString()}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </main>
      </div>
    </div>
  );
}
