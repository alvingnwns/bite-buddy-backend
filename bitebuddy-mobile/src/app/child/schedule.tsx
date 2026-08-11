import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { apiClient } from '../../api/client';

export default function SchedulePage() {
  const router = useRouter();
  const [schedules, setSchedules] = useState<any[]>([]);

  useEffect(() => {
    fetchSchedules();
  }, []);

  const fetchSchedules = async () => {
    try {
      const res = await apiClient.get('/schedules/');
      setSchedules(res.data || []);
    } catch (e) {
      console.log('Error fetching schedules', e);
      // Dummy data fallback
      setSchedules([
        { id: 1, meal_type: 'breakfast', status: 'done', target_time: '07:00' },
        { id: 2, meal_type: 'lunch', status: 'missed', target_time: '12:00' },
        { id: 3, meal_type: 'dinner', status: 'pending', target_time: '19:00' },
      ]);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backText}>{'< Back'}</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.title}>Take a picture of your food!</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Today's Schedule</Text>
        <ScrollView style={styles.list}>
          {schedules.map((s, i) => (
            <View key={i} style={styles.taskItem}>
              <View style={[styles.statusDot, s.status === 'done' ? styles.dotDone : styles.dotPending]} />
              <Text style={styles.taskText}>{s.meal_type.toUpperCase()} ({s.target_time})</Text>
            </View>
          ))}
        </ScrollView>
      </View>

      <View style={styles.streakCard}>
        <Text style={styles.streakNumber}>165</Text>
        <Text style={styles.streakLabel}>days streak!</Text>
        <Text style={styles.emoji}>🔥</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF' },
  header: { padding: 24, paddingTop: 40 },
  backBtn: { backgroundColor: '#D9ECF3', padding: 10, borderRadius: 10, alignSelf: 'flex-start' },
  backText: { color: '#0C3638', fontWeight: 'bold' },
  title: { fontSize: 24, fontWeight: '700', color: '#0C3638', textAlign: 'center', marginBottom: 30, paddingHorizontal: 40 },
  card: { backgroundColor: '#D9ECF3', marginHorizontal: 24, borderRadius: 20, padding: 20, height: 200, marginBottom: 20 },
  cardTitle: { fontSize: 20, fontWeight: '700', color: '#0C3638', marginBottom: 15 },
  list: { flex: 1 },
  taskItem: { flexDirection: 'row', alignItems: 'center', marginBottom: 15 },
  statusDot: { width: 16, height: 16, borderRadius: 8, marginRight: 10 },
  dotDone: { backgroundColor: '#6CC55F' },
  dotPending: { backgroundColor: '#CBD5E1' },
  taskText: { fontSize: 16, color: '#334155', fontWeight: '500' },
  streakCard: { backgroundColor: '#D9FFE1', marginHorizontal: 24, borderRadius: 20, padding: 30, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 15 },
  streakNumber: { fontSize: 48, fontWeight: '800', color: '#116367' },
  streakLabel: { fontSize: 20, fontWeight: '600', color: '#116367' },
  emoji: { fontSize: 40 },
});
