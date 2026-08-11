import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, ScrollView, ActivityIndicator, Image, Dimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../context/AuthContext';
import { apiClient, supabase } from '../../api/client';

const { width } = Dimensions.get('window');

export default function ParentDashboard() {
  const router = useRouter();
  const { user } = useAuth();
  const [children, setChildren] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchChildren();
  }, []);

  const fetchChildren = async () => {
    try {
      // In a real scenario, this fetches from Supabase or API where parent_id = user.id
      // We mock it for now since the backend endpoint might vary
      setChildren([
        { id: 1, name: 'Alli', status: 'Good' },
        { id: 2, name: 'Marvel', status: 'Good' }
      ]);
    } catch (e) {
      console.log('Error fetching children', e);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.replace('/login');
  };

  if (loading) return <View style={styles.center}><ActivityIndicator color="#0C3638" /></View>;

  return (
    <SafeAreaView style={styles.container}>
      {/* Top Header */}
      <View style={styles.header}>
        {/* Placeholder for Logo */}
        <View style={styles.logoPlaceholder} />
        <Text style={styles.title}>BiteBuddy</Text>
        <TouchableOpacity style={styles.settingsBtn} onPress={handleLogout}>
          <Text style={{fontSize: 24}}>⚙️</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.greetingSection}>
        <Text style={styles.greetingTitle}>Hi, {user?.email?.split('@')[0] || 'Ortukeren123'}!</Text>
        <Text style={styles.greetingSub}>
          BiteBuddy is here to help you monitor your child's health.
        </Text>

        <TouchableOpacity style={styles.addBtn}>
          <Text style={styles.addBtnText}>Add New Child</Text>
        </TouchableOpacity>
      </View>

      {/* Bottom Blue Background Area */}
      <View style={styles.bottomArea}>
        <ScrollView contentContainerStyle={styles.listContainer} showsVerticalScrollIndicator={false}>
          {children.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={{fontSize: 50, marginBottom: 15}}>😔</Text>
              <Text style={styles.emptyText}>
                You have not registered any child. Click 'Add New Child' button above to register your children.
              </Text>
            </View>
          ) : (
            children.map((c, index) => (
              <View key={c.id} style={{position: 'relative', marginBottom: 15}}>
                {/* Notification indicator bubble */}
                {index === 0 && (
                  <View style={styles.notificationBubble} />
                )}

                <TouchableOpacity 
                  style={styles.childCard} 
                  activeOpacity={0.9}
                  onPress={() => router.push(`/parent/view-child?id=${c.id}`)}
                >
                  <View style={styles.cardLeft}>
                    <View style={styles.childPhoto}>
                      <Text style={{fontSize:30}}>👧</Text>
                    </View>
                    <View style={styles.childDetails}>
                      <Text style={styles.childName}>{c.name}</Text>
                      <Text style={styles.childStatusLabel}>Pet Status:</Text>
                      <View style={styles.statusBadge}>
                        <Text style={styles.statusText}>{c.status}</Text>
                      </View>
                    </View>
                  </View>
                  <View style={styles.cardRight}>
                    <Text style={styles.caret}>{'>'}</Text>
                  </View>
                </TouchableOpacity>
              </View>
            ))
          )}
          <View style={{height: 50}} />
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3FEF8' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 35,
    paddingTop: 50,
  },
  logoPlaceholder: { width: 43, height: 43, backgroundColor: '#D9ECF3', borderRadius: 10 },
  title: { fontSize: 28, fontWeight: '600', color: '#0C3638', top: 5 },
  settingsBtn: {
    width: 57,
    height: 57,
    backgroundColor: '#D9ECF3',
    borderWidth: 4,
    borderColor: '#0C3638',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: -10,
  },
  greetingSection: {
    paddingHorizontal: 39,
    paddingTop: 40,
    paddingBottom: 25,
  },
  greetingTitle: {
    fontSize: 21,
    fontWeight: '600',
    color: '#0C3638',
    marginBottom: 5,
  },
  greetingSub: {
    fontSize: 15,
    fontWeight: '600',
    color: '#0C3638',
    marginBottom: 20,
    width: 272,
  },
  addBtn: {
    backgroundColor: '#5282BB',
    paddingVertical: 8,
    borderRadius: 10,
    alignItems: 'center',
    width: '100%',
  },
  addBtnText: {
    color: '#F3FEF8',
    fontSize: 15,
    fontWeight: '600',
  },
  bottomArea: {
    flex: 1,
    backgroundColor: '#5282BB',
    borderTopLeftRadius: 0,
    borderTopRightRadius: 0,
    width: '100%',
    paddingTop: 30,
  },
  listContainer: {
    paddingHorizontal: 39,
    paddingBottom: 50,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 60,
    paddingHorizontal: 40,
  },
  emptyText: {
    textAlign: 'center',
    color: '#F3FEF8',
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 24,
  },
  childCard: {
    flexDirection: 'row',
    height: 119,
    borderRadius: 10,
    overflow: 'hidden',
  },
  cardLeft: {
    flex: 79,
    backgroundColor: '#D9ECF3',
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: 20,
  },
  cardRight: {
    flex: 21,
    backgroundColor: '#374A71',
    justifyContent: 'center',
    alignItems: 'center',
  },
  childPhoto: {
    width: 86,
    height: 86,
    borderRadius: 43,
    backgroundColor: '#FFF',
    borderWidth: 3,
    borderColor: '#D518B5',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 15,
  },
  childDetails: {
    justifyContent: 'center',
  },
  childName: {
    fontSize: 21,
    fontWeight: '600',
    color: '#0C3638',
  },
  childStatusLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#0C3638',
    marginTop: 4,
    marginBottom: 2,
  },
  statusBadge: {
    backgroundColor: '#6CC55F',
    paddingHorizontal: 12,
    paddingVertical: 2,
    borderRadius: 10,
    alignSelf: 'flex-start',
  },
  statusText: {
    color: '#F3FEF8',
    fontSize: 14,
    fontWeight: '600',
  },
  caret: {
    color: '#F3FEF8',
    fontSize: 24,
    fontWeight: 'bold',
  },
  notificationBubble: {
    position: 'absolute',
    left: -13,
    top: -11,
    width: 37,
    height: 37,
    backgroundColor: '#FF6B6B',
    borderRadius: 18.5,
    zIndex: 10,
  },
});
