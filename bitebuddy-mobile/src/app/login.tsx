import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform, Alert, Dimensions, ScrollView } from 'react-native';
import { supabase } from '../api/client';
import { useRouter } from 'expo-router';

const { width } = Dimensions.get('window');

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'child' | 'parent'>('child');

  async function signInWithEmail() {
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({
      email: email,
      password: password,
    });

    if (error) {
      Alert.alert('Gagal Login', error.message);
    } else {
      router.replace('/');
    }
    setLoading(false);
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        <View style={styles.logoContainer}>
          <View style={styles.logoMock} />
          <Text style={styles.logoText}>BiteBuddy</Text>
        </View>
        
        <Text style={styles.title}>Log in as</Text>

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
            <Text style={styles.label}>Username:</Text>
            <TextInput
              style={styles.input}
              onChangeText={(text) => setEmail(text)}
              value={email}
              autoCapitalize={'none'}
              placeholder="email@example.com"
              placeholderTextColor="#94A3B8"
            />
            
            <Text style={styles.label}>Password:</Text>
            <TextInput
              style={styles.input}
              onChangeText={(text) => setPassword(text)}
              value={password}
              secureTextEntry={true}
              autoCapitalize={'none'}
              placeholder="••••••••"
              placeholderTextColor="#94A3B8"
            />
            
            <TouchableOpacity style={styles.button} onPress={signInWithEmail} disabled={loading}>
              <Text style={styles.buttonText}>{loading ? 'Memuat...' : `Log in as ${activeTab === 'child' ? 'Child' : 'Parent'}`}</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>Don't have account yet? </Text>
          <TouchableOpacity onPress={() => router.push('/register')}>
            <Text style={styles.footerLink}>Register here!</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3FEF8',
  },
  scrollContent: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  logoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 40,
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
    fontSize: 18,
    fontWeight: '600',
    color: '#0C3638',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#FEFEFF',
    borderWidth: 1,
    borderColor: '#374A71',
    borderRadius: 10,
    height: 42,
    paddingHorizontal: 12,
    marginBottom: 20,
    color: '#0C3638',
    fontSize: 15,
  },
  button: {
    backgroundColor: '#5282BB',
    borderRadius: 20,
    height: 42,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 5,
  },
  buttonText: {
    color: '#E5FDEF',
    fontSize: 18,
    fontWeight: '600',
  },
  footer: {
    flexDirection: 'row',
    marginTop: 40,
  },
  footerText: {
    fontSize: 14,
    color: '#0C3638',
    fontWeight: '600',
  },
  footerLink: {
    fontSize: 14,
    color: '#003FEC',
    fontWeight: '600',
  },
});
