import React, { useState, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, Alert, ActivityIndicator } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { apiClient } from '../../api/client';
import { useRouter } from 'expo-router';

export default function MedsPage() {
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
        <TouchableOpacity style={styles.btn} onPress={requestPermission}>
          <Text style={styles.btnText}>Izinkan Kamera</Text>
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

  const uploadImage = async () => {
    if (!imageUri) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', {
        uri: imageUri,
        name: 'meds.jpg',
        type: 'image/jpeg',
      } as any);

      // Endpoint API dari spesifikasi untuk medicine
      await apiClient.post('/scan/medicine/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      Alert.alert('Berhasil', 'Obat berhasil dideteksi!', [
        { text: 'OK', onPress: () => router.replace('/child') }
      ]);
    } catch (error) {
      Alert.alert('Gagal', 'Terjadi kesalahan saat mendeteksi obat.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      {imageUri ? (
        <View style={styles.previewContainer}>
          <Image source={{ uri: imageUri }} style={styles.previewImage} />
          <View style={styles.actionRow}>
            <TouchableOpacity style={[styles.actionBtn, styles.btnSecondary]} onPress={() => setImageUri(null)}>
              <Text style={styles.btnTextSecondary}>Retake</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.actionBtn, styles.btnPrimary]} onPress={uploadImage} disabled={loading}>
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnTextPrimary}>Confirm</Text>}
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        <CameraView style={styles.camera} ref={cameraRef} facing="back">
          <View style={styles.overlay}>
            <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
              <Text style={styles.backText}>{'< Back'}</Text>
            </TouchableOpacity>
            
            <Text style={styles.instruction}>Take a picture of your pills/insulin</Text>

            <View style={styles.bottomControls}>
              <TouchableOpacity style={styles.captureBtn} onPress={takePicture}>
                <View style={styles.captureInner} />
              </TouchableOpacity>
            </View>
          </View>
        </CameraView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  text: { color: '#FFF', fontSize: 16, marginBottom: 16 },
  btn: { backgroundColor: '#10B981', padding: 16, borderRadius: 12 },
  btnText: { color: '#FFF', fontWeight: 'bold' },
  camera: { flex: 1 },
  overlay: { flex: 1, justifyContent: 'space-between', backgroundColor: 'rgba(0,0,0,0.2)', padding: 24, paddingTop: 60 },
  backBtn: { backgroundColor: 'rgba(255,255,255,0.3)', padding: 10, borderRadius: 10, alignSelf: 'flex-start' },
  backText: { color: '#FFF', fontWeight: 'bold' },
  instruction: { color: '#FFF', fontSize: 24, fontWeight: '700', textAlign: 'center', backgroundColor: 'rgba(0,0,0,0.4)', padding: 20, borderRadius: 20 },
  bottomControls: { alignItems: 'center', paddingBottom: 40 },
  captureBtn: { width: 80, height: 80, borderRadius: 40, borderWidth: 4, borderColor: '#FFF', justifyContent: 'center', alignItems: 'center' },
  captureInner: { width: 64, height: 64, borderRadius: 32, backgroundColor: '#FFF' },
  previewContainer: { flex: 1, backgroundColor: '#000' },
  previewImage: { flex: 1, resizeMode: 'cover' },
  actionRow: { flexDirection: 'row', padding: 24, justifyContent: 'space-between', backgroundColor: '#FFF', borderTopLeftRadius: 30, borderTopRightRadius: 30, position: 'absolute', bottom: 0, left: 0, right: 0 },
  actionBtn: { flex: 1, padding: 20, borderRadius: 16, alignItems: 'center', marginHorizontal: 8 },
  btnSecondary: { backgroundColor: '#F1F5F9' },
  btnTextSecondary: { color: '#475569', fontSize: 18, fontWeight: '700' },
  btnPrimary: { backgroundColor: '#5282BB' },
  btnTextPrimary: { color: '#FFF', fontSize: 18, fontWeight: '700' },
});
