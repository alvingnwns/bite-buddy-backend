import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';

export default function ViewChildPage() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backText}>{'< Back'}</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Child Activity</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Recent Meals</Text>
          
          <View style={styles.logItem}>
            <Text style={styles.logEmoji}>🥣</Text>
            <View style={styles.logInfo}>
              <Text style={styles.logText}>Breakfast (Oatmeal)</Text>
              <Text style={styles.logTime}>07:30 AM</Text>
            </View>
            <Text style={styles.statusOk}>Good</Text>
          </View>
          
          <View style={styles.logItem}>
            <Text style={styles.logEmoji}>🥣</Text>
            <View style={styles.logInfo}>
              <Text style={styles.logText}>Lunch (Chicken Soup)</Text>
              <Text style={styles.logTime}>12:45 PM</Text>
            </View>
            <Text style={styles.statusOk}>Good</Text>
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Medication</Text>
          
          <View style={styles.logItem}>
            <Text style={styles.logEmoji}>💊</Text>
            <View style={styles.logInfo}>
              <Text style={styles.logText}>Insulin Uploaded</Text>
              <Text style={styles.logTime}>07:00 AM</Text>
            </View>
            <Text style={styles.statusOk}>Verified</Text>
          </View>
        </View>

        <TouchableOpacity style={styles.notifyBtn}>
          <Text style={styles.notifyText}>Notify Child to Eat</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF' },
  header: { flexDirection: 'row', alignItems: 'center', padding: 24, paddingTop: 40, borderBottomWidth: 1, borderBottomColor: '#E2E8F0' },
  backBtn: { backgroundColor: '#D9ECF3', padding: 10, borderRadius: 10, marginRight: 20 },
  backText: { color: '#0C3638', fontWeight: 'bold' },
  title: { fontSize: 20, fontWeight: '700', color: '#0C3638' },
  content: { padding: 24 },
  card: { backgroundColor: '#F8FAFC', borderRadius: 20, padding: 20, marginBottom: 20, borderWidth: 1, borderColor: '#E2E8F0' },
  cardTitle: { fontSize: 18, fontWeight: '600', color: '#0C3638', marginBottom: 15 },
  logItem: { flexDirection: 'row', alignItems: 'center', marginBottom: 15 },
  logEmoji: { fontSize: 24, marginRight: 15 },
  logInfo: { flex: 1 },
  logText: { fontSize: 16, fontWeight: '500', color: '#334155' },
  logTime: { fontSize: 13, color: '#94A3B8' },
  statusOk: { color: '#10B981', fontWeight: 'bold', fontSize: 14 },
  notifyBtn: { backgroundColor: '#F59E0B', padding: 18, borderRadius: 15, alignItems: 'center', marginTop: 10 },
  notifyText: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' },
});
