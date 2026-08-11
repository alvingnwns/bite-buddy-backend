import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, ActivityIndicator, ScrollView, Alert } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { api } from '../services/api';

interface ScanScreenProps {
  onBack: () => void;
}

export default function ScanScreen({ onBack }: ScanScreenProps) {
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const pickImage = async (useCamera: boolean = false) => {
    let result;
    if (useCamera) {
      const permission = await ImagePicker.requestCameraPermissionsAsync();
      if (!permission.granted) return;
      result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        quality: 0.5,
      });
    } else {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) return;
      result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        quality: 0.5,
      });
    }

    if (!result.canceled && result.assets && result.assets.length > 0) {
      setImageUri(result.assets[0].uri);
      setResult(null);
    }
  };

  const uploadImage = async () => {
    if (!imageUri) return;
    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('file', {
        uri: imageUri,
        name: 'food.jpg',
        type: 'image/jpeg',
      } as any);

      // Dummy child_id for now, in real app pick from context
      // Note: we can omit child_id if we adjust backend or just pass dummy
      formData.append('child_id', '00000000-0000-0000-0000-000000000000'); 
      formData.append('meal_type', 'lunch');

      const res = await api.post('/scan/food/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResult(res.data);
    } catch (error: any) {
      console.error(error);
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to analyze food');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <TouchableOpacity style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>← Back</Text>
      </TouchableOpacity>

      <Text style={styles.title}>AI Food Scanner</Text>

      {imageUri ? (
        <Image source={{ uri: imageUri }} style={styles.previewImage} />
      ) : (
        <View style={styles.placeholderBox}>
          <Text style={styles.placeholderText}>No Image Selected</Text>
        </View>
      )}

      <View style={styles.row}>
        <TouchableOpacity style={styles.btnSmall} onPress={() => pickImage(true)}>
          <Text style={styles.btnText}>📷 Camera</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.btnSmall} onPress={() => pickImage(false)}>
          <Text style={styles.btnText}>🖼 Gallery</Text>
        </TouchableOpacity>
      </View>

      {imageUri && !result && (
        <TouchableOpacity style={styles.uploadBtn} onPress={uploadImage} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnTextLarge}>Analyze with AI</Text>}
        </TouchableOpacity>
      )}

      {result && (
        <View style={styles.resultBox}>
          <Text style={styles.resultTitle}>Detection Result:</Text>
          <Text style={styles.resultText}>Score: {result.ai_evaluation?.health_score}/10</Text>
          <Text style={styles.resultText}>Status: {result.ai_evaluation?.is_healthy ? '✅ Healthy' : '❌ Junk Food'}</Text>
          <Text style={styles.resultDesc}>{result.ai_evaluation?.reasoning}</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    paddingTop: 50,
    backgroundColor: '#F5F7FA',
    minHeight: '100%',
  },
  backButton: {
    marginBottom: 20,
  },
  backButtonText: {
    fontSize: 16,
    color: '#3498DB',
    fontWeight: 'bold',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 20,
  },
  previewImage: {
    width: '100%',
    height: 300,
    borderRadius: 15,
    marginBottom: 20,
  },
  placeholderBox: {
    width: '100%',
    height: 300,
    backgroundColor: '#E0E6ED',
    borderRadius: 15,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  placeholderText: {
    color: '#7F8C8D',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  btnSmall: {
    flex: 1,
    backgroundColor: '#95A5A6',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginHorizontal: 5,
  },
  uploadBtn: {
    backgroundColor: '#9B59B6',
    padding: 18,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 20,
  },
  btnText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  btnTextLarge: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 18,
  },
  resultBox: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 15,
    marginTop: 10,
  },
  resultTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  resultText: {
    fontSize: 16,
    marginBottom: 5,
    color: '#2C3E50',
  },
  resultDesc: {
    fontSize: 14,
    color: '#7F8C8D',
    marginTop: 10,
    fontStyle: 'italic',
  }
});
