import React, { useState, useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View } from 'react-native';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import ScanScreen from './src/screens/ScanScreen';
import { supabase } from './src/services/supabase';

type Screen = 'login' | 'home' | 'scan';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('login');

  useEffect(() => {
    // Cek session awal
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setCurrentScreen('home');
      }
    });

    // Listen untuk perubahan auth (login/logout)
    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      if (session) {
        setCurrentScreen('home');
      } else {
        setCurrentScreen('login');
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, []);

  let content;
  if (currentScreen === 'login') {
    content = <LoginScreen onLoginSuccess={() => setCurrentScreen('home')} />;
  } else if (currentScreen === 'home') {
    content = (
      <HomeScreen 
        onNavigateToScan={() => setCurrentScreen('scan')} 
        onLogout={() => setCurrentScreen('login')}
      />
    );
  } else if (currentScreen === 'scan') {
    content = <ScanScreen onBack={() => setCurrentScreen('home')} />;
  }

  return (
    <View style={styles.container}>
      <StatusBar style="auto" />
      {content}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
});
