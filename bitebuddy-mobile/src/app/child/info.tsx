import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, TextInput, ActivityIndicator, Alert, ScrollView } from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../api/client';
import { useRouter } from 'expo-router';

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
      // Assuming PUT /users/me or /clinical/
      await apiClient.put('/users/me', {
        full_name: fullName,
        birthdate,
        gender,
      });

      // Update clinical parameters
      await apiClient.post('/clinical/', {
        child_id: user?.id,
        height_cm: parseFloat(height),
        weight_kg: parseFloat(weight),
        allergies: allergies,
        diabetes_type: 'type_1', // default
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
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backText}>{'< Back'}</Text>
        </TouchableOpacity>
        <View style={styles.headerRight}>
          <View style={styles.iconBox}><Text>⚙️</Text></View>
          <View style={styles.iconBox}><Text>🔔</Text></View>
        </View>
      </View>

      <Text style={styles.title}>Profile</Text>

      <ScrollView contentContainerStyle={styles.cardContainer}>
        <View style={styles.card}>
          <Text style={styles.codeText}>Patient Code : {patientCode.split('-')[0]}</Text>

          <View style={styles.infoBlock}>
            <Text style={styles.infoLabel}>Username: {user?.email?.split('@')[0]}</Text>
            <Text style={styles.infoLabel}>Doctor: {doctorCode}</Text>
          </View>

          <View style={styles.detailsBlock}>
            {isEditing ? (
              <View style={styles.editForm}>
                <TextInput style={styles.input} placeholder="Full Name" value={fullName} onChangeText={setFullName} />
                <TextInput style={styles.input} placeholder="Birthdate (YYYY-MM-DD)" value={birthdate} onChangeText={setBirthdate} />
                <TextInput style={styles.input} placeholder="Gender" value={gender} onChangeText={setGender} />
                <TextInput style={styles.input} placeholder="Height (cm)" value={height} onChangeText={setHeight} keyboardType="numeric" />
                <TextInput style={styles.input} placeholder="Weight (kg)" value={weight} onChangeText={setWeight} keyboardType="numeric" />
                <Text style={styles.sectionTitle}>More information (Allergy, Medical History)</Text>
                <TextInput style={styles.inputArea} placeholder="Allergies..." value={allergies} onChangeText={setAllergies} multiline />
              </View>
            ) : (
              <View style={styles.viewForm}>
                <Text style={styles.infoValue}>Full Name: {fullName}</Text>
                <Text style={styles.infoValue}>Birthdate: {birthdate}</Text>
                <Text style={styles.infoValue}>Gender: {gender}</Text>
                <Text style={styles.infoValue}>Height: {height} cm</Text>
                <Text style={styles.infoValue}>Weight: {weight} kg</Text>
                
                <Text style={styles.sectionTitle}>More information (Allergy, Medical History)</Text>
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>{allergies || 'None'}</Text>
                </View>
              </View>
            )}
          </View>

          {isEditing ? (
            <TouchableOpacity style={styles.button} onPress={saveProfile} disabled={saving}>
              <Text style={styles.buttonText}>{saving ? 'Saving...' : 'Confirm'}</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={styles.button} onPress={() => setIsEditing(true)}>
              <Text style={styles.buttonText}>Edit Profile</Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', justifyContent: 'space-between', padding: 24, paddingTop: 40 },
  backBtn: { backgroundColor: '#D9ECF3', padding: 10, borderRadius: 10, justifyContent: 'center' },
  backText: { color: '#0C3638', fontWeight: 'bold' },
  headerRight: { flexDirection: 'row', gap: 10 },
  iconBox: { width: 45, height: 45, backgroundColor: '#D9ECF3', borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 32, fontWeight: '700', color: '#0C3638', textAlign: 'center', marginBottom: 20 },
  cardContainer: { paddingHorizontal: 20, paddingBottom: 40 },
  card: { backgroundColor: '#F8FAFC', borderRadius: 20, padding: 20, borderWidth: 1, borderColor: '#E2E8F0' },
  codeText: { fontSize: 16, fontWeight: '600', color: '#64748B', marginBottom: 20, textAlign: 'center' },
  infoBlock: { marginBottom: 20 },
  infoLabel: { fontSize: 16, color: '#0C3638', fontWeight: '600', marginBottom: 5 },
  detailsBlock: { backgroundColor: '#FFFFFF', borderRadius: 15, padding: 15, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 5, elevation: 2, marginBottom: 20 },
  editForm: { gap: 10 },
  viewForm: { gap: 10 },
  input: { backgroundColor: '#F1F5F9', padding: 12, borderRadius: 10, color: '#0C3638' },
  inputArea: { backgroundColor: '#F1F5F9', padding: 12, borderRadius: 10, color: '#0C3638', height: 80, textAlignVertical: 'top' },
  infoValue: { fontSize: 15, color: '#334155' },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#0C3638', marginTop: 15, marginBottom: 10 },
  badge: { backgroundColor: '#D9FFE1', alignSelf: 'flex-start', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  badgeText: { color: '#116367', fontWeight: '600' },
  button: { backgroundColor: '#5282BB', padding: 15, borderRadius: 15, alignItems: 'center' },
  buttonText: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' },
});
