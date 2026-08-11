import React, { useState, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, Alert, ActivityIndicator } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { apiClient } from '../api/client';
import { useRouter } from 'expo-router';

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

      // Sesuai dengan spesifikasi endpoint dari backend: POST /api/v1/scan/food/analyze
      const res = await apiClient.post('/scan/food/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      Alert.alert('Berhasil', 'Makanan berhasil dianalisis!', [
        { text: 'OK', onPress: () => router.replace('/') }
      ]);
    } catch (error) {
      console.log(error);
      Alert.alert('Gagal', 'Terjadi kesalahan saat memproses gambar.');
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
              <Text style={styles.btnTextSecondary}>Ulangi</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.actionBtn, styles.btnPrimary]} onPress={uploadImage} disabled={loading}>
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnTextPrimary}>Beri Makan!</Text>}
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        <CameraView style={styles.camera} ref={cameraRef} facing="back">
          <View style={styles.overlay}>
            <View style={styles.headerRow}>
              <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
                <Text style={styles.backText}>Tutup</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.bottomControls}>
              <TouchableOpacity style={styles.galleryBtn} onPress={pickImage}>
                <Text style={styles.galleryText}>Galeri</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.captureBtn} onPress={takePicture}>
                <View style={styles.captureInner} />
              </TouchableOpacity>
              <View style={{ width: 60 }} />
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
  overlay: { flex: 1, justifyContent: 'space-between', backgroundColor: 'rgba(0,0,0,0.1)' },
  headerRow: { padding: 24, paddingTop: 60, alignItems: 'flex-start' },
  backBtn: { backgroundColor: 'rgba(0,0,0,0.5)', padding: 10, borderRadius: 12 },
  backText: { color: '#FFF', fontSize: 16 },
  bottomControls: { flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center', paddingBottom: 60, paddingHorizontal: 24 },
  galleryBtn: { width: 60, height: 60, borderRadius: 30, backgroundColor: 'rgba(255,255,255,0.2)', justifyContent: 'center', alignItems: 'center' },
  galleryText: { color: '#FFF', fontSize: 12, fontWeight: 'bold' },
  captureBtn: { width: 80, height: 80, borderRadius: 40, borderWidth: 4, borderColor: '#FFF', justifyContent: 'center', alignItems: 'center' },
  captureInner: { width: 64, height: 64, borderRadius: 32, backgroundColor: '#FFF' },
  previewContainer: { flex: 1, backgroundColor: '#000' },
  previewImage: { flex: 1, resizeMode: 'cover' },
  actionRow: { flexDirection: 'row', padding: 24, justifyContent: 'space-between', backgroundColor: '#FFF', borderTopLeftRadius: 30, borderTopRightRadius: 30, position: 'absolute', bottom: 0, left: 0, right: 0 },
  actionBtn: { flex: 1, padding: 20, borderRadius: 16, alignItems: 'center', marginHorizontal: 8 },
  btnSecondary: { backgroundColor: '#F1F5F9' },
  btnTextSecondary: { color: '#475569', fontSize: 18, fontWeight: '700' },
  btnPrimary: { backgroundColor: '#10B981' },
  btnTextPrimary: { color: '#FFF', fontSize: 18, fontWeight: '700' },
});
