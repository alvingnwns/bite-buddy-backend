import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, TextInput, ActivityIndicator, Alert, ScrollView, Dimensions } from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../api/client';
import { useRouter } from 'expo-router';

const { width } = Dimensions.get('window');

export default function InfoPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Form State
  const [patientCode, setPatientCode] = useState('');
  const [doctorCode, setDoctorCode] = useState('');
  const [fullName, setFullName] = useState('');
  const [birthdate, setBirthdate] = useState('');
  const [gender, setGender] = useState('');
  const [height, setHeight] = useState('');
  const [weight, setWeight] = useState('');
  const [allergies, setAllergies] = useState('');

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await apiClient.get('/users/me');
      const data = res.data;
      setPatientCode(data.id || '');
      setDoctorCode(data.doctor_id || '');
      setFullName(data.full_name || '');
      setBirthdate(data.birthdate || '');
      setGender(data.gender || '');
      
      if (data.clinical_parameter) {
        setHeight(data.clinical_parameter.height_cm?.toString() || '');
        setWeight(data.clinical_parameter.weight_kg?.toString() || '');
        setAllergies(data.clinical_parameter.allergies || '');
      }
    } catch (error) {
      console.log('Failed to fetch profile', error);
    } finally {
      setLoading(false);
    }
  };

  const saveProfile = async () => {
    setSaving(true);
    try {
      await apiClient.put('/users/me', {
        full_name: fullName,
        birthdate,
        gender,
      });

      await apiClient.post('/clinical/', {
        child_id: user?.id,
        height_cm: parseFloat(height),
        weight_kg: parseFloat(weight),
        allergies: allergies,
        diabetes_type: 'type_1',
      });

      Alert.alert('Sukses', 'Profil berhasil diperbarui!');
      setIsEditing(false);
    } catch (error) {
      console.log('Failed to update profile', error);
      Alert.alert('Gagal', 'Terjadi kesalahan saat menyimpan profil.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <View style={styles.center}><ActivityIndicator color="#0C3638" /></View>;
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Top Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backBtnText}>{'<'}</Text>
        </TouchableOpacity>
        <View style={styles.headerRight}>
          <TouchableOpacity style={styles.iconBox}><Text style={{fontSize:24}}>⚙️</Text></TouchableOpacity>
          <TouchableOpacity style={styles.iconBox}><Text style={{fontSize:24}}>🔔</Text></TouchableOpacity>
        </View>
      </View>

      <Text style={styles.title}>Profile</Text>

      <ScrollView contentContainerStyle={styles.cardContainerWrapper} showsVerticalScrollIndicator={false}>
        <View style={styles.cardContainer}>
          {/* Top Blue Banner */}
          <View style={styles.cardHeader}>
            <Text style={styles.patientCodeText}>
              Patient Code : {patientCode.split('-')[0] || 'P230401'}
            </Text>
          </View>

          {/* Card Body */}
          <View style={styles.cardBody}>
            <Text style={styles.accountText}>Username: {user?.email?.split('@')[0] || 'cherrylcantik34'}</Text>
            <Text style={styles.accountText}>Doctor: {doctorCode || 'Dr. Alvin (D551)'}</Text>
            
            <View style={styles.infoBlock}>
              <View style={styles.infoBlockRow}>
                {/* Photo Placeholder */}
                <View style={styles.photoCircle}>
                  <Text style={{fontSize:20}}>👧</Text>
                </View>
                {/* Details */}
                <View style={styles.detailsColumn}>
                  {isEditing ? (
                    <>
                      <TextInput style={styles.input} placeholder="Full Name" value={fullName} onChangeText={setFullName} />
                      <TextInput style={styles.input} placeholder="Birthdate" value={birthdate} onChangeText={setBirthdate} />
                      <TextInput style={styles.input} placeholder="Gender" value={gender} onChangeText={setGender} />
                      <TextInput style={styles.input} placeholder="Height (cm)" value={height} onChangeText={setHeight} keyboardType="numeric" />
                      <TextInput style={styles.input} placeholder="Weight (kg)" value={weight} onChangeText={setWeight} keyboardType="numeric" />
                    </>
                  ) : (
                    <>
                      <Text style={styles.detailText}>Full Name: {fullName || 'Cherryl'}</Text>
                      <Text style={styles.detailText}>Birthdate: {birthdate || '25/12/20'}</Text>
                      <Text style={styles.detailText}>Gender: {gender || 'Female'}</Text>
                      <Text style={styles.detailText}>Height: {height || '80'} centimeters</Text>
                      <Text style={styles.detailText}>Weight: {weight || '30'} kilograms</Text>
                    </>
                  )}
                </View>
              </View>
            </View>

            <Text style={styles.sectionTitle}>More information (Allergy, Medical History)</Text>
            <View style={styles.allergyBlock}>
              {isEditing ? (
                <TextInput 
                  style={[styles.input, {width: '100%'}]} 
                  placeholder="Allergies..." 
                  value={allergies} 
                  onChangeText={setAllergies} 
                  multiline 
                />
              ) : (
                <Text style={styles.detailText}>{allergies || 'seafood'}</Text>
              )}
            </View>

            {isEditing ? (
              <TouchableOpacity style={styles.actionBtn} onPress={saveProfile} disabled={saving}>
                <Text style={styles.actionBtnText}>{saving ? 'Saving...' : 'Confirm'}</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity style={styles.actionBtn} onPress={() => setIsEditing(true)}>
                <Text style={styles.actionBtnText}>Edit Profile</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
        <View style={{height: 50}} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3FEF8', alignItems: 'center' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    width: '100%',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 35,
    paddingTop: 50,
    zIndex: 10,
  },
  backBtn: {
    backgroundColor: '#E03B38',
    width: 37,
    height: 37,
    borderRadius: 7,
    justifyContent: 'center',
    alignItems: 'center',
  },
  backBtnText: { color: 'white', fontWeight: 'bold', fontSize: 18 },
  headerRight: {
    flexDirection: 'row',
    gap: 10,
  },
  iconBox: {
    width: 57,
    height: 57,
    backgroundColor: '#D9ECF3',
    borderWidth: 4,
    borderColor: '#0C3638',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: -10, // Adjust alignment
  },
  title: {
    fontSize: 32,
    fontWeight: '600',
    color: '#0C3638',
    marginBottom: 20,
    marginTop: 10,
  },
  cardContainerWrapper: {
    alignItems: 'center',
    width: width,
  },
  cardContainer: {
    width: 319,
    backgroundColor: '#D9ECF3',
    borderRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  cardHeader: {
    backgroundColor: '#5282BB',
    width: '100%',
    height: 45,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  patientCodeText: {
    color: '#F3FEF8',
    fontSize: 15,
    fontWeight: '600',
  },
  cardBody: {
    padding: 20,
  },
  accountText: {
    fontSize: 15,
    color: '#0C3638',
    fontWeight: '600',
    marginBottom: 5,
  },
  infoBlock: {
    backgroundColor: '#F3FEF8',
    borderRadius: 10,
    padding: 15,
    marginTop: 15,
  },
  infoBlockRow: {
    flexDirection: 'row',
    gap: 15,
    alignItems: 'flex-start',
  },
  photoCircle: {
    width: 69,
    height: 69,
    borderRadius: 35,
    borderWidth: 3,
    borderColor: '#D518B5',
    backgroundColor: '#CCC',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 5,
  },
  detailsColumn: {
    flex: 1,
    gap: 4,
  },
  detailText: {
    fontSize: 14,
    color: '#0C3638',
    fontWeight: '600',
  },
  input: {
    backgroundColor: '#E8F4FF',
    borderWidth: 1,
    borderColor: '#5282BB',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 5,
    fontSize: 13,
    color: '#0C3638',
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0C3638',
    marginTop: 20,
    marginBottom: 10,
  },
  allergyBlock: {
    backgroundColor: '#F3FEF8',
    borderRadius: 10,
    padding: 15,
    minHeight: 60,
    marginBottom: 25,
  },
  actionBtn: {
    backgroundColor: '#5282BB',
    borderRadius: 20,
    paddingVertical: 10,
    alignItems: 'center',
    alignSelf: 'center',
    width: '90%',
  },
  actionBtnText: {
    color: '#E5FDEF',
    fontSize: 20,
    fontWeight: '600',
  }
});
