import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform, Alert, Dimensions } from 'react-native';
import { supabase } from '../api/client';
import { useRouter } from 'expo-router';

const { width } = Dimensions.get('window');

export default function RegisterScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [doctorCode, setDoctorCode] = useState('');
  const [patientCode, setPatientCode] = useState(''); // for child claiming
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'child' | 'parent'>('child');

  async function signUp() {
    setLoading(true);
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          role: activeTab, // saving role to metadata
          doctor_code: activeTab === 'child' ? doctorCode : undefined,
          patient_code: activeTab === 'parent' ? patientCode : undefined,
        },
      },
    });

    if (error) {
      Alert.alert('Gagal Registrasi', error.message);
    } else if (data?.user) {
      // Sisipkan row ke public.users agar /api/v1/users/me bisa menemukan data
      const { error: insertError } = await supabase
        .from('users')
        .insert({
          id: data.user.id,
          email: data.user.email,
          full_name: email.split('@')[0], // nama sementara dari email
          role: activeTab,
          is_active: true,
          password_hash: 'supabase_managed',
        });

      if (insertError) {
        console.log('Insert public.users gagal (mungkin sudah ada):', insertError.message);
      }

      Alert.alert('Sukses', 'Registrasi berhasil! Silakan login.', [
        { text: 'OK', onPress: () => router.replace('/login') }
      ]);
    }
    setLoading(false);
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.container}>
      <View style={styles.logoContainer}>
        <View style={styles.logoMock} />
        <Text style={styles.logoText}>BiteBuddy</Text>
      </View>
      
      <Text style={styles.title}>Register as</Text>

      <View style={styles.card}>
        <View style={styles.tabContainer}>
          <TouchableOpacity 
            style={[styles.tab, activeTab === 'child' ? styles.activeTab : styles.inactiveTab, { borderTopLeftRadius: 20 }]} 
            onPress={() => setActiveTab('child')}
          >
            <Text style={styles.tabText}>Child</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.tab, activeTab === 'parent' ? styles.activeTab : styles.inactiveTab, { borderTopRightRadius: 20 }]}
            onPress={() => setActiveTab('parent')}
          >
            <Text style={styles.tabText}>Parent</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.formContainer}>
          <Text style={styles.label}>Email:</Text>
          <TextInput
            style={styles.input}
            onChangeText={(text) => setEmail(text)}
            value={email}
            autoCapitalize={'none'}
          />
          
          <Text style={styles.label}>Password:</Text>
          <TextInput
            style={styles.input}
            onChangeText={(text) => setPassword(text)}
            value={password}
            secureTextEntry={true}
            autoCapitalize={'none'}
          />

          {activeTab === 'child' ? (
            <>
              <Text style={styles.label}>Doctor's Code:</Text>
              <TextInput
                style={styles.input}
                onChangeText={(text) => setDoctorCode(text)}
                value={doctorCode}
                autoCapitalize={'none'}
                placeholder="e.g. D551"
              />
            </>
          ) : (
            <>
              <Text style={styles.label}>Patient's Code (Optional):</Text>
              <TextInput
                style={styles.input}
                onChangeText={(text) => setPatientCode(text)}
                value={patientCode}
                autoCapitalize={'none'}
                placeholder="e.g. P230401"
              />
            </>
          )}
          
          <TouchableOpacity style={styles.button} onPress={signUp} disabled={loading}>
            <Text style={styles.buttonText}>{loading ? 'Memuat...' : `Register as ${activeTab === 'child' ? 'Child' : 'Parent'}`}</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.footer}>
        <TouchableOpacity onPress={() => router.replace('/login')}>
          <Text style={styles.footerLink}>Back to Login</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3FEF8', 
    alignItems: 'center',
  },
  logoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 67, 
    marginBottom: 60,
  },
  logoMock: {
    width: 43,
    height: 43,
    backgroundColor: '#D9ECF3',
    borderRadius: 10,
    marginRight: 10,
  },
  logoText: {
    fontSize: 28,
    fontWeight: '600',
    color: '#0C3638',
  },
  title: {
    fontSize: 32,
    fontWeight: '600',
    color: '#0C3638',
    marginBottom: 20,
  },
  card: {
    backgroundColor: '#D9ECF3',
    width: width - 84, 
    borderRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 2,
    elevation: 4,
  },
  tabContainer: {
    flexDirection: 'row',
    height: 58,
  },
  tab: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  activeTab: {
    backgroundColor: '#5282BB',
  },
  inactiveTab: {
    backgroundColor: '#B9E5D8',
  },
  tabText: {
    color: '#FFF',
    fontSize: 20,
    fontWeight: '600',
  },
  formContainer: {
    padding: 29,
    paddingRight: 26,
    paddingBottom: 33,
  },
  label: {
    fontSize: 20,
    fontWeight: '600',
    color: '#0C3638',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#FEFEFF',
    borderWidth: 1,
    borderColor: '#374A71',
    borderRadius: 10,
    height: 37,
    paddingHorizontal: 10,
    marginBottom: 23,
    color: '#0C3638',
  },
  button: {
    backgroundColor: '#5282BB',
    borderRadius: 20,
    height: 35,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
  },
  buttonText: {
    color: '#E5FDEF',
    fontSize: 20,
    fontWeight: '600',
  },
  footer: {
    flexDirection: 'row',
    position: 'absolute',
    bottom: 50,
  },
  footerLink: {
    fontSize: 16,
    color: '#0C3638',
    fontWeight: '600',
  },
});
