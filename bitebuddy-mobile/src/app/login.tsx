import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform, Alert } from 'react-native';
import { supabase } from '../api/client';
import { useRouter } from 'expo-router';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

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
      <View style={styles.card}>
        <Text style={styles.title}>BiteBuddy</Text>
        <Text style={styles.subtitle}>Log in untuk menemui peliharaanmu!</Text>

        <TextInput
          style={styles.input}
          onChangeText={(text) => setEmail(text)}
          value={email}
          placeholder="Email@domain.com"
          placeholderTextColor="#9ca3af"
          autoCapitalize={'none'}
        />
        <TextInput
          style={styles.input}
          onChangeText={(text) => setPassword(text)}
          value={password}
          secureTextEntry={true}
          placeholder="Password"
          placeholderTextColor="#9ca3af"
          autoCapitalize={'none'}
        />
        <TouchableOpacity style={styles.button} onPress={signInWithEmail} disabled={loading}>
          <Text style={styles.buttonText}>{loading ? 'Memuat...' : 'Masuk'}</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#E6F4FE', // Light blue background
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 32,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 10,
    },
    shadowOpacity: 0.1,
    shadowRadius: 20,
    elevation: 5,
  },
  title: {
    fontSize: 32,
    fontWeight: '800',
    color: '#1E3A8A', // Deep blue
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
    marginBottom: 32,
  },
  input: {
    backgroundColor: '#F3F4F6',
    borderRadius: 16,
    padding: 16,
    fontSize: 16,
    marginBottom: 16,
    color: '#1F2937',
  },
  button: {
    backgroundColor: '#10B981', // Emerald green
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '700',
  },
});
