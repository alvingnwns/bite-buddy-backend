import React, { useState, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, Alert, ActivityIndicator, Dimensions } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { supabase } from '../../api/client';
import { useRouter } from 'expo-router';

const { width } = Dimensions.get('window');

export default function ScanScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const cameraRef = useRef<CameraView>(null);
  const router = useRouter();

  if (!permission) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text style={styles.text}>Akses kamera dibutuhkan.</Text>
        <TouchableOpacity style={styles.btnPrimary} onPress={requestPermission}>
          <Text style={styles.btnTextPrimary}>Izinkan Kamera</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const takePicture = async () => {
    if (cameraRef.current) {
      const photo = await cameraRef.current.takePictureAsync();
      setImageUri(photo?.uri || null);
    }
  };

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
    });
    if (!result.canceled) {
      setImageUri(result.assets[0].uri);
    }
  };

  const uploadImage = async () => {
    if (!imageUri) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', {
        uri: imageUri,
        name: 'food.jpg',
        type: 'image/jpeg',
      } as any);

      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token || '';
      const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.1.7:8000/api/v1';
      
      const response = await fetch(`${API_URL}/scan/food/analyze`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const result = await response.json();

      router.replace({
        pathname: '/child/analysis',
        params: {
          foodName: result.food_name || 'Tidak diketahui',
          xpGained: result.xp_gained || 0,
          imageUri: imageUri
        }
      });
    } catch (error) {
      console.log(error);
      Alert.alert('Gagal', 'Terjadi kesalahan saat memproses gambar.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Top Header Background */}
      <View style={styles.topHeader}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backBtnText}>{'<'}</Text>
        </TouchableOpacity>
        
        {/* Schedule Card (Mock for layout) */}
        <View style={styles.scheduleCard}>
          <Text style={styles.scheduleTitle}>Today's Schedule</Text>
          <View style={styles.taskList}>
            <View style={styles.taskRow}>
              <View style={styles.taskIcon} />
              <Text style={styles.taskText}>breakfast (06:00-08:00)</Text>
              <View style={[styles.taskProgress, { backgroundColor: '#10B981' }]}><Text style={styles.taskProgressText}>Done</Text></View>
            </View>
            <View style={styles.taskRow}>
              <View style={styles.taskIcon} />
              <Text style={styles.taskText}>lunch (11:50-13:00)</Text>
              <View style={[styles.taskProgress, { backgroundColor: '#F59E0B' }]}><Text style={styles.taskProgressText}>Late</Text></View>
            </View>
          </View>
        </View>
      </View>

      <Text style={styles.instruction}>Take a picture of your food!</Text>

      {imageUri ? (
        <View style={styles.previewWrapper}>
          <View style={styles.cameraBox}>
            <Image source={{ uri: imageUri }} style={styles.previewImage} />
          </View>
          <View style={styles.actionRow}>
             <TouchableOpacity style={[styles.actionBtn, styles.btnSecondary]} onPress={() => setImageUri(null)}>
               <Text style={styles.btnTextSecondary}>Ulangi</Text>
             </TouchableOpacity>
             <TouchableOpacity style={[styles.actionBtn, styles.btnPrimary]} onPress={uploadImage} disabled={loading}>
               {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnTextPrimary}>Confirm</Text>}
             </TouchableOpacity>
           </View>
        </View>
      ) : (
        <View style={styles.previewWrapper}>
          <View style={styles.cameraBox}>
            <CameraView style={styles.cameraInner} ref={cameraRef} facing="back" />
          </View>

          <TouchableOpacity style={styles.feedBuddyBtn} onPress={takePicture}>
            <View style={styles.cameraIconMock} />
            <Text style={styles.feedBuddyText}>Feed Buddy!</Text>
          </TouchableOpacity>
        </View>
      )}

      {!imageUri && (
        <TouchableOpacity style={styles.historyBtn} onPress={pickImage}>
          <Text style={styles.historyText}>Upload from Gallery</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3FEF8', alignItems: 'center' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  text: { color: '#0C3638', fontSize: 16, marginBottom: 16 },
  topHeader: {
    backgroundColor: '#0C3638',
    width: '100%',
    height: 214,
    position: 'absolute',
    top: 0,
    zIndex: 0,
  },
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
  scheduleCard: {
    backgroundColor: '#FFFFFF',
    width: 316,
    height: 105,
    borderRadius: 10,
    position: 'absolute',
    top: 89,
    alignSelf: 'center',
    padding: 15,
    zIndex: 1,
  },
  scheduleTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#0C3638',
    textAlign: 'center',
    marginBottom: 5,
  },
  taskList: { flex: 1 },
  taskRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 5, justifyContent: 'space-between' },
  taskIcon: { width: 15, height: 15, backgroundColor: '#CCC', borderRadius: 7.5 },
  taskText: { fontSize: 12, color: '#374A71', fontWeight: '600', flex: 1, marginLeft: 10 },
  taskProgress: { paddingHorizontal: 10, paddingVertical: 2, borderRadius: 10 },
  taskProgressText: { color: 'white', fontSize: 10, fontWeight: 'bold' },
  instruction: {
    marginTop: 230,
    fontSize: 20,
    fontWeight: '600',
    color: '#0C3638',
    marginBottom: 20,
  },
  previewWrapper: {
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  cameraBox: {
    width: 273,
    height: 349,
    borderWidth: 5,
    borderColor: '#5282BB',
    borderRadius: 10,
    overflow: 'hidden',
    backgroundColor: '#000',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 4,
  },
  cameraInner: { flex: 1 },
  previewImage: { flex: 1, resizeMode: 'cover' },
  feedBuddyBtn: {
    backgroundColor: '#5282BB',
    width: 311,
    height: 189,
    borderRadius: 20,
    position: 'absolute',
    bottom: -90, // overlaps the camera box
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 2,
    elevation: 5,
  },
  cameraIconMock: {
    width: 24,
    height: 24,
    backgroundColor: '#FFF',
    borderRadius: 4,
    marginBottom: 10,
  },
  feedBuddyText: {
    color: '#E5FDEF',
    fontSize: 20,
    fontWeight: '600',
  },
  historyBtn: {
    position: 'absolute',
    bottom: 50,
    width: 311,
    height: 43,
    backgroundColor: '#D9ECF3',
    borderWidth: 4,
    borderColor: '#0C3638',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  historyText: {
    color: '#000',
    fontSize: 16,
    fontWeight: '500',
  },
  actionRow: {
    flexDirection: 'row',
    marginTop: 30,
    width: 273,
    justifyContent: 'space-between',
  },
  actionBtn: { flex: 1, padding: 15, borderRadius: 10, alignItems: 'center', marginHorizontal: 5 },
  btnSecondary: { backgroundColor: '#F1F5F9' },
  btnTextSecondary: { color: '#475569', fontSize: 16, fontWeight: '700' },
  btnPrimary: { backgroundColor: '#5282BB' },
  btnTextPrimary: { color: '#FFF', fontSize: 16, fontWeight: '700' },
});
