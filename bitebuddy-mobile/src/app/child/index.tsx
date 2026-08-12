import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Dimensions, Image, ImageBackground } from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from 'expo-router';
import { apiClient } from '../../api/client';

const { width, height } = Dimensions.get('window');

type PetData = {
  happiness: number;
  experience_points: number;
  level: number;
  pet_name: string;
  pet_type: string;
  hunger: number;
  current_status: string;
};

export default function HomeScreen() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [pet, setPet] = useState<PetData | null>(null);
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
      const res = await apiClient.get(`/pets/${user.id}`);
      if (res.data) {
        setPet(res.data);
      } else {
        setDefaultPet();
      }
    } catch (error) {
      console.log('Pet fetch error, using defaults:', error);
      setDefaultPet();
    } finally {
      setLoading(false);
    }
  };

  const setDefaultPet = () => {
    setPet({
      happiness: 100,
      experience_points: 0,
      level: 1,
      pet_name: 'Buddy',
      pet_type: 'dog',
      hunger: 100,
      current_status: 'happy',
    });
  };

  if (authLoading || loading || !user) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#0C3638" />
      </View>
    );
  }

  // Compute HP from happiness (0-100 scale)
  const hp = pet?.happiness ?? 100;
  // XP as percentage of level progress (experience_points mod 100)
  const xp = (pet?.experience_points ?? 0) % 100;
  const level = pet?.level ?? 1;

  return (
    <View style={styles.container}>
      {/* Background - vertical stripes like Figma */}
      <View style={styles.bgStripes}>
        <View style={[styles.stripe, { left: '15%' }]} />
        <View style={[styles.stripe, { left: '38%' }]} />
        <View style={[styles.stripe, { left: '60%' }]} />
        <View style={[styles.stripe, { left: '82%' }]} />
      </View>
      
      {/* Floor */}
      <View style={styles.floor} />

      {/* Settings / Top Bar */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.iconBtn} onPress={() => router.push('/child/info')}>
          <Text style={{fontSize: 22}}>⚙️</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.iconBtn}>
          <Text style={{fontSize: 22}}>🔔</Text>
        </TouchableOpacity>
      </View>

      {/* Level Badge */}
      <View style={styles.levelBadge}>
        <Text style={styles.levelText}>Level {level}</Text>
      </View>

      {/* Pet Status Card */}
      <View style={styles.petStatusCard}>
        <Text style={styles.petStatusTitle}>Pet Status</Text>
        
        <View style={styles.barRow}>
          <Text style={styles.barLabel}>HP</Text>
          <View style={styles.barBackground}>
            <View style={[styles.hpBarFill, { width: `${hp}%` as any }]} />
            <Text style={styles.barText}>{hp}</Text>
          </View>
        </View>

        <View style={styles.barRow}>
          <Text style={styles.barLabel}>XP</Text>
          <View style={styles.barBackground}>
            <View style={[styles.xpBarFill, { width: `${xp}%` as any }]} />
            <Text style={styles.barText}>{xp}</Text>
          </View>
        </View>
      </View>

      {/* Pet Character - using imported Figma sprite */}
      <View style={styles.petCharacterContainer}>
        <Image 
          source={require('../../../assets/pet-happy.png')} 
          style={styles.petImage}
          resizeMode="contain"
        />
      </View>

      {/* Bottom Menu Navigation */}
      <View style={styles.bottomMenu}>
        <TouchableOpacity style={styles.menuItem} onPress={() => router.push('/child/schedule')}>
          <View style={styles.menuIconBox}>
            <Text style={{fontSize: 28}}>📅</Text>
          </View>
          <View style={styles.menuLabelBox}>
            <Text style={styles.menuLabel}>Schedule</Text>
          </View>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.menuItem} onPress={() => router.push('/child/scan')}>
          <View style={styles.menuIconBox}>
            <Text style={{fontSize: 28}}>🍲</Text>
          </View>
          <View style={styles.menuLabelBox}>
            <Text style={styles.menuLabel}>Feed</Text>
          </View>
        </TouchableOpacity>

        <TouchableOpacity style={styles.menuItem} onPress={() => router.push('/child/meds')}>
          <View style={styles.menuIconBox}>
            <Text style={{fontSize: 28}}>💊</Text>
          </View>
          <View style={styles.menuLabelBox}>
            <Text style={styles.menuLabel}>Heal</Text>
          </View>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#F3FEF8',
  },
  center: { 
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center' 
  },
  // Background stripes (Figma dark blue vertical stripes)
  bgStripes: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 140,
  },
  stripe: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: '8%',
    backgroundColor: '#374A71',
    opacity: 0.15,
  },
  floor: {
    position: 'absolute',
    bottom: 120,
    left: 0,
    right: 0,
    height: 60,
    backgroundColor: '#C4A882',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    paddingHorizontal: 24,
    paddingTop: 50,
    zIndex: 10,
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
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
    borderTopRightRadius: 20,
    borderTopLeftRadius: 0,
    padding: 20,
    paddingLeft: 27,
    alignSelf: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3.8 },
    shadowOpacity: 0.25,
    shadowRadius: 4.75,
    elevation: 5,
  },
  petStatusTitle: {
    fontSize: 22,
    fontWeight: '600',
    color: '#0C3638',
    marginBottom: 10,
  },
  barRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
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
    height: 24,
    borderRadius: 14,
    flex: 1,
    justifyContent: 'center',
  },
  hpBarFill: {
    backgroundColor: '#6CC55F',
    height: 24,
    borderRadius: 14,
    position: 'absolute',
    left: 0,
  },
  xpBarFill: {
    backgroundColor: '#5282BB',
    height: 24,
    borderRadius: 14,
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
    zIndex: 5,
  },
  petImage: {
    width: 220,
    height: 220,
  },
  bottomMenu: {
    backgroundColor: '#0C3638',
    width: width - 24,
    height: 140,
    borderRadius: 100,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 31,
    paddingTop: 5,
    alignSelf: 'center',
    position: 'absolute',
    bottom: 20,
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
  menuLabelBox: {
    backgroundColor: '#116367',
    borderRadius: 65,
    paddingVertical: 3,
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
