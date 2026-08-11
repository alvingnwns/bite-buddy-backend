import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, ScrollView, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../context/AuthContext';
import { apiClient, supabase } from '../../api/client';

export default function ParentDashboard() {
  const router = useRouter();
  const { user } = useAuth();
  const [children, setChildren] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchChildren();
  }, []);

  const fetchChildren = async () => {
    try {
      // In a real scenario, this fetches from Supabase or API where parent_id = user.id
      // We mock it for now since the backend endpoint might vary
      setChildren([
        { id: 1, name: 'Budi', level: 5, health: 96, xp: 67 },
      ]);
    } catch (e) {
      console.log('Error fetching children', e);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.replace('/login');
  };

  if (loading) return <View style={styles.center}><ActivityIndicator color="#0C3638" /></View>;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Parent Dashboard</Text>
        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.content}>
        <Text style={styles.sectionTitle}>Your Children</Text>
        
        <ScrollView style={styles.list}>
          {children.map((c) => (
            <TouchableOpacity key={c.id} style={styles.card} onPress={() => router.push(`/parent/view-child?id=${c.id}`)}>
              <View style={styles.avatarMock}><Text style={styles.avatarEmoji}>👦</Text></View>
              <View style={styles.cardInfo}>
                <Text style={styles.childName}>{c.name}</Text>
                <Text style={styles.childStats}>Level {c.level} • HP: {c.health}</Text>
              </View>
              <Text style={styles.arrow}>{'>'}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <TouchableOpacity style={styles.addBtn}>
          <Text style={styles.addBtnText}>+ Link New Child</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 24, paddingTop: 40, borderBottomWidth: 1, borderBottomColor: '#E2E8F0' },
  title: { fontSize: 24, fontWeight: '700', color: '#0C3638' },
  logoutBtn: { backgroundColor: '#FEE2E2', paddingHorizontal: 15, paddingVertical: 8, borderRadius: 10 },
  logoutText: { color: '#EF4444', fontWeight: 'bold' },
  content: { padding: 24, flex: 1 },
  sectionTitle: { fontSize: 20, fontWeight: '600', color: '#0C3638', marginBottom: 20 },
  list: { flex: 1 },
  card: { backgroundColor: '#F8FAFC', padding: 20, borderRadius: 20, flexDirection: 'row', alignItems: 'center', marginBottom: 15, borderWidth: 1, borderColor: '#E2E8F0' },
  avatarMock: { width: 50, height: 50, backgroundColor: '#D9ECF3', borderRadius: 25, justifyContent: 'center', alignItems: 'center', marginRight: 15 },
  avatarEmoji: { fontSize: 24 },
  cardInfo: { flex: 1 },
  childName: { fontSize: 18, fontWeight: '700', color: '#0C3638', marginBottom: 5 },
  childStats: { fontSize: 14, color: '#64748B' },
  arrow: { fontSize: 20, color: '#CBD5E1', fontWeight: 'bold' },
  addBtn: { backgroundColor: '#5282BB', padding: 18, borderRadius: 15, alignItems: 'center', marginTop: 20 },
  addBtnText: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' },
});
