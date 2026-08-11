import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { api } from '../services/api';
import { supabase } from '../services/supabase';

interface HomeScreenProps {
  onNavigateToScan: () => void;
  onLogout: () => void;
}

export default function HomeScreen({ onNavigateToScan, onLogout }: HomeScreenProps) {
  const [userData, setUserData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchUserData = async () => {
    try {
      setLoading(true);
      const res = await api.get('/users/me');
      setUserData(res.data);
    } catch (error) {
      console.error('Failed to fetch user', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserData();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    onLogout();
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#3498DB" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.welcome}>Hi, {userData?.full_name || 'User'}!</Text>
        <TouchableOpacity onPress={handleLogout}>
          <Text style={styles.logout}>Logout</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.petCard}>
        <Text style={styles.petEmoji}>🐶</Text>
        <Text style={styles.petTitle}>Your Virtual Pet</Text>
        <Text style={styles.petStat}>Happiness: 100/100 (Dummy)</Text>
        <Text style={styles.petStat}>EXP: 520 (Dummy)</Text>
        <Text style={styles.petNote}>(Mocked from DB data for now)</Text>
      </View>

      <TouchableOpacity style={styles.scanButton} onPress={onNavigateToScan}>
        <Text style={styles.scanButtonText}>📸 Scan Food</Text>
      </TouchableOpacity>
      
      <TouchableOpacity style={styles.refreshButton} onPress={fetchUserData}>
        <Text style={styles.refreshButtonText}>Refresh Profile</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#F5F7FA',
    paddingTop: 60,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 40,
  },
  welcome: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2C3E50',
  },
  logout: {
    color: '#E74C3C',
    fontWeight: 'bold',
  },
  petCard: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 30,
    alignItems: 'center',
    marginBottom: 40,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 5,
  },
  petEmoji: {
    fontSize: 80,
    marginBottom: 10,
  },
  petTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  petStat: {
    fontSize: 16,
    color: '#34495E',
    marginBottom: 5,
  },
  petNote: {
    fontSize: 12,
    color: '#95A5A6',
    marginTop: 10,
  },
  scanButton: {
    backgroundColor: '#2ECC71',
    padding: 18,
    borderRadius: 15,
    alignItems: 'center',
    marginBottom: 15,
  },
  scanButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  refreshButton: {
    padding: 15,
    alignItems: 'center',
  },
  refreshButtonText: {
    color: '#3498DB',
    fontWeight: 'bold',
  },
});
