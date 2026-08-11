import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, SafeAreaView, ActivityIndicator } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { useRouter } from 'expo-router';
import { apiClient } from '../api/client';

type PetStatus = {
  health: number;
  exp: number;
  level: number;
};

export default function HomeScreen() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [pet, setPet] = useState<PetStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace('/login');
    }
  }, [user, authLoading]);

  useEffect(() => {
    if (user) {
      fetchPetStatus();
    }
  }, [user]);

  const fetchPetStatus = async () => {
    try {
      // Mocking fetch or assuming backend has this endpoint.
      // In handoff it mentions GET /api/v1/users/me
      const res = await apiClient.get('/users/me');
      if (res.data && res.data.virtual_pet) {
        setPet(res.data.virtual_pet);
      } else {
        // Dummy fallback if no real data
        setPet({ health: 80, exp: 450, level: 3 });
      }
    } catch (error) {
      console.log('Error fetching pet, using dummy data', error);
      setPet({ health: 100, exp: 10, level: 1 });
    } finally {
      setLoading(false);
    }
  };

  if (authLoading || loading || !user) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#10B981" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.greeting}>Halo, {user.email?.split('@')[0]}!</Text>
        <TouchableOpacity style={styles.profileBtn}>
          <Text style={styles.profileText}>{user.email?.charAt(0).toUpperCase()}</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.petContainer}>
        {/* Placeholder for Virtual Pet Image */}
        <View style={styles.petImagePlaceholder}>
          <Text style={styles.petEmoji}>🦖</Text>
        </View>

        <View style={styles.statsCard}>
          <Text style={styles.statsTitle}>Status Peliharaan</Text>
          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Level {pet?.level}</Text>
            <Text style={styles.statLabel}>HP: {pet?.health}%</Text>
          </View>
          <View style={styles.progressBarBg}>
            <View style={[styles.progressBarFill, { width: `${pet?.health}%`, backgroundColor: (pet?.health ?? 0) > 50 ? '#10B981' : '#EF4444' }]} />
          </View>
        </View>
      </View>

      <View style={styles.actionsContainer}>
        <TouchableOpacity style={styles.scanBtn} onPress={() => router.push('/scan')}>
          <Text style={styles.scanBtnText}>📸 Scan Makanan</Text>
          <Text style={styles.scanBtnSub}>Beri makan pet kamu!</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 10,
  },
  greeting: { fontSize: 24, fontWeight: '800', color: '#1E293B' },
  profileBtn: {
    width: 40, height: 40, borderRadius: 20, backgroundColor: '#DBEAFE',
    justifyContent: 'center', alignItems: 'center'
  },
  profileText: { fontSize: 18, fontWeight: '700', color: '#1E3A8A' },
  petContainer: {
    flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24,
  },
  petImagePlaceholder: {
    width: 200, height: 200, borderRadius: 100, backgroundColor: '#E0E7FF',
    justifyContent: 'center', alignItems: 'center', marginBottom: 40,
    shadowColor: '#4F46E5', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.2, shadowRadius: 20, elevation: 10,
  },
  petEmoji: { fontSize: 80 },
  statsCard: {
    backgroundColor: '#FFFFFF', width: '100%', borderRadius: 24, padding: 24,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.05, shadowRadius: 10, elevation: 2,
  },
  statsTitle: { fontSize: 18, fontWeight: '700', color: '#334155', marginBottom: 16 },
  statRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  statLabel: { fontSize: 16, fontWeight: '600', color: '#64748B' },
  progressBarBg: { height: 12, backgroundColor: '#F1F5F9', borderRadius: 6, overflow: 'hidden' },
  progressBarFill: { height: '100%', borderRadius: 6 },
  actionsContainer: { padding: 24, paddingBottom: 40 },
  scanBtn: {
    backgroundColor: '#10B981', borderRadius: 20, padding: 20, alignItems: 'center',
    shadowColor: '#10B981', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 5,
  },
  scanBtnText: { color: '#FFF', fontSize: 22, fontWeight: '800' },
  scanBtnSub: { color: '#D1FAE5', fontSize: 14, fontWeight: '500', marginTop: 4 },
});
