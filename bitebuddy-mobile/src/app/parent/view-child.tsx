import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, ScrollView, Dimensions } from 'react-native';
import { useRouter } from 'expo-router';

const { width } = Dimensions.get('window');

export default function ViewChildPage() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container}>
      {/* Background Splitting */}
      <View style={styles.bgBottom} />

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
            <Text style={styles.backBtnText}>{'<'}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.notifBtn}>
            <Text style={{fontSize: 24}}>🔔</Text>
          </TouchableOpacity>
        </View>

        {/* Child Profile Card */}
        <View style={styles.childCard}>
          <View style={styles.childPhoto}>
            <Text style={{fontSize: 30}}>👧</Text>
          </View>
          <View style={styles.childDetails}>
            <Text style={styles.childName}>Alli</Text>
            <Text style={styles.childStatusLabel}>Pet Status:</Text>
            <View style={styles.statusBadge}>
              <Text style={styles.statusText}>Good</Text>
            </View>
          </View>
        </View>

        {/* Notify Child Button */}
        <TouchableOpacity style={styles.notifyBtn}>
          <Text style={{fontSize: 24, marginRight: 10}}>⚠️</Text>
          <Text style={styles.notifyText}>Notify Child</Text>
        </TouchableOpacity>

        {/* Today's Schedule Card */}
        <Text style={styles.sectionTitle}>Today's Schedule</Text>
        <View style={styles.scheduleCard}>
          <View style={styles.taskItem}>
            <Text style={{fontSize: 20}}>💊</Text>
            <Text style={styles.taskText}>pills (07:00-08:00)</Text>
            <View style={[styles.progressBadge, {backgroundColor: '#EF4444'}]}>
              <Text style={styles.progressText}>Skipped</Text>
            </View>
          </View>

          <View style={styles.taskItem}>
            <Text style={{fontSize: 20}}>🍲</Text>
            <Text style={styles.taskText}>lunch (11:50-13:00)</Text>
            <View style={[styles.progressBadge, {backgroundColor: '#F59E0B'}]}>
              <Text style={styles.progressText}>Late</Text>
            </View>
          </View>

          <View style={styles.taskItem}>
            <Text style={{fontSize: 20}}>💊</Text>
            <Text style={styles.taskText}>pills (07:00-08:00)</Text>
            <View style={[styles.progressBadge, {backgroundColor: '#94A3B8'}]}>
              <Text style={styles.progressText}>Not Yet</Text>
            </View>
          </View>
          
          <TouchableOpacity style={styles.editScheduleBtn}>
            <Text style={styles.editScheduleText}>Edit Child's Eating Schedule</Text>
          </TouchableOpacity>
        </View>

        {/* Submitted Pictures Section */}
        <Text style={styles.sectionTitlePictures}>Submitted Pictures</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.historyList}>
          
          {/* Card 1 */}
          <View style={styles.historyCard}>
            <View style={styles.historyImgPlaceholder}>
              <Text style={{fontSize: 30}}>🍝</Text>
            </View>
            <View style={styles.historyCardBody}>
              <Text style={styles.historyCardTitle}>Homecook Spaghetti</Text>
              <View style={styles.healthyBadge}>
                <Text style={styles.healthyText}>Healthy</Text>
              </View>
              <Text style={styles.historyTime}>Submitted Today, 12:10</Text>
              <TouchableOpacity>
                <Text style={styles.historyMoreDetails}>More details {'>'}</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Card 2 */}
          <View style={styles.historyCard}>
            <View style={styles.historyImgPlaceholder}>
              <Text style={{fontSize: 30}}>🍝</Text>
            </View>
            <View style={styles.historyCardBody}>
              <Text style={styles.historyCardTitle}>Homecook Spaghetti</Text>
              <View style={styles.healthyBadge}>
                <Text style={styles.healthyText}>Healthy</Text>
              </View>
              <Text style={styles.historyTime}>Submitted Today, 12:10</Text>
              <TouchableOpacity>
                <Text style={styles.historyMoreDetails}>More details {'>'}</Text>
              </TouchableOpacity>
            </View>
          </View>

        </ScrollView>
        <View style={{height: 50}}/>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3FEF8' },
  bgBottom: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '65%',
    backgroundColor: '#5282BB',
  },
  scrollContent: {
    paddingBottom: 40,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 35,
    paddingTop: 50,
  },
  backBtn: {
    backgroundColor: '#E03B38',
    width: 51,
    height: 51,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  backBtnText: { color: 'white', fontWeight: 'bold', fontSize: 24 },
  notifBtn: {
    width: 57,
    height: 57,
    backgroundColor: '#D9ECF3',
    borderWidth: 4,
    borderColor: '#0C3638',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  childCard: {
    backgroundColor: '#D9ECF3',
    borderRadius: 10,
    marginHorizontal: 43,
    marginTop: 20,
    paddingVertical: 15,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
  },
  childPhoto: {
    width: 86,
    height: 86,
    borderRadius: 43,
    backgroundColor: '#FFF',
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
  notifyBtn: {
    backgroundColor: '#374A71',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginHorizontal: 46,
    marginTop: 20,
    paddingVertical: 15,
    borderRadius: 8,
  },
  notifyText: {
    color: '#D9ECF3',
    fontSize: 20,
    fontWeight: '600',
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#374A71',
    marginLeft: 69,
    marginTop: 20,
    marginBottom: 10,
  },
  scheduleCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    marginHorizontal: 46,
    padding: 20,
  },
  taskItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  taskText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374A71',
    marginLeft: 10,
    flex: 1,
  },
  progressBadge: {
    paddingHorizontal: 10,
    paddingVertical: 2,
    borderRadius: 10,
  },
  progressText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '600',
  },
  editScheduleBtn: {
    backgroundColor: '#D9ECF3',
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 15,
  },
  editScheduleText: {
    color: '#0C3638',
    fontSize: 14,
    fontWeight: '600',
  },
  sectionTitlePictures: {
    fontSize: 20,
    fontWeight: '600',
    color: '#F3FEF8',
    marginLeft: 48,
    marginTop: 25,
    marginBottom: 15,
  },
  historyList: {
    paddingHorizontal: 46,
    paddingBottom: 20,
  },
  historyCard: {
    width: 157,
    backgroundColor: '#D3F1D9',
    borderRadius: 20,
    marginRight: 15,
    overflow: 'hidden',
    paddingBottom: 15,
  },
  historyImgPlaceholder: {
    width: '100%',
    height: 100,
    backgroundColor: '#BDE3C6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  historyCardBody: {
    paddingHorizontal: 15,
    paddingTop: 10,
  },
  historyCardTitle: {
    fontSize: 11,
    fontWeight: 'bold',
    color: '#31454A',
    marginBottom: 5,
  },
  healthyBadge: {
    backgroundColor: '#6CC55F',
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 2,
    borderRadius: 10,
    marginBottom: 10,
  },
  healthyText: {
    color: '#E5FDEF',
    fontSize: 11,
    fontWeight: 'bold',
  },
  historyTime: {
    fontSize: 9,
    color: '#6CC55F',
    fontWeight: 'bold',
    marginBottom: 5,
  },
  historyMoreDetails: {
    fontSize: 9,
    color: '#5282BB',
    fontWeight: 'bold',
  }
});
