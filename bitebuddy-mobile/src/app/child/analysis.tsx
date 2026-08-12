import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, ScrollView, Dimensions, TextInput } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';

const { width } = Dimensions.get('window');

export default function AnalysisResult() {
  const router = useRouter();
  const params = useLocalSearchParams();
  
  const foodName = (params.foodName as string) || 'Detected Food';
  const imageUri = (params.imageUri as string) || null;
  const totalWeight = parseInt((params.totalWeight as string) || '0', 10);
  
  const [editableFoodName, setEditableFoodName] = useState(foodName);
  
  // Parse real ingredients from API
  let ingredients: any[] = [];
  try {
    ingredients = JSON.parse((params.ingredients as string) || '[]');
  } catch { ingredients = []; }

  const [editableGrams, setEditableGrams] = useState(totalWeight || ingredients.reduce((sum: number, i: any) => sum + (i.weight_g || 0), 0));
  
  // Calculate nutrition estimates from ingredients weight
  // These are rough estimates - in production the /food/confirm endpoint calculates exact values
  const totalGrams = editableGrams;
  const estimatedCalories = Math.round(totalGrams * 1.2); // rough kcal estimate
  const estimatedSugar = Math.round(totalGrams * 0.04 * 10) / 10;
  const estimatedCarbs = Math.round(totalGrams * 0.24 * 100) / 100;
  const estimatedFiber = Math.round(totalGrams * 0.01 * 10) / 10;
  const estimatedProtein = Math.round(totalGrams * 0.04 * 100) / 100;
  const estimatedFat = Math.round(totalGrams * 0.007 * 100) / 100;

  const sugarCategory = estimatedSugar < 5 ? 'low' : estimatedSugar < 15 ? 'medium' : 'high';
  const sugarCategoryColor = sugarCategory === 'low' ? '#10B981' : sugarCategory === 'medium' ? '#E03B38' : '#DC2626';

  return (
    <ScrollView style={styles.scrollContainer} contentContainerStyle={styles.scrollContent}>
      {/* Back Button */}
      <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
        <Text style={styles.backBtnText}>{'<'}</Text>
      </TouchableOpacity>
      
      <Text style={styles.pageTitle}>Analysis Result</Text>

      {/* Main Card */}
      <View style={styles.cardContainer}>
          {/* Top Header inside Card */}
        <View style={styles.cardHeader}>
          <Text style={styles.aiDetectedText}>AI detected</Text>
          <TextInput 
            style={styles.foodNameInput} 
            value={editableFoodName} 
            onChangeText={setEditableFoodName} 
            placeholder="Food Name"
            placeholderTextColor="#999"
          />
        </View>
        
        <Text style={styles.estSugarTitle}>Estimated Sugar Content</Text>
        
        {/* Sugar Content Badge */}
        <View style={styles.sugarBadge}>
          <Text style={styles.sugarValue}>{estimatedSugar} g/portion</Text>
        </View>
        <View style={styles.sugarCategoryBadge}>
          <Text style={[styles.sugarCategoryText, { color: sugarCategoryColor }]}>Category: {sugarCategory}</Text>
        </View>

        {/* Middle Section: Image & Portion */}
        <View style={styles.middleRow}>
          {/* Image Box */}
          <View style={styles.imageBox}>
            {imageUri ? (
              <Image source={{ uri: imageUri }} style={styles.foodImage} />
            ) : (
              <View style={styles.imagePlaceholder}><Text style={{fontSize: 40}}>🍽️</Text></View>
            )}
          </View>
          
          {/* Portion Box */}
          <View style={styles.portionBox}>
            <Text style={styles.portionTitle}>Portion{'\n'}size</Text>
            <TextInput 
              style={styles.portionInput} 
              value={String(editableGrams)} 
              onChangeText={(text) => setEditableGrams(parseInt(text) || 0)} 
              keyboardType="numeric"
            />
            <Text style={styles.portionUnit}>gram</Text>
          </View>
        </View>

        {/* Detected Ingredients List */}
        {ingredients.length > 0 && (
          <View style={styles.ingredientsList}>
            <Text style={styles.ingredientsTitle}>Detected Ingredients:</Text>
            {ingredients.map((item: any, idx: number) => (
              <Text key={idx} style={styles.ingredientItem}>
                • {item.ingredient || item.description} ({item.weight_g}g)
              </Text>
            ))}
          </View>
        )}

        {/* Nutrition Facts Bottom Block */}
        <View style={styles.nutritionBlock}>
          <View style={styles.nutritionLeft}>
            <Text style={styles.nutritionTitle}>Nutrition Facts</Text>
            <Text style={styles.nutritionText}>Calories: {estimatedCalories} kkal</Text>
            <Text style={styles.nutritionText}>Carbs: {estimatedCarbs} gram</Text>
            <Text style={styles.nutritionText}>Fiber: {estimatedFiber} gram</Text>
            <Text style={styles.nutritionText}>Protein: {estimatedProtein} gram</Text>
            <Text style={styles.nutritionText}>Fat: {estimatedFat} gram</Text>
          </View>
          <Image 
            source={require('../../../assets/pet-glasses.png')} 
            style={styles.petGlasses}
            resizeMode="contain"
          />
        </View>
      </View>

      {/* Confirm Button */}
      <TouchableOpacity style={styles.confirmBtn} onPress={() => router.replace('/child')}>
        <Text style={styles.confirmBtnText}>Confirm</Text>
      </TouchableOpacity>
      
      <View style={{height: 40}} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollContainer: {
    flex: 1,
    backgroundColor: '#F3FEF8',
  },
  scrollContent: {
    alignItems: 'center',
    paddingBottom: 20,
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
  pageTitle: {
    fontSize: 32,
    fontWeight: '700',
    color: '#0C3638',
    marginTop: 95,
    marginBottom: 15,
  },
  cardContainer: {
    backgroundColor: '#374171',
    width: width - 70,
    borderRadius: 20,
    shadowColor: '#374171',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.25,
    shadowRadius: 20,
    elevation: 8,
    overflow: 'hidden',
  },
  cardHeader: {
    backgroundColor: '#5282BB',
    width: '100%',
    paddingVertical: 15,
    alignItems: 'center',
  },
  aiDetectedText: {
    color: '#D9ECF3',
    fontSize: 14,
    fontWeight: '600',
  },
  foodNameText: {
    color: 'white',
    fontSize: 22,
    fontWeight: '700',
  },
  foodNameInput: {
    color: 'white',
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.3)',
    minWidth: 150,
  },
  estSugarTitle: {
    color: '#F9FDFF',
    fontSize: 11,
    fontWeight: '600',
    textAlign: 'center',
    marginTop: 12,
    marginBottom: 8,
  },
  sugarBadge: {
    backgroundColor: '#F3B73B',
    borderWidth: 4,
    borderColor: '#E8F4FF',
    borderRadius: 10,
    width: 257,
    height: 50,
    alignSelf: 'center',
    justifyContent: 'center',
    alignItems: 'center',
  },
  sugarValue: {
    color: '#FF6200',
    fontSize: 22,
    fontWeight: 'bold',
  },
  sugarCategoryBadge: {
    backgroundColor: '#E8F4FF',
    paddingHorizontal: 14,
    paddingVertical: 3,
    borderRadius: 20,
    alignSelf: 'center',
    marginTop: -5,
    zIndex: 2,
  },
  sugarCategoryText: {
    fontSize: 10,
    fontWeight: '600',
  },
  middleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    marginTop: 15,
  },
  imageBox: {
    width: 133,
    height: 170,
    borderWidth: 4,
    borderColor: '#5282BB',
    borderRadius: 10,
    overflow: 'hidden',
    backgroundColor: '#CCC',
  },
  foodImage: { width: '100%', height: '100%', resizeMode: 'cover' },
  imagePlaceholder: { width: '100%', height: '100%', backgroundColor: '#D9D9D9', justifyContent: 'center', alignItems: 'center' },
  portionBox: {
    width: 113,
    height: 170,
    backgroundColor: 'white',
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
  },
  portionTitle: {
    color: '#374171',
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 5,
  },
  portionNumber: {
    color: '#0C3638',
    fontSize: 36,
    fontWeight: 'bold',
  },
  portionInput: {
    color: '#0C3638',
    fontSize: 36,
    fontWeight: 'bold',
    textAlign: 'center',
    borderBottomWidth: 2,
    borderBottomColor: '#CCC',
    minWidth: 80,
    padding: 0,
    margin: 0,
  },
  portionUnit: {
    color: '#0C3638',
    fontSize: 13,
    fontWeight: 'bold',
    marginTop: -5,
  },
  ingredientsList: {
    paddingHorizontal: 25,
    marginTop: 12,
  },
  ingredientsTitle: {
    color: '#E8F4FF',
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 4,
  },
  ingredientItem: {
    color: '#D9ECF3',
    fontSize: 11,
    fontWeight: '500',
  },
  nutritionBlock: {
    backgroundColor: '#D9ECF3',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    marginTop: 15,
  },
  nutritionLeft: {
    flex: 1,
  },
  nutritionTitle: {
    color: '#374171',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  nutritionText: {
    color: '#5282BB',
    fontSize: 12,
    fontWeight: 'bold',
  },
  petGlasses: {
    width: 90,
    height: 90,
  },
  confirmBtn: {
    backgroundColor: '#374171',
    borderWidth: 3,
    borderColor: '#272E51',
    width: width - 70,
    height: 48,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 20,
    shadowColor: '#374171',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 2,
    elevation: 3,
  },
  confirmBtnText: {
    color: '#E8F4FF',
    fontSize: 22,
    fontWeight: 'bold',
  }
});
