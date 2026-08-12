import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, ScrollView, Dimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { apiClient } from '../../api/client';
import { useAuth } from '../../context/AuthContext';

const { width } = Dimensions.get('window');

export default function SchedulePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [schedules, setSchedules] = useState<any[]>([]);

  useEffect(() => {
    if (user?.id) fetchSchedules();
  }, [user]);

  const fetchSchedules = async () => {
    try {
      const res = await apiClient.get(`/schedules/${user.id}`);
      setSchedules(res.data || []);
    } catch (e) {
      console.log('Error fetching schedules', e);
      // Dummy data fallback matching Figma
      setSchedules([
        { id: 1, meal_type: 'breakfast', status: 'done', target_time: '06:00-08:00' },
        { id: 2, meal_type: 'pills', status: 'missed', target_time: '07:00-08:00' },
        { id: 3, meal_type: 'lunch', status: 'late', target_time: '11:50-13:00' },
        { id: 4, meal_type: 'dinner', status: 'pending', target_time: '17:00-19:00' },
      ]);
    }
  };

  const getStatusStyle = (status: string) => {
    switch(status) {
      case 'done': return { bg: '#10B981', text: 'Done' };
      case 'missed': return { bg: '#E03B38', text: 'Skipped' };
      case 'late': return { bg: '#F59E0B', text: 'Late' };
      default: return { bg: '#5282BB', text: 'Not Yet' };
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Back Button */}
      <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
        <Text style={styles.backBtnText}>{'<'}</Text>
      </TouchableOpacity>

      <Text style={styles.pageTitle}>Daily Tasks</Text>

      <ScrollView style={styles.contentScroll} showsVerticalScrollIndicator={false}>
        
        {/* Stats Card (Chart Placeholder) */}
        <View style={styles.statsCard}>
          <Text style={styles.statsSubtitle}>Current streak</Text>
          <View style={styles.streakRow}>
            <Text style={styles.streakNumber}>🔥 12 Days</Text>
            <View style={styles.xpBadge}>
              <Text style={styles.xpText}>45 XP</Text>
            </View>
          </View>
          
          <Text style={styles.statsSubtitleSmall}>Mon, Mar 22</Text>
          
          {/* Mock Chart Area */}
          <View style={styles.chartArea}>
             <View style={styles.chartBars}>
               {/* Just simple vertical bars simulating the Figma chart */}
               <View style={[styles.bar, { height: '80%' }]} />
               <View style={[styles.bar, { height: '50%' }]} />
               <View style={[styles.bar, { height: '100%', backgroundColor: '#719FC6' }]} />
               <View style={[styles.bar, { height: '40%' }]} />
               <View style={[styles.bar, { height: '70%' }]} />
             </View>
             <View style={styles.chartLabels}>
               <Text style={styles.chartLabel}>9h</Text>
               <Text style={styles.chartLabel}>7h</Text>
               <Text style={styles.chartLabel}>5h</Text>
               <Text style={styles.chartLabel}>3h</Text>
               <Text style={styles.chartLabel}>1h</Text>
             </View>
          </View>
        </View>

        {/* Schedule List */}
        <View style={styles.scheduleCard}>
          <Text style={styles.scheduleTitle}>Today's Schedule</Text>
          
          <View style={styles.taskList}>
            {schedules.map((s, i) => {
              const statusStyle = getStatusStyle(s.status);
              return (
                <View key={i} style={styles.taskRow}>
                  <View style={styles.taskIconWrapper}>
                     <View style={styles.taskIcon} />
                  </View>
                  <Text style={styles.taskText}>{s.meal_type} ({s.target_time})</Text>
                  <View style={[styles.taskProgress, { backgroundColor: statusStyle.bg }]}>
                    <Text style={styles.taskProgressText}>{statusStyle.text}</Text>
                  </View>
                </View>
              );
            })}
          </View>
        </View>
        
        <View style={{ height: 50 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3FEF8', alignItems: 'center' },
  backBtn: {
    backgroundColor: '#E03B38',
    width: 37,
    height: 37,
    borderRadius: 7,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'absolute',
    top: 50,
    left: 35,
    zIndex: 10,
  },
  backBtnText: { color: 'white', fontWeight: 'bold', fontSize: 18 },
  pageTitle: {
    fontSize: 32,
    fontWeight: '700',
    color: '#0C3638',
    marginTop: 90,
    marginBottom: 20,
  },
  contentScroll: {
    flex: 1,
    width: '100%',
    paddingHorizontal: 30,
  },
  statsCard: {
    backgroundColor: '#374A71',
    borderRadius: 10,
    width: '100%',
    padding: 20,
    marginBottom: 20,
    shadowColor: '#374A71',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
    elevation: 5,
  },
  streakRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 5,
  },
  statsSubtitle: {
    color: '#F9FDFF',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 5,
  },
  streakNumber: {
    color: '#F9FDFF',
    fontSize: 24,
    fontWeight: 'bold',
  },
  xpBadge: {
    backgroundColor: '#719FC6',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 15,
  },
  xpText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: 'bold',
  },
  statsSubtitleSmall: {
    color: '#F9FDFF',
    fontSize: 12,
    fontWeight: '400',
    textAlign: 'center',
    marginBottom: 15,
  },
  chartArea: {
    height: 120,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#596977',
    paddingVertical: 10,
    justifyContent: 'space-between',
  },
  chartBars: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-around',
    paddingHorizontal: 10,
  },
  bar: {
    width: 24,
    backgroundColor: '#F9FDFF',
    borderRadius: 5,
  },
  chartLabels: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 5,
  },
  chartLabel: {
    color: '#596977',
    fontSize: 12,
  },
  scheduleCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    width: '100%',
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  scheduleTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#0C3638',
    marginBottom: 15,
  },
  taskList: {
    flexDirection: 'column',
    gap: 15,
  },
  taskRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  taskIconWrapper: {
    width: 25,
    height: 25,
    backgroundColor: '#D9ECF3',
    borderRadius: 12.5,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  taskIcon: {
    width: 12,
    height: 12,
    backgroundColor: '#0C3638',
    borderRadius: 6,
  },
  taskText: {
    fontSize: 15,
    color: '#374A71',
    fontWeight: '600',
    flex: 1,
  },
  taskProgress: {
    paddingHorizontal: 15,
    paddingVertical: 4,
    borderRadius: 15,
  },
  taskProgressText: {
    color: 'white',
    fontSize: 11,
    fontWeight: 'bold',
  }
});
