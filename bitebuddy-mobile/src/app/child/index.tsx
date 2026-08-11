import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, ActivityIndicator, Dimensions } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { useRouter } from 'expo-router';
import { apiClient } from '../api/client';

const { width } = Dimensions.get('window');

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
      const res = await apiClient.get('/users/me');
      if (res.data && res.data.virtual_pet) {
        setPet(res.data.virtual_pet);
      } else {
        setPet({ health: 96, exp: 67, level: 5 }); // Matching Figma values
      }
    } catch (error) {
      setPet({ health: 96, exp: 67, level: 5 });
    } finally {
      setLoading(false);
    }
  };

  if (authLoading || loading || !user) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#0C3638" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Settings / Top Bar */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.iconBtn} onPress={() => router.push('/child/info')}>
          <Text style={styles.iconText}>⚙️</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.iconBtn}>
          <Text style={styles.iconText}>🔔</Text>
        </TouchableOpacity>
      </View>

      {/* Level Badge */}
      <View style={styles.levelBadge}>
        <Text style={styles.levelText}>Level {pet?.level ?? 5}</Text>
      </View>

      {/* Pet Status Card */}
      <View style={styles.petStatusCard}>
        <Text style={styles.petStatusTitle}>Pet Status</Text>
        
        <View style={styles.barRow}>
          <Text style={styles.barLabel}>HP</Text>
          <View style={styles.barBackground}>
            <View style={[styles.hpBarFill, { width: `${pet?.health ?? 96}%` as any }]} />
            <Text style={styles.barText}>{pet?.health ?? 96}</Text>
          </View>
        </View>

        <View style={styles.barRow}>
          <Text style={styles.barLabel}>XP</Text>
          <View style={styles.barBackground}>
            <View style={[styles.xpBarFill, { width: `${pet?.exp ?? 67}%` as any }]} />
            <Text style={styles.barText}>{pet?.exp ?? 67}</Text>
          </View>
        </View>
      </View>

      {/* Placeholder for Pet Character */}
      <View style={styles.petCharacterContainer}>
        {/* Figma uses an illustration here */}
        <Text style={styles.petEmojiPlaceholder}>🦖</Text>
      </View>

      {/* Bottom Menu Navigation */}
      <View style={styles.bottomMenu}>
        <TouchableOpacity style={styles.menuItem} onPress={() => router.push('/child/schedule')}>
          <View style={styles.menuIconBox}>
            <Text style={styles.menuEmoji}>📅</Text>
          </View>
          <View style={styles.menuLabelBox}>
            <Text style={styles.menuLabel}>Schedule</Text>
          </View>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.menuItem} onPress={() => router.push('/child/scan')}>
          <View style={styles.menuIconBox}>
            <Text style={styles.menuEmoji}>🥣</Text>
          </View>
          <View style={styles.menuLabelBox}>
            <Text style={styles.menuLabel}>Feed</Text>
          </View>
        </TouchableOpacity>

        <TouchableOpacity style={styles.menuItem} onPress={() => router.push('/child/meds')}>
          <View style={styles.menuIconBox}>
            <Text style={styles.menuEmoji}>💊</Text>
          </View>
          <View style={styles.menuLabelBox}>
            <Text style={styles.menuLabel}>Heal</Text>
          </View>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#FFFFFF', // Assuming white background before image
    alignItems: 'center',
  },
  center: { 
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center' 
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    paddingHorizontal: 24,
    paddingTop: 42, // from Figma
  },
  iconBtn: {
    width: 57,
    height: 57,
    backgroundColor: '#D9ECF3',
    borderWidth: 4,
    borderColor: '#0C3638',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconText: {
    fontSize: 24,
  },
  levelBadge: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 17,
    paddingVertical: 11,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    marginTop: 20,
    alignSelf: 'center',
  },
  levelText: {
    fontSize: 20,
    fontWeight: '600',
    color: '#0C3638',
  },
  petStatusCard: {
    backgroundColor: '#FEFEFF',
    width: 337,
    height: 138.7,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
    borderTopRightRadius: 20,
    borderTopLeftRadius: 0,
    padding: 20,
    paddingLeft: 27,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3.8 },
    shadowOpacity: 0.25,
    shadowRadius: 4.75,
    elevation: 5,
  },
  petStatusTitle: {
    fontSize: 22.8,
    fontWeight: '600',
    color: '#0C3638',
    marginBottom: 10,
  },
  barRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 13,
  },
  barLabel: {
    fontSize: 19,
    fontWeight: '600',
    color: '#0C3638',
    width: 30,
    marginRight: 6,
  },
  barBackground: {
    backgroundColor: '#D9D9D9',
    height: 23.75,
    borderRadius: 14.25,
    width: 248.9,
    justifyContent: 'center',
  },
  hpBarFill: {
    backgroundColor: '#6CC55F',
    height: 23.75,
    borderRadius: 14.25,
    position: 'absolute',
    left: 0,
  },
  xpBarFill: {
    backgroundColor: '#5282BB',
    height: 23.75,
    borderRadius: 14.25,
    position: 'absolute',
    left: 0,
  },
  barText: {
    position: 'absolute',
    left: 14,
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  petCharacterContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  petEmojiPlaceholder: {
    fontSize: 100,
  },
  bottomMenu: {
    backgroundColor: '#0C3638',
    width: width - 24, // Approx 377px
    height: 140,
    borderRadius: 100,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 31,
    paddingTop: 27,
    paddingBottom: 25,
    position: 'absolute',
    bottom: 20, // Adjust based on screen
  },
  menuItem: {
    width: 88,
    alignItems: 'center',
  },
  menuIconBox: {
    backgroundColor: '#D9FFE1',
    width: 88,
    height: 88,
    borderRadius: 44,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: -15,
    zIndex: 1,
  },
  menuEmoji: {
    fontSize: 32,
  },
  menuLabelBox: {
    backgroundColor: '#116367',
    borderRadius: 65,
    paddingVertical: 3, // approx to height 23
    paddingHorizontal: 12,
    zIndex: 2,
  },
  menuLabel: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'center',
  },
});
